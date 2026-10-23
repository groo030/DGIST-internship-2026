"""
EMO 댄스/애니메이션 재생 테스트 (BLE, anim_req) — 2026-07-13

목적: AnimationRequest.playEmoDance(n)이 fw3.x에서 실제로 재생되는지 확인한다.
      (JSON 채널이라 sta_req처럼 거부될 수도, customize_req처럼 수락될 수도 있음 — 실행해봐야 안다.)

동작 (3단계)
  [1단계] anim_req {"op":"in"}  → 애니메이션 모드 진입 (anim_rsp 응답 확인)
  [2단계] anim_req {"op":"play","name":댄스이름} → 댄스 재생 (화면/모터 반응 관찰)
  [3단계] anim_req {"op":"out"} → 애니메이션 모드 종료

사용법
  python3 emo_dance.py         # 0번 댄스(d1_EmoDance) 재생
  python3 emo_dance.py 4       # n번 댄스 재생 (0~10)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from emoconnect.ble.request import AnimationRequest
from emo_move import connect, _is_connected

DANCE_LIST = AnimationRequest.DANCE_LIST


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


async def main():
    dance_num = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if not (0 <= dance_num < len(DANCE_LIST)):
        print(f"❌ 댄스 번호는 0~{len(DANCE_LIST) - 1} 사이여야 합니다.")
        return
    dance_name = DANCE_LIST[dance_num]
    print(f"[선택] {dance_num}번 댄스: {dance_name}")

    ecm = await connect()
    if ecm is None:
        return

    try:
        print("\n[1단계] anim_req(op:in) — 애니메이션 모드 진입")
        await send_and_capture(ecm, AnimationRequest.enterAnimationMode())
        if not _is_connected(ecm):
            print("❌ EMO가 연결을 끊었습니다 => fw3.x가 anim_req(op:in)를 거부.")
            return

        print(f"\n[2단계] anim_req(op:play, name:{dance_name}) — 댄스 재생 시도")
        print("   EMO의 화면/모터 반응과 아래 📡 상태 이벤트(DANCING 등)를 확인하세요.")
        await send_and_capture(ecm, AnimationRequest.playEmoDance(dance_num), wait=3.0)

        print("\n[관찰] 약 10초간 대기하며 상태 이벤트를 관찰합니다...")
        for _ in range(20):
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
