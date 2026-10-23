"""
EMO 움직임 제어 (BLE) — 2026-06-18

EMO에 블루투스로 연결한 뒤 이동 명령(앞/뒤/좌/우)을 보낸다.

사용법:
    python3 emo_move.py          # 연결 + 자동 데모(앞→좌→우→뒤돌기) 시퀀스
    python3 emo_move.py drive    # 키보드(WASD)로 실시간 조종
                                 #   W=앞 A=좌 D=우 S=뒤돌기(180°) 스페이스=정지 Q=종료

참고: EMO는 후진(reverse) 기능이 없다(forward/left/right/turn_around만 존재).
그래서 'S' 와 데모의 마지막 단계는 제자리 180° 뒤돌기로 처리한다.

⚠️ 실행 조건 (안 지키면 실패/위험)
    1. macOS 블루투스 권한이 있는 '터미널(Terminal.app)' 에서 실행할 것
       (Terminal.app이 아닌 다른 셸에서 실행하면 권한 문제로 즉시 종료됨)
    2. EMO를 충전대(스케이트보드)에서 내려놓을 것 — 올려두면 움직이지 않음
    3. EMO를 바닥/넓은 곳에 두고 떨어지지 않게 할 것
    4. 폰/태블릿의 EMO 공식 앱을 종료할 것 (BLE는 1:1, 앱이 잡으면 노트북이 못 잡음)
    5. EMO가 깨어 있어 BLE 광고 중일 것

배경: 이 스크립트가 보내는 '이동 명령'은 0xDD 0xCC 바이너리 명령으로,
JSON 상태요청(sta_req)과는 다른 경로다. 현재 펌웨어(3.x)에서 이 명령이
동작하는지 실제로 확인하는 것이 이 코드의 목적이다.
"""
import asyncio
import os
import sys

# 저장소의 src 폴더를 import 경로에 추가 (pip install 없이 실행)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from typing import Any

from bleak import BleakScanner
from emoconnect import EmoConstants
from emoconnect.EmoConnectManager import EmoConnectManager
from emoconnect.ble.command import CommandUtil

EMO_SERVICE_UUID = EmoConstants.SERVICE_UUID.lower()  # 0000ffe0-...

# EMO는 후진(back) 기능이 없다 (basic_move 동작: forward/left/right/turn_around).
# 그래서 's' 는 제자리에서 약 180° 도는 '뒤돌기'로 대체한다.
# EMO 회전 속도에 맞춰 이 값을 조절하면 회전 각도가 바뀐다.
TURN_AROUND_SECONDS = 1.2


def _is_connected(ecm: EmoConnectManager) -> bool:
    return ecm._client is not None and ecm._client.is_connected


async def find_emo_device(timeout: float = 8.0):
    """ffe0 서비스를 타깃 스캔해 가장 신호가 강한 EMO(BLEDevice)를 반환한다.
    (macOS에서 일반 스캔은 서비스 UUID를 숨겨 라이브러리 기본 필터가 실패하므로)"""
    devices = await BleakScanner.discover(
        timeout=timeout, service_uuids=[EMO_SERVICE_UUID], return_adv=True
    )
    best = None  # (rssi, device, name)
    for _addr, (device, adv) in devices.items():
        rssi = adv.rssi if adv.rssi is not None else -999
        if best is None or rssi > best[0]:
            best = (rssi, device, adv.local_name or device.name or "EMO")
    if best is None:
        return None, None
    return best[1], best[2]


async def commandRx(command: Any):
    """EMO가 보내는 0xDDCC 바이너리 명령 수신 콜백 (StatusAlert/ChargeStatus/HuntResponse).
    statusOnOff(True)/chargeLevelOnOff(True) 전송 후 여기로 이벤트가 들어오는지가
    '상태 이벤트를 PC로 받을 수 있는지'의 실제 검증 지점이다."""
    print(f"📡 [상태 이벤트 수신] {command}")


async def connect() -> EmoConnectManager | None:
    print("[연결] EMO 검색 중 (ffe0 타깃 스캔)...")
    device, name = await find_emo_device()
    if device is None:
        print("❌ EMO를 찾지 못했습니다.")
        print("   EMO를 깨우고, 공식 앱을 종료한 뒤 다시 시도하세요.")
        return None

    print(f"[연결] '{name}' 에 연결 시도 중...")
    ecm = EmoConnectManager()
    if not await ecm.connectToEmo(device=device):
        print("❌ 연결에 실패했습니다.")
        return None
    print("✅ EMO에 연결되었습니다!")
    ecm.setCommandCallback(commandRx)
    return ecm


