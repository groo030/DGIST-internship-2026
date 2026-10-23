"""
EMO enterApp(appId) 범위 스윕 (BLE, 바이너리 명령) — 2026-07-23

배경: waringer/emo 문서에 캡처된 appId는 1(modern ludo), 2(rhythmatic tap),
3(angry emo), 4(treasure hunt, 확인됨), 6(dance repeat) 뿐이었다.
실측 결과 이 펌웨어에서는 4번만 반응하고 1,2,3,5,6은 전부 무반응이었다.
appId 매핑이 이 펌웨어에서 바뀌었을 가능성을 보고, 문서에 없는 번호
(0, 7~15)까지 넓혀서 반응이 있는 appId가 더 있는지 찾는다.

한 번 연결한 상태에서 appId를 하나씩 바꿔가며 진입→관찰→종료를 반복한다.

사용법
    python3 emo_appid_sweep.py                  # 0, 7~15 기본 범위
    python3 emo_appid_sweep.py --range 0 20      # 범위 직접 지정
    python3 emo_appid_sweep.py --wait 5          # 각 appId 관찰 시간(초)
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from emoconnect.ble.command import CommandUtil
from emo_move import connect, _is_connected

DEFAULT_APP_IDS = [0, 7, 8, 9, 10, 11, 12, 13, 14, 15]


def on_command(ecm, command):
    raw = bytes(getattr(ecm, "_packet", b"") or b"")
    print(f"    📡 [상태 이벤트 수신] {command}  raw={raw.hex()}")


async def try_app_id(ecm, app_id: int, wait: float):
    print(f"\n[appId={app_id}] 진입 시도...")
    await ecm.sendCommand(CommandUtil.clear())
    await asyncio.sleep(0.4)
    await ecm.sendCommand(CommandUtil.enterApp(app_id))
    await asyncio.sleep(0.4)
    await ecm.sendCommand(CommandUtil.startGame())
    await asyncio.sleep(0.4)

    if not _is_connected(ecm):
        print(f"  ⚠️  appId={app_id} 진입 중 연결이 끊겼습니다 (거부됐을 수 있음).")
        return False

    print(f"  → {wait}초간 관찰하세요 (반응 있으면 appId 메모!)")
    await asyncio.sleep(wait)

    if not _is_connected(ecm):
        print(f"  ⚠️  appId={app_id} 관찰 중 연결이 끊겼습니다.")
        return False

    await ecm.sendCommand(CommandUtil.exitApp())
    await asyncio.sleep(0.4)
    return True


async def main():
    parser = argparse.ArgumentParser(description="EMO enterApp(appId) 범위 스윕")
    parser.add_argument(
        "--range", nargs=2, type=int, metavar=("START", "END"), default=None,
        help="시도할 appId 범위 [START, END) — 예: --range 0 20",
    )
    parser.add_argument(
        "--wait", type=float, default=4.0,
        help="각 appId 진입 후 관찰 시간(초, 기본 4)",
    )
    args = parser.parse_args()
    app_ids = list(range(args.range[0], args.range[1])) if args.range else DEFAULT_APP_IDS

    print(f"[준비] 시도할 appId {len(app_ids)}개: {app_ids}")

    ecm = await connect()
    if ecm is None:
        return

    ecm.setCommandCallback(lambda command: on_command(ecm, command))

    try:
        for app_id in app_ids:
            if not _is_connected(ecm):
                print("⚠️  EMO 연결이 끊겨서 스윕을 중단합니다. 재연결이 필요합니다.")
                break
            ok = await try_app_id(ecm, app_id, args.wait)
            if not ok:
                print("    (재연결 없이는 계속할 수 없어 스윕을 종료합니다.)")
                break
    finally:
        try:
            if _is_connected(ecm):
                await ecm.sendCommand(CommandUtil.exitApp())
                await ecm.disconnect()
                print("\n연결을 종료했습니다.")
            else:
                print("\n(EMO가 이미 연결을 끊은 상태입니다.)")
        except Exception as e:
            print(f"(종료 중 무시된 예외: {e})")


if __name__ == "__main__":
    asyncio.run(main())
