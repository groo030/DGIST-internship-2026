"""LLM 감정 분류로 anger 트리거를 판단하는 테스트 하니스.

사용자 문장을 emotion_classifier.classify_emotion()으로 분류해 anger이면, EMO BLE +
XIAO BLE 동시 발사(dispatch_anger())를 실행한다. 리터럴 키워드("화나" 등
감정 단어 자체) 포함 여부가 아니라, 발언 내용이 EMO 입장에서 화날 만한지를 LLM이 판단함
— 그래서 "진짜 화나 죽겠다" 같은 직접적인 문장이 아니어도(예: 놀리는 말) 트리거된다.

아두이노(XIAO nRF52840)와의 통신은 BLE(Nordic UART Service)로 함 — 그 보드엔 WiFi가 없어서
기존 WiFi(TCP) 방식은 더 이상 안 됨(펌웨어: NetworkTransport.cpp 참고). EMO도 BLE라 PC 하나가
두 BLE 기기(EMO + XIAO)에 동시에 별도 연결을 맺는 구조 — 표준 지원되는 시나리오임.

사용법:
    pip install -r requirements-haptic.txt
    export ANTHROPIC_API_KEY=...   # emotion_classifier.py가 씀
    python3 haptic_chat_harness.py

⚠️ 실행 조건은 emo_move.py와 동일 (Terminal.app 블루투스 권한, 공식 앱 종료,
   EMO가 충전대에서 내려와 있을 것 등).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

# 저장소의 src 폴더를 import 경로에 추가 (pip install 없이 실행) — emo_move.py 등 기존
# 스크립트와 동일한 패턴.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from emo_move import connect as connect_emo
from emotion_classifier import classify_emotion
from haptic_ble import HapticBleClient
from haptic_dispatch import ANIMATION_EXIT_DELAY_S, dispatch_anger, exit_animation_mode


async def _delayed_exit_animation(ecm) -> None:
    """트리거마다 ANIMATION_EXIT_DELAY_S 뒤에 애니메이션 모드를 종료하는 백그라운드 태스크.

    입력 루프를 막지 않도록 asyncio.create_task로 띄워서 쓴다."""
    await asyncio.sleep(ANIMATION_EXIT_DELAY_S)
    try:
        await exit_animation_mode(ecm)
    except Exception as e:
        print(f"(애니메이션 모드 종료 중 무시된 예외: {e})")


async def main(device_name: str) -> None:
    print("[EMO] BLE 연결 시도 중...")
    ecm = await connect_emo()
    if ecm is None:
        print("[EMO] 연결 실패 — EMO 명령은 건너뛰고 XIAO(햅틱)만 계속 진행합니다.")

    haptic = HapticBleClient(device_name)
    print(f"[XIAO] '{device_name}' 스캔/연결 중...")
    haptic.open()
    print("[XIAO] 연결됨")

    print("문장을 입력하세요 (EMO를 화나게 하는 발언이면 트리거, 'quit' 입력 시 종료):")
    loop = asyncio.get_event_loop()
    try:
        while True:
            line = await loop.run_in_executor(None, input, "> ")
            if line.strip().lower() == "quit":
                break

            emotion = await asyncio.to_thread(classify_emotion, line)
            print(f"[감정] {emotion}")

            if emotion == "anger":
                if ecm is not None:
                    print(f"[트리거] EMO BLE devil + XIAO BLE 진동/열 동시 발사 "
                          f"(애니메이션은 {ANIMATION_EXIT_DELAY_S:.1f}초 뒤 자동 종료)")
                else:
                    print("[트리거] XIAO BLE 진동/열만 발사 (EMO 미연결)")
                await dispatch_anger(ecm, haptic)
                if ecm is not None:
                    asyncio.create_task(_delayed_exit_animation(ecm))
    finally:
        try:
            await exit_animation_mode(ecm)
        except Exception as e:
            print(f"(애니메이션 모드 종료 중 무시된 예외: {e})")
        haptic.close()
        if ecm is not None and ecm._client is not None and ecm._client.is_connected:
            await ecm.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM 감정 분류 → EMO BLE + XIAO BLE 동시 디스패치 테스트 하니스")
    parser.add_argument("--device-name", default="EMO-Haptic", help="XIAO의 BLE 광고 이름 (기본: EMO-Haptic)")
    args = parser.parse_args()
    asyncio.run(main(args.device_name))
