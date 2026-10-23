"""EMO 얼굴에 이미지 띄우기 + XIAO 햅틱(Peltier 냉/열 + ERM 램프)을 발사하는 테스트.

명령 수신 즉시 구동: 얼굴 이미지 표시 + Peltier 1(냉감)/2(열감), HOLD_DURATION_MS까지 유지.
ERM_DELAY_MS만큼 늦게 시작: ERM이 ERM_RAMP_WINDOW_MS 동안 0→255→0을 오가는 사인파(sine wave)를
ERM_RAMP_CYCLES번 반복 — "0부터 255까지 높아졌다 다시 0까지 낮아지는 걸 반복". 파형 배열을
펌웨어 WavePlayer에 한 번에 업로드해 로컬 타이머로 재생하므로(upload_erm_wave(), haptic_ble.py
참고) 매 스텝 BLE 왕복 없이 매끄럽게 나간다.

emo_eye.py의 이미지 표시 로직(BLE customize_req + WiFi raw TCP 서버)과
haptic_ble.HapticBleClient(BLE NUS)를 asyncio.gather로 동시에 실행한다 — EMO 얼굴 BLE
연결, XIAO 햅틱 BLE 연결, 이미지 전송용 로컬 WiFi TCP 서버까지 세 가지가 동시에 돈다.

펌웨어는 이제 Off/Low/High 양자화 없이 PC가 지정한 duty(0-255)를 그대로 받는다(Peltier는
SafetyGuard.cpp의 PELTIER_DUTY_SAFETY_CAP=150까지만 클램프, ERM은 상한 없음) — 그래서 ERM을
계단식 3단계가 아니라 ERM_RAMP_STEP_MS 간격으로 잘게 쪼갠 진짜 사인파로 구동할 수 있다.
ERM_RAMP_STEP_MS(100ms=10Hz)는 ERM 자체의 기계적 응답 속도를 감안한 재생 해상도 — 더 촘촘히
잡아봐야 모터가 못 따라가서 체감상 의미가 없다(WavePlayer 로컬 재생이라 BLE 왕복 지연은 더는
고려 대상 아님).

사용법:
    ./venv/bin/python3 emo_face_and_haptic_test.py [이미지경로]
    (경로 생략 시 기본값: ~/Desktop/DGIST/emo_heat_cold.png)

실행 조건은 emo_eye.py와 동일 — Terminal.app 블루투스 권한,
EMO 공식 앱 종료, EMO와 이 컴퓨터가 같은 2.4GHz WiFi에 있을 것, 포트 9090 인바운드 허용.
"""
from __future__ import annotations

import asyncio
import math
import os
import sys
import threading

# 저장소의 src 폴더를 import 경로에 추가 (pip install 없이 실행) — 기존 스크립트와 동일 패턴.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from emo_eye import (
    EMO_HTTP_PORT,
    RawImageHandler,
    ReuseTCPServer,
    encode_json,
    get_local_ip,
    normalize_for_emo,
    restore_normal_eyes,
    send_and_capture,
)
from emo_move import _is_connected
from emo_move import connect as connect_emo
from haptic_ble import HapticBleClient

DEFAULT_IMAGE_PATH = os.path.expanduser("~/Desktop/DGIST/emo_heat_cold.png")

HOLD_DURATION_MS = 30000  # Peltier 유지 시간(=전체 시나리오 길이) — 명령 수신 즉시 구동.
ERM_DELAY_MS = 2500  # ERM 램프는 이만큼 늦게 시작 — Peltier 둘과 얼굴 표시는 명령 수신 즉시 구동.
ERM_RAMP_WINDOW_MS = 6500  # ERM 램프 자체의 길이는 그대로 유지(HOLD_DURATION_MS와 더는 연동 안 함).

PELTIER1_DUTY = 110
PELTIER2_DUTY = 110

ERM_RAMP_STEP_MS = 100  # ERM 사인파 갱신 주기(10Hz) — BLE 왕복/ERM 기계적 응답 한계 고려.
ERM_RAMP_CYCLES = 3  # ERM_RAMP_WINDOW_MS(6.5초) 동안 0->255->0을 몇 번 반복할지.


