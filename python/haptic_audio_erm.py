"""오디오 파일의 진폭 엔벨로프를 ERM duty 파형으로 변환해 펌웨어에 업로드하고,
펌웨어가 로컬 타이머로 그 파형을 재생하는 동안 오디오도 같이 틀어준다.

ERM(편심 회전질량 진동모터)은 회전 관성 때문에 세기 변화가 기계적으로 수십 ms 걸려서 진짜
오디오 주파수(수백 Hz~수 kHz)를 재생할 수 없다 — 그래서 오디오 파형 자체가 아니라 진폭
엔벨로프(짧은 구간별 RMS 크기)만 추출해서 duty로 매핑한다.

예전 버전은 매 프레임마다 BLE로 send_haptic_command()를 왕복 전송해서 계단식으로만
움직였는데, 이제 펌웨어에 WavePlayer(erm_ramp_test.cpp처럼 로컬 타이머로 duty를 재생)가
생겨서 파형 배열 전체를 한 번 업로드해두면 펌웨어가 BLE 왕복과 무관하게 매끄럽게 재생한다
(haptic_ble.HapticBleClient.upload_erm_wave() 참고). ENVELOPE_FRAME_MS(20ms=50Hz)도 더는
BLE 왕복 지연에 맞출 필요가 없어져서 ERM의 기계적 응답 한계에 맞춰 촘촘하게 잡았다.

펌웨어 버퍼 용량(ERM_WAVE_BUFFER_CAPACITY=8192 샘플)을 넘는 길이의 오디오는 업로드할 수
없다 — 20ms 프레임 기준 약 164초. 더 긴 파일은 --frame-ms를 키우거나 오디오를 잘라서 쓸 것.

지원 포맷: WAV(PCM 16/24/32-bit 또는 float)만 직접 디코딩한다(표준 라이브러리 wave 모듈,
추가 의존성 없음). mp3 등은 미리 wav로 변환해서 사용할 것(예: `ffmpeg -i in.mp3 out.wav`).
오디오 자체 재생은 macOS 내장 `afplay`로 별도 프로세스에서 동시 실행해 사람도 같이 들을 수
있게 한다(재생 없이 햅틱만 필요하면 --no-playback).

사용법:
    ./venv/bin/python3 haptic_audio_erm.py <wav 파일 경로> [--gain 1.5] [--frame-ms 20] [--no-playback]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import wave

import numpy as np

from haptic_ble import HapticBleClient

ENVELOPE_FRAME_MS = 20  # ERM 파형 재생 간격(50Hz) — 이제 펌웨어 로컬 재생이라 BLE 왕복과 무관.
ERM_WAVE_BUFFER_CAPACITY = 8192  # WavePlayer.h의 ERM_WAVE_BUFFER_CAPACITY와 동일해야 함.
ERM_MIN_ACTIVE_DUTY = 60  # 이보다 작은 duty는 모터가 실제로 안 돌 수 있어 사실상 무음 구간과 동급 취급.
ERM_MAX_DUTY = 255
SILENCE_RMS_RATIO = 0.02  # 클립 전체 최대 RMS 대비 이 비율 미만이면 무음(duty=0)으로 취급.


def load_wav_mono(path: str) -> tuple[np.ndarray, int]:
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frame_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    dtype_by_width = {1: np.uint8, 2: np.int16, 4: np.int32}
    if sample_width not in dtype_by_width:
        raise ValueError(f"지원하지 않는 샘플 폭입니다: {sample_width * 8}bit")

    samples = np.frombuffer(raw, dtype=dtype_by_width[sample_width])
    if sample_width == 1:
        samples = samples.astype(np.float32) - 128.0
        full_scale = 127.0
    else:
        samples = samples.astype(np.float32)
        full_scale = float(2 ** (sample_width * 8 - 1) - 1)

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)

    return samples / full_scale, frame_rate


def compute_envelope_duty(samples: np.ndarray, frame_rate: int, frame_ms: int, gain: float) -> np.ndarray:
    frame_len = max(1, int(frame_rate * frame_ms / 1000))
    n_frames = int(np.ceil(len(samples) / frame_len))
    padded = np.zeros(n_frames * frame_len, dtype=np.float32)
    padded[: len(samples)] = samples
    frames = padded.reshape(n_frames, frame_len)

    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    peak_rms = float(rms.max()) if rms.max() > 0 else 1.0
    silence_floor = peak_rms * SILENCE_RMS_RATIO

    normalized = np.clip(rms / peak_rms * gain, 0.0, 1.0)
    duty = np.where(
        rms < silence_floor,
        0,
        ERM_MIN_ACTIVE_DUTY + normalized * (ERM_MAX_DUTY - ERM_MIN_ACTIVE_DUTY),
    )
    return duty.round().astype(np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav_path", help="재생할 WAV 파일 경로")
    parser.add_argument("--gain", type=float, default=1.5, help="엔벨로프 세기 배율(기본 1.5)")
    parser.add_argument("--frame-ms", type=int, default=ENVELOPE_FRAME_MS, help="ERM 파형 재생 간격(ms)")
    parser.add_argument("--no-playback", action="store_true", help="afplay로 소리 재생 안 하고 햅틱만 구동")
    args = parser.parse_args()

    samples, frame_rate = load_wav_mono(args.wav_path)
    duty_frames = compute_envelope_duty(samples, frame_rate, args.frame_ms, args.gain)
    duration_s = len(samples) / frame_rate
    print(f"[오디오] {args.wav_path} ({duration_s:.1f}s, {frame_rate}Hz) -> {len(duty_frames)}프레임 엔벨로프 계산 완료")

    if len(duty_frames) > ERM_WAVE_BUFFER_CAPACITY:
        max_frame_ms = int(np.ceil(len(samples) / frame_rate * 1000 / ERM_WAVE_BUFFER_CAPACITY))
        print(f"❌ 프레임 수({len(duty_frames)})가 펌웨어 버퍼 용량({ERM_WAVE_BUFFER_CAPACITY})을 초과합니다.")
        print(f"   --frame-ms를 {max_frame_ms} 이상으로 올리거나 오디오를 잘라서 쓰세요.")
        return

    haptic = HapticBleClient()
    print("[XIAO] 'EMO-Haptic' 스캔/연결 중...")
    haptic.open()
    print("[XIAO] 연결됨")

    try:
        print(f"[XIAO] ERM 파형 {len(duty_frames)}샘플 업로드 중({args.frame_ms}ms 간격)...")
        haptic.upload_erm_wave(duty_frames.tolist(), step_ms=args.frame_ms, repeat=False, autoplay=False)
        print("[XIAO] 업로드 완료 — 재생 시작")

        playback_proc = None
        if not args.no_playback:
            playback_proc = subprocess.Popen(["afplay", args.wav_path])
        haptic.play_erm_wave()

        time.sleep(duration_s)
        if playback_proc is not None:
            playback_proc.wait()
    finally:
        haptic.stop_erm_wave()
        haptic.close()
        print("완료.")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(1)
    main()
