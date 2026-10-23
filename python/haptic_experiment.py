"""Peltier1/2 + ERM 파라미터를 자유롭게 바꿔가며 실험하는 스크립트.

아래 "여기 값만 바꿔가며 실험" 구간만 고쳐서 재실행하면 됨. ERM_MODE로 두 방식 중 선택:
  - "plain": Peltier와 똑같이 고정 duty를 ERM_DURATION_MS 동안 유지(send_haptic_command).
  - "wave" : 파형(기본 사인파, build_wave()로 자유롭게 커스텀 가능)을 펌웨어에 업로드해
             로컬 재생(WavePlayer, upload_erm_wave).
Peltier는 항상 send_haptic_command()로 직접 제어 — ERM_MODE와 무관하게 매번 같이 나감
(프로토콜상 한 메시지에 peltier1/peltier2/erm이 항상 같이 들어가야 해서).

사용법:
    ./venv/bin/python3 haptic_experiment.py
"""
from __future__ import annotations

import math
import time

from haptic_ble import HapticBleClient

# ===== 여기 값만 바꿔가며 실험 =====
PELTIER1_DUTY = 0
PELTIER1_DIRECTION = 0  # 1=가열, -1=냉각
PELTIER1_DURATION_MS = 0  # 0이면 다음 명령까지 무기한 유지(워치독 상한 있음)

PELTIER2_DUTY = 0
PELTIER2_DIRECTION = 0
PELTIER2_DURATION_MS = 0

ERM_MODE = "plain"  # "plain" 또는 "wave"

# ERM_MODE == "plain"일 때만 쓰는 값
ERM_DUTY = 0
ERM_DURATION_MS = 0

# ERM_MODE == "wave"일 때만 쓰는 값 (기본은 사인파 0->255->0 반복, 커스텀은 build_wave() 참고)
WAVE_STEP_MS = 100       # 파형 재생 간격(ms) — 로컬 재생이라 BLE 왕복과 무관, 촘촘히 줄여도 됨
WAVE_WINDOW_MS = 5000   # 파형 한 벌의 길이(ms) — 이 안에 아래 주기가 몇 번 들어가든 자동으로 반복됨
WAVE_REPEAT = True      # True면 RUN_SECONDS 동안 파형을 계속 반복 재생

# 아래 두 곳만 바꾸면 원하는 파형을 만들 수 있음. x는 실제 경과 시간(ms, 한 주기 시작을 0으로
# 봤을 때)이고, 함수가 돌려준 값이 그대로 duty(0-255)로 나감. 진폭/기준선도 함수 안에서 직접
# 표현(예: 128 기준 ±100이면 `128 + (...) * 100`). x_range의 폭(x_max - x_min)이 곧 한
# 주기의 실제 길이(ms)가 됨.
#   사인파(주기 2000ms)  : lambda x: math.sin(x / 2000 * math.pi) * 255, x_range = (0, 2000)
#   삼각파(주기 1000ms)  : lambda x: 255 - abs(x - 500) / 500 * 255,     x_range = (0, 1000)
#   톱니파(주기 1000ms)  : lambda x: x / 1000 * 255,                    x_range = (0, 1000)
#   사각파(주기 800ms)   : lambda x: 255 if x < 400 else 0,             x_range = (0, 800)
WAVE_FUNC = lambda x: 255 * math.exp(-((x - 500) ** 2) / (2 * 150 ** 2))  # 1. 수학 함수 — x(ms) -> duty(0-255)
WAVE_X_RANGE = (0, 1000)  # 2. 함수 범위(ms) — 한 주기의 실제 길이. x는 이 구간(ms)을 반복해서 움직임

RUN_SECONDS = 5  # Peltier_duration_ms 혹은 Wave_WINDOW_ms # 스크립트가 대기하는 시간(초) — 이 시간 끝나면 정지하고 종료
# ===================================


def build_wave(
    window_ms: int,
    step_ms: int,
    *,
    func,
    x_range: tuple[float, float],
) -> list[int]:
    """임의 파형을 duty(0-255) 리스트로 만든다.

    x는 실제 경과 시간(ms, 한 주기 시작을 x_range[0]으로 봤을 때)이고, func(x)가 돌려준
    값이 그대로 duty로 쓰인다(0-255 밖 값은 clamp됨). 한 주기의 실제 길이는
    x_range[1] - x_range[0](ms)이고, window_ms를 다 채울 때까지 이 주기가 반복된다.
    """
    x_min, x_max = x_range
    period_ms = x_max - x_min
    n_steps = max(1, window_ms // step_ms)
    levels = []
    for i in range(n_steps):
        t_ms = i * step_ms
        x = x_min + (t_ms % period_ms)  # 한 주기 내 실제 경과 시간(ms)
        levels.append(round(max(0, min(255, func(x)))))
    levels.append(round(max(0, min(255, func(x_min)))))  # 반복 끝에서 주기 시작으로 매끄럽게 복귀
    return levels


def main() -> None:
    h = HapticBleClient()
    print("[XIAO] 'EMO-Haptic' 스캔/연결 중...")
    h.open()
    print("[XIAO] 연결됨")

    try:
        print(
            f"[XIAO] Peltier1 duty={PELTIER1_DUTY} dir={PELTIER1_DIRECTION} "
            f"{PELTIER1_DURATION_MS}ms / Peltier2 duty={PELTIER2_DUTY} dir={PELTIER2_DIRECTION} "
            f"{PELTIER2_DURATION_MS}ms 구동"
        )
        h.send_haptic_command(
            peltier1_duty=PELTIER1_DUTY,
            peltier1_direction=PELTIER1_DIRECTION,
            peltier1_duration_ms=PELTIER1_DURATION_MS,
            peltier2_duty=PELTIER2_DUTY,
            peltier2_direction=PELTIER2_DIRECTION,
            peltier2_duration_ms=PELTIER2_DURATION_MS,
            erm_duty=ERM_DUTY if ERM_MODE == "plain" else 0,
            erm_duration_ms=ERM_DURATION_MS if ERM_MODE == "plain" else 0,
        )

        if ERM_MODE == "plain":
            print(f"[XIAO] ERM duty={ERM_DUTY} {ERM_DURATION_MS}ms 구동")
        elif ERM_MODE == "wave":
            wave = build_wave(
                WAVE_WINDOW_MS,
                WAVE_STEP_MS,
                func=WAVE_FUNC,
                x_range=WAVE_X_RANGE,
            )
            print(f"[XIAO] ERM 파형 업로드 중 ({len(wave)}샘플, {WAVE_STEP_MS}ms 간격, repeat={WAVE_REPEAT})...")
            h.upload_erm_wave(wave, step_ms=WAVE_STEP_MS, repeat=WAVE_REPEAT, autoplay=True)
        else:
            raise ValueError(f"알 수 없는 ERM_MODE: {ERM_MODE!r} (plain 또는 wave)")

        print(f"[XIAO] {RUN_SECONDS}초 대기...")
        time.sleep(RUN_SECONDS)
    finally:
        if ERM_MODE == "wave":
            h.stop_erm_wave()
        h.close()
        print("완료.")


if __name__ == "__main__":
    main()