def _build_erm_sine_wave() -> list[int]:
    """ERM_RAMP_WINDOW_MS 동안 0->255->0을 ERM_RAMP_CYCLES번 반복하는 사인파 duty 목록.

    sin(pi * phase)는 phase가 0->1로 갈 때 0->1->0으로 움직이면서 항상 0 이상이라
    duty(0-255) 범위에 그대로 맞음 — 한 사이클이 "반 주기 사인"인 셈."""
    n_steps = max(1, ERM_RAMP_WINDOW_MS // ERM_RAMP_STEP_MS)
    cycle_ms = ERM_RAMP_WINDOW_MS / ERM_RAMP_CYCLES
    levels = []
    for i in range(n_steps):
        t_ms = i * ERM_RAMP_STEP_MS
        phase = (t_ms % cycle_ms) / cycle_ms  # 0.0-1.0, 한 사이클 내 위치
        sine = math.sin(math.pi * phase)  # 0 -> 1 -> 0
        levels.append(round(sine * 255))
    levels.append(0)  # 마지막은 항상 0으로 마무리
    return levels


ERM_RAMP_LEVELS = _build_erm_sine_wave()


async def show_face(ecm, ip: str, img_bytes: bytes) -> None:
    print("\n[EMO] customize_req(op:in) — 커스터마이즈 모드 진입")
    await send_and_capture(ecm, encode_json({"data": {"op": "in"}, "type": "customize_req"}), wait=6.0)
    if not _is_connected(ecm):
        print("❌ EMO가 연결을 끊었습니다 — 얼굴 표시 실패.")
        return

    set_eye = {
        "data": {
            "image": {"length": len(img_bytes), "name": "sticker.png", "tran": 100},
            "op": "set_eye",
            "server": {"ip": ip, "port": EMO_HTTP_PORT},
        },
        "type": "customize_req",
    }
    print(f"[EMO] set_eye 전송 — {ip}:{EMO_HTTP_PORT}에서 이미지를 받아가게 함")
    await send_and_capture(ecm, encode_json(set_eye), wait=3.0)


async def fire_haptic(haptic: HapticBleClient) -> None:
    """Peltier 1/2는 즉시 구동해 HOLD_DURATION_MS까지 유지하고, ERM은 ERM_DELAY_MS 뒤부터
    ERM_RAMP_LEVELS(사인파)를 펌웨어 WavePlayer에 통째로 업로드해 로컬 재생한다
    (upload_erm_wave(), haptic_ble.py 참고).

    act 경로로 ERM duty를 지정하면 재생 중이던 파형이 취소되므로(WavePlayer.h 참고),
    Peltier는 여기서 HOLD_DURATION_MS 전체를 한 번만 지정해두고 이후로는 act를 다시
    보내지 않는다 — 그래서 예전처럼 스텝마다 Peltier duration을 재계산해 재전송할 필요가
    없어졌다.
    """
    print(f"[XIAO] Peltier1=냉감/Peltier2=열감(둘 다 duty={PELTIER1_DUTY}) 즉시 구동, "
          f"ERM은 {ERM_DELAY_MS}ms 뒤부터 {ERM_RAMP_WINDOW_MS}ms 동안 사인파(0->255->0) "
          f"{ERM_RAMP_CYCLES}회 반복 ({ERM_RAMP_STEP_MS}ms 간격, WavePlayer 로컬 재생)")
    await asyncio.to_thread(
        haptic.send_haptic_command,
        peltier1_duty=PELTIER1_DUTY,
        peltier1_direction=-1,  # 냉각
        peltier1_duration_ms=HOLD_DURATION_MS,
        peltier2_duty=PELTIER2_DUTY,
        peltier2_direction=1,  # 가열
        peltier2_duration_ms=HOLD_DURATION_MS,
        erm_duty=0,  # Off — 아직 시작 안 함
        erm_duration_ms=0,
    )

    await asyncio.sleep(ERM_DELAY_MS / 1000.0)

    await asyncio.to_thread(
        haptic.upload_erm_wave,
        ERM_RAMP_LEVELS,
        step_ms=ERM_RAMP_STEP_MS,
        repeat=False,
        autoplay=True,
    )
    await asyncio.sleep(ERM_RAMP_WINDOW_MS / 1000.0)


async def main() -> None:
    image_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE_PATH
    if not os.path.isfile(image_path):
        print(f"❌ 파일을 찾을 수 없습니다: {image_path}")
        return

    with open(image_path, "rb") as f:
        raw = f.read()
    img_bytes = normalize_for_emo(raw)
    print(f"[이미지] {image_path} 준비 완료 ({len(img_bytes)} bytes)")

    print("[EMO] BLE 연결 시도 중...")
    ecm = await connect_emo()
    if ecm is None:
        print("[EMO] 연결 실패 — 얼굴 표시는 건너뛰고 햅틱만 진행합니다.")

    haptic = HapticBleClient()
    print("[XIAO] 'EMO-Haptic' 스캔/연결 중...")
    haptic.open()
    print("[XIAO] 연결됨")

    ip = get_local_ip()
    RawImageHandler.data = img_bytes
    httpd = None
    try:
        httpd = ReuseTCPServer(("0.0.0.0", EMO_HTTP_PORT), RawImageHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        print(f"[서버] raw TCP 이미지 서버 시작: {ip}:{EMO_HTTP_PORT}")
    except OSError as e:
        print(f"❌ 포트 {EMO_HTTP_PORT} 사용 중입니다 ({e}).")
        print(f"   (정리: lsof -tiTCP:{EMO_HTTP_PORT} -sTCP:LISTEN | xargs kill -9)")
        haptic.close()
        if ecm is not None and _is_connected(ecm):
            await ecm.disconnect()
        return

    try:
        # 얼굴 표시(EMO BLE+WiFi)와 햅틱(XIAO BLE)을 동시에 발사.
        # fire_haptic()이 ERM 램프 루프 때문에 내부적으로 HOLD_DURATION_MS 근처까지
        # 계속 실행되므로, gather()가 끝나는 시점이 곧 전체 유지 시간이 끝나는 시점이다
        # (얼굴도 자연히 같이 맞춰짐 — 별도로 더 기다릴 필요 없음).
        tasks = [asyncio.create_task(fire_haptic(haptic))]
        if ecm is not None:
            tasks.append(asyncio.create_task(show_face(ecm, ip, img_bytes)))
        await asyncio.gather(*tasks)

        if ecm is not None:
            await restore_normal_eyes(ecm, ip)
    finally:
        try:
            await asyncio.to_thread(haptic.stop_erm_wave)
        except Exception as e:
            print(f"(ERM 파형 정지 중 무시된 예외: {e})")
        haptic.close()
        if ecm is not None:
            try:
                if _is_connected(ecm):
                    await ecm.disconnect()
            except Exception as e:
                print(f"(EMO 종료 중 무시된 예외: {e})")
        httpd.shutdown()
        print("연결 종료.")


if __name__ == "__main__":
    asyncio.run(main())
