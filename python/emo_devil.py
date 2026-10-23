"""
EMO "devil" 애니메이션 재생 (BLE, anim_req) — 2026-07-23

anim_req(op:play, name:"devil")로 확정됨 — emo_anim_sweep.py로 여러 후보
(devil, e_devil, devil_face 등)를 실측한 결과 정확히 "devil"만 반응했다.

참고: name="devil"을 보냈을 때 실제로 재생된 애니메이션은 이름이 같은
"demon"(Cool 카테고리에 별도로 존재)과 동일하게 보였다. 즉 devil이 별도
에셋이 아니라 demon의 별칭이거나, 두 이름이 같은 애니메이션을 가리키는
것으로 추정된다 (미확정 — name="demon"으로 직접 보내 비교해보면 확인 가능).

사용법
    python3 emo_devil.py                # name="devil" (확정)
    python3 emo_devil.py --name xxx     # 다른 이름을 실험하고 싶을 때만

⚠️ 실행 조건은 emo_move.py와 동일 (Terminal.app 블루투스 권한, 공식 앱 종료 등).
"""
import argparse
import asyncio
import os
import sys

# 저장소의 src 폴더를 import 경로에 추가 (pip install 없이 실행)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from emoconnect.ble.config.AnimationConfig import AnimationConfig, Op
from emoconnect.ble.request import AnimationRequest
from emo_move import connect, _is_connected


async def send_and_capture(ecm, packet: bytes, wait: float = 3.0):
    """JSON 패킷을 보내고 EMO의 BLE 응답(anim_rsp 등)을 잡아 출력한다."""
    ecm._resonse = None
    await ecm.sendCommand(packet)
    waited = 0.0
    while waited < wait:
        await asyncio.sleep(0.2)
        waited += 0.2
        if getattr(ecm, "_resonse", None) is not None:
            print(f"  ↩︎ EMO 응답: {ecm._resonse}")
            return ecm._resonse
    print("  ↩︎ EMO 응답 없음 (응답을 보내지 않음)")
    return None


def playAnimationByName(name: str) -> bytes:
    """DANCE_LIST에 없는 임의의 애니메이션 이름으로 재생을 시도한다."""
    return AnimationConfig(op=Op.PLAY, name=name).getRequest()


async def main():
    parser = argparse.ArgumentParser(description="EMO devil 애니메이션 재생 시도")
    parser.add_argument(
        "--name", default="devil",
        help="시도할 애니메이션 이름 (기본: devil)",
    )
    args = parser.parse_args()
    anim_name = args.name

    print(f"[선택] 애니메이션 이름: {anim_name}")

    ecm = await connect()
    if ecm is None:
        return

    try:
        print("\n[1단계] anim_req(op:in) — 애니메이션 모드 진입")
        await send_and_capture(ecm, AnimationRequest.enterAnimationMode())
        if not _is_connected(ecm):
            print("❌ EMO가 연결을 끊었습니다 => fw3.x가 anim_req(op:in)를 거부.")
            return

        print(f"\n[2단계] anim_req(op:play, name:{anim_name}) — 재생 시도")
        print("   EMO의 화면/모터 반응과 아래 📡 상태 이벤트를 확인하세요.")
        await send_and_capture(ecm, playAnimationByName(anim_name), wait=3.0)

        print("\n[관찰] 약 5초간 대기하며 상태 이벤트를 관찰합니다...")
        for _ in range(10):
            await asyncio.sleep(0.5)
            if not _is_connected(ecm):
                print("⚠️  대기 중 EMO가 연결을 끊었습니다.")
                break
    finally:
        try:
            if _is_connected(ecm):
                print("\n[3단계] anim_req(op:out) — 애니메이션 모드 종료")
                await send_and_capture(ecm, AnimationRequest.exitAnimationMode())
                await ecm.disconnect()
                print("연결을 종료했습니다.")
            else:
                print("(EMO가 이미 연결을 끊은 상태입니다.)")
        except Exception as e:
            print(f"(종료 중 무시된 예외: {e})")


if __name__ == "__main__":
    asyncio.run(main())