async def enter_drive_mode(ecm: EmoConnectManager) -> bool:
    """이동 제어 모드 진입 시퀀스.
    (movement_example.py 기반: clear → enterApp(4)=탐험/이동 게임 →
     startGame → resetting → 상태 업데이트 ON)"""
    print("[초기화] 이동 제어 모드 진입 중...")
    await ecm.sendCommand(CommandUtil.clear())
    await asyncio.sleep(0.5)
    await ecm.sendCommand(CommandUtil.enterApp(4))
    await asyncio.sleep(0.5)
    await ecm.sendCommand(CommandUtil.startGame())
    await asyncio.sleep(0.5)
    await ecm.sendCommand(CommandUtil.resetting())
    await asyncio.sleep(0.5)
    await ecm.sendCommand(CommandUtil.statusOnOff(True))
    await ecm.sendCommand(CommandUtil.chargeLevelOnOff(True))
    await asyncio.sleep(0.5)

    if not _is_connected(ecm):
        print("⚠️  초기화 중 EMO가 연결을 끊었습니다.")
        print("    => 현재 펌웨어가 BLE 이동 명령을 차단하는 것으로 보입니다.")
        return False
    print("   진입 완료.")
    return True


async def _step(ecm: EmoConnectManager, fn, label: str, seconds: float) -> bool:
    """한 방향으로 seconds 동안 이동 후 정지. 중간 연결 끊김을 감지한다."""
    print(f"  → {label} ({seconds}s)")
    await ecm.sendCommand(fn())
    await asyncio.sleep(seconds)
    await ecm.sendCommand(CommandUtil.stop())
    await asyncio.sleep(0.3)
    if not _is_connected(ecm):
        print(f"⚠️  '{label}' 도중 EMO가 연결을 끊었습니다.")
        return False
    return True


async def turn_around(ecm: EmoConnectManager):
    """제자리에서 약 180° 회전 (EMO에 후진 기능이 없어 뒤돌기로 대체)."""
    await ecm.sendCommand(CommandUtil.right())
    await asyncio.sleep(TURN_AROUND_SECONDS)
    await ecm.sendCommand(CommandUtil.stop())
    await asyncio.sleep(0.3)


async def demo(ecm: EmoConnectManager):
    print("\n[데모] 3초 후 움직임을 시작합니다. EMO가 바닥(넓은 곳)에 있는지 확인하세요!")
    for i in (3, 2, 1):
        print(f"   {i}...")
        await asyncio.sleep(1)

    sequence = [
        (CommandUtil.forward, "앞으로", 1.0),
        (CommandUtil.left, "좌회전", 0.8),
        (CommandUtil.right, "우회전", 0.8),
    ]
    for fn, label, sec in sequence:
        if not await _step(ecm, fn, label, sec):
            return
    # EMO는 후진이 없으므로 마지막은 제자리 뒤돌기로 마무리
    print("  → 뒤돌기(180°)")
    await turn_around(ecm)
    if not _is_connected(ecm):
        print("⚠️  뒤돌기 도중 EMO가 연결을 끊었습니다.")
        return
    print("\n✅ 데모 완료 — BLE 이동 명령이 정상 동작합니다! 🎉")


async def drive(ecm: EmoConnectManager):
    """키보드(WASD)로 실시간 조종. 표준 라이브러리만 사용 (termios raw 입력)."""
    import termios
    import tty

    print("\n[조종 모드]")
    print("  W=앞  A=좌  D=우  S=뒤  |  스페이스/X=정지  |  Q=종료")
    print("  (방향키를 누르면 그 방향으로 계속 이동, 정지하려면 스페이스)")

    loop = asyncio.get_event_loop()
    fd = sys.stdin.fileno()
    old_attr = termios.tcgetattr(fd)
    queue: asyncio.Queue = asyncio.Queue()

    def _on_key():
        queue.put_nowait(sys.stdin.read(1))

    mapping = {
        "w": (CommandUtil.forward, "앞"),
        "a": (CommandUtil.left, "좌"),
        "d": (CommandUtil.right, "우"),
    }

    try:
        tty.setcbreak(fd)
        loop.add_reader(fd, _on_key)
        while True:
            ch = (await queue.get()).lower()
            if ch == "q":
                print("  종료합니다.")
                break
            if ch in mapping:
                fn, label = mapping[ch]
                await ecm.sendCommand(fn())
                print(f"  {label}")
            elif ch == "s":
                # EMO는 후진 명령(back())이 fw3.x에서 동작하지 않는 것으로 확인됨.
                # 데모 모드와 동일하게 제자리 180° 뒤돌기로 대체한다.
                print("  뒤돌기(180°)")
                await turn_around(ecm)
            elif ch in (" ", "x"):
                await ecm.sendCommand(CommandUtil.stop())
                print("  정지")
            if not _is_connected(ecm):
                print("⚠️  EMO가 연결을 끊었습니다.")
                break
    finally:
        loop.remove_reader(fd)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"

    ecm = await connect()
    if ecm is None:
        return

    try:
        if not await enter_drive_mode(ecm):
            return
        if mode == "drive":
            await drive(ecm)
        else:
            await demo(ecm)
    finally:
        # 항상 정지시키고 앱 모드에서 나간 뒤 안전하게 연결 종료
        try:
            if _is_connected(ecm):
                await ecm.sendCommand(CommandUtil.stop())
                await ecm.sendCommand(CommandUtil.exitApp())
                await ecm.disconnect()
                print("연결을 종료했습니다.")
            else:
                print("(EMO가 이미 연결을 끊은 상태입니다.)")
        except Exception as e:
            print(f"(종료 중 무시된 예외: {e})")


if __name__ == "__main__":
    asyncio.run(main())
