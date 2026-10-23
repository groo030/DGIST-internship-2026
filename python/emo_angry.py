"""
EMO "Angry Emo" 미니게임 진입 (BLE, 바이너리 명령) — 2026-07-23

처음엔 anim_req(이름 맞추기)로 시도했으나, waringer/emo 리포지토리
(https://github.com/waringer/emo/blob/master/Doc/Bluetooth/README.md)에서
공식 앱이 실제로 보내는 패킷을 캡처한 로그를 보면 "angry"는 anim_req가 아니라
enterApp() 계열의 바이너리 명령(0xDD 0xCC)이었다:

    DDCC xx 0301 0000 ...  // stop play            = exitApp()
    DDCC xx 0302 0100 ...  // play modern ludo      = enterApp(1)
    DDCC xx 0302 0200 ...  // play rhythmatic tap   = enterApp(2)
    DDCC xx 0302 0300 ...  // play angry emo        = enterApp(3)  ← 이거
    DDCC xx 0302 0400 ...  // play treasure hunt    = enterApp(4)  (emo_move.py가 쓰는 것)
    DDCC xx 0302 0600 ...  // play dance repeat     = enterApp(6)

즉 emo_move.py의 이동 모드 진입(clear → enterApp(4) → startGame → ...)과
완전히 같은 메커니즘이고, appId만 3이다. 라이브러리에 이미 있는
CommandUtil.enterApp()/startGame()으로 충분해서 이름을 추측할 필요가 없었다.

"Angry Emo"는 원래 앱에서 사용자가 EMO를 흔들거나 쓰다듬는 것에 반응해
점점 화내는 반응형 미니게임으로 보인다. 그래서 게임 모드 진입 후
statusOnOff(True)를 켜서 BEING_SHAKEN/BEING_PETTED 같은 상태 이벤트가
오는지 관찰한다 (직접 흔들어보면 반응이 커질 가능성이 있음).

실측 결과 (2026-07-23): appId=3으로 진입해도 EMO는 평소와 다른 반응을 보이지 않았다
(Angry Emo 모드에 안 들어감). --app-id로 다른 후보(1,2,5,6)를 찔러보며
어떤 appId가 실제로 무언가를 바꾸는지 먼저 확인이 필요하다.

사용법
    python3 emo_angry.py                # appId=3 (angry emo, 문서 기준)
    python3 emo_angry.py --app-id 1     # 다른 appId 시도 (modern ludo)
    python3 emo_angry.py --app-id 2     # rhythmatic tap
    python3 emo_angry.py --app-id 6     # dance repeat

⚠️ 실행 조건은 emo_move.py와 동일 (Terminal.app 블루투스 권한, 공식 앱 종료,
   충전대에서 내려놓기 등).
"""
import argparse
import asyncio
import os
import sys

# 저장소의 src 폴더를 import 경로에 추가 (pip install 없이 실행)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from emoconnect.ble.command import CommandUtil
from emo_move import connect, _is_connected

ANGRY_EMO_APP_ID = 3
# 문서상 다른 appId들 (실측 결과 3=Angry Emo는 이 펌웨어에서 반응 없음 확인됨)
#   1=modern ludo, 2=rhythmatic tap, 3=angry emo, 4=treasure hunt(검증됨), 6=dance repeat


def on_command(ecm, command):
    """수신된 바이너리 명령을 파싱 결과 + 원본 hex 둘 다 출력한다.
    CommandParser가 모르는 카테고리는 None을 반환하며 원본 바이트를 버리므로,
    ecm._packet(수신 시점의 raw 17바이트)을 직접 읽어서 같이 보여준다."""
    raw = bytes(getattr(ecm, "_packet", b"") or b"")
    print(f"📡 [상태 이벤트 수신] {command}  raw={raw.hex()}")


async def main():
    parser = argparse.ArgumentParser(description="EMO enterApp(appId) 게임 진입 실험")
    parser.add_argument(
        "--app-id", type=int, default=ANGRY_EMO_APP_ID,
        help=f"시도할 appId (기본: {ANGRY_EMO_APP_ID}=angry emo). 1=modern ludo, 2=rhythmatic tap, 4=treasure hunt(검증됨), 6=dance repeat",
    )
    args = parser.parse_args()
    app_id = args.app_id

    ecm = await connect()
    if ecm is None:
        return

    # 초기화 단계에서 오는 패킷도 놓치지 않도록 콜백을 먼저 등록
    ecm.setCommandCallback(lambda command: on_command(ecm, command))

    try:
        print(f"\n[초기화] enterApp({app_id}) 게임 모드 진입 중...")
        # emo_move.py의 검증된 진입 시퀀스(clear→enterApp→startGame→resetting→
        # statusOnOff→chargeLevelOnOff)를 그대로 따르고 appId만 바꾼다.
        await ecm.sendCommand(CommandUtil.clear())
        await asyncio.sleep(0.5)
        await ecm.sendCommand(CommandUtil.enterApp(app_id))
        await asyncio.sleep(0.5)
        await ecm.sendCommand(CommandUtil.startGame())
        await asyncio.sleep(0.5)
        await ecm.sendCommand(CommandUtil.resetting())
        await asyncio.sleep(0.5)
        await ecm.sendCommand(CommandUtil.statusOnOff(True))
        await ecm.sendCommand(CommandUtil.chargeLevelOnOff(True))
        await asyncio.sleep(0.3)

        if not _is_connected(ecm):
            print("⚠️  초기화 중 EMO가 연결을 끊었습니다.")
            print("    => 현재 펌웨어가 이 게임 진입 명령을 거부하는 것으로 보입니다.")
            return
        print("✅ 진입 완료. EMO 화면/모터 반응을 확인하세요.")

        print("\n[관찰] 약 15초간 대기합니다. 실제로 EMO를 흔들거나 쓰다듬어")
        print("       반응(화남 애니메이션)이 커지는지 확인해 보세요. (Ctrl+C로 중단)")
        for _ in range(30):
            await asyncio.sleep(0.5)
            if not _is_connected(ecm):
                print("⚠️  대기 중 EMO가 연결을 끊었습니다.")
                break
    finally:
        try:
            if _is_connected(ecm):
                await ecm.sendCommand(CommandUtil.exitApp())
                await ecm.disconnect()
                print("연결을 종료했습니다.")
            else:
                print("(EMO가 이미 연결을 끊은 상태입니다.)")
        except Exception as e:
            print(f"(종료 중 무시된 예외: {e})")


if __name__ == "__main__":
    asyncio.run(main())
