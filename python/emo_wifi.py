"""
EMO를 WiFi에 연결시키기 (BLE) — 2026-06-18

EMO에 BLE로 연결한 뒤, WiFi 정보(SSID/비밀번호)를 보내 EMO를 WiFi에 붙인다.
WiFi에 한 번 붙으면 EMO는 BLE를 끊어도 WiFi 연결을 유지하므로,
그 다음에 emo_eye.py(이미지 표시)가 동작할 수 있게 된다.

왜 필요한가
  emo_eye.py 의 set_eye 는 'EMO가 노트북의 HTTP 서버에서 이미지를 내려받는' 방식이라,
  EMO가 노트북과 같은 WiFi에 연결돼 있어야 한다. EMO가 WiFi에 없으면 이미지가 안 떴다.

⚠️ 주의
  - EMO는 5GHz WiFi를 지원하지 않는다. 반드시 '2.4GHz' WiFi 정보를 입력할 것.
  - 노트북도 같은 2.4GHz WiFi에 있어야 (나중에 emo_eye.py 가 동작) 한다.
  - 이 명령은 JSON 채널(0xBB 0xAA)을 쓴다. customize_req 는 fw3.x에서 통과했지만
    wifi_set 이 통과하는지는 실행해 봐야 안다. 안 되면 폰 EMO 앱으로 WiFi를 설정한 뒤
    앱을 끄고(=BLE 해제) emo_eye.py 를 돌리면 된다.

사용법
  python3 emo_wifi.py
    → 실행 중 SSID 와 비밀번호를 입력받는다 (비밀번호는 파일에 저장하지 않음).
"""
import asyncio
import getpass
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from emoconnect.EmoConnectManager import EmoConnectManager
from emoconnect.ble.request import WifiSetRequest
from emo_move import connect, _is_connected


async def send_and_capture(ecm, packet: bytes, wait: float = 5.0):
    """JSON 패킷을 보내고 EMO의 BLE 응답(wifi_rsp 등)을 잡아 출력한다."""
    ecm._resonse = None
    await ecm.sendCommand(packet)
    waited = 0.0
    while waited < wait:
        await asyncio.sleep(0.2)
        waited += 0.2
        if getattr(ecm, "_resonse", None) is not None:
            print(f"  ↩︎ EMO 응답: {ecm._resonse}")
            return ecm._resonse
    print("  ↩︎ EMO 응답 없음")
    return None


async def main():
    print("=== EMO WiFi 설정 ===")
    print("※ 반드시 2.4GHz WiFi 정보를 입력하세요 (EMO는 5GHz 미지원).\n")
    ssid = input("WiFi 이름(SSID): ").strip()
    if not ssid:
        print("SSID가 비어 있습니다. 종료합니다.")
        return
    password = getpass.getpass("WiFi 비밀번호(입력해도 화면에 안 보임): ")

    ecm = await connect()
    if ecm is None:
        return

    try:
        print(f"\n[WiFi] '{ssid}' 로 연결 정보 전송 중...")
        packet = WifiSetRequest.setWifi(ssid, password)
        await send_and_capture(ecm, packet, wait=8.0)

        if not _is_connected(ecm):
            print("⚠️  EMO가 연결을 끊었습니다. (wifi_set 이 fw3.x에서 거부됐을 수 있음)")
            print("    => 폰 EMO 앱으로 WiFi를 설정한 뒤, 앱을 끄고 emo_eye.py 를 실행하세요.")
            return

        print("\nEMO가 WiFi에 접속을 시도하는지 추가로 10초 관찰합니다...")
        for _ in range(20):
            await asyncio.sleep(0.5)
            if getattr(ecm, "_resonse", None) is not None:
                print(f"  ↩︎ EMO 추가 응답: {ecm._resonse}")
                ecm._resonse = None
            if not _is_connected(ecm):
                print("⚠️  관찰 중 EMO가 연결을 끊었습니다.")
                break

        print("\n[완료] EMO의 화면에서 WiFi 연결 표시(예: WiFi 아이콘)를 확인하세요.")
        print("       WiFi가 연결됐다면, 이제 'python3 emo_eye.py' 로 이미지 표시를 시도할 수 있습니다.")
    finally:
        try:
            if _is_connected(ecm):
                await ecm.disconnect()
                print("연결을 종료했습니다.")
        except Exception as e:
            print(f"(종료 중 무시된 예외: {e})")


if __name__ == "__main__":
    asyncio.run(main())
