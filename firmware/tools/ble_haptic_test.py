import argparse
import asyncio
import json

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "EMO-Haptic"
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # PC -> XIAO (write)
NUS_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # XIAO -> PC (notify)

# 협상된 BLE MTU를 넘는 한 번의 write는 조용히 잘리거나 유실될 수 있음(실측으로 확인됨 —
# peltier1/peltier2 추가로 페이로드가 길어지자 개행이 아예 도착 안 해서 펌웨어가 계속
# 대기만 하는 문제가 발생했음). 작은 청크로 나눠 순서대로 여러 번 write.
WRITE_CHUNK_SIZE = 100


def parse_args():
    p = argparse.ArgumentParser(description="EMO-Haptic(XIAO) BLE NUS 명령 테스트 도구")
    p.add_argument("--emotion", default="test")
    p.add_argument("--valence", type=float, default=-0.3)
    p.add_argument("--arousal", type=float, default=0.5)

    p.add_argument("--peltier1-intensity", type=float, default=0.5, help="0.0-1.0")
    p.add_argument("--peltier1-direction", choices=["heat", "cool"], default="heat")
    p.add_argument("--peltier1-duration-ms", type=int, default=10000)

    # peltier2를 생략하면 peltier1과 동일하게 미러링 — 대부분의 테스트는 여전히 둘을
    # 같이 쓰고 싶을 때가 많아서, 필요할 때만 --peltier2-*로 따로 지정하면 됨.
    p.add_argument("--peltier2-intensity", type=float, default=None,
                    help="0.0-1.0, 생략 시 --peltier1-intensity와 동일")
    p.add_argument("--peltier2-direction", choices=["heat", "cool"], default=None,
                    help="생략 시 --peltier1-direction과 동일")
    p.add_argument("--peltier2-duration-ms", type=int, default=None,
                    help="생략 시 --peltier1-duration-ms와 동일")

    p.add_argument("--erm-intensity", type=float, default=0.5, help="0.0-1.0")
    p.add_argument("--erm-duration-ms", type=int, default=10000)
    p.add_argument("--device-name", default=DEVICE_NAME)
    args = p.parse_args()

    if args.peltier2_intensity is None:
        args.peltier2_intensity = args.peltier1_intensity
    if args.peltier2_direction is None:
        args.peltier2_direction = args.peltier1_direction
    if args.peltier2_duration_ms is None:
        args.peltier2_duration_ms = args.peltier1_duration_ms
    return args


def build_command(args):
    # 실제 firmware(HapticProtocol.cpp)가 파싱하는 스키마. Peltier는 모듈별 독립 제어라
    # act.p1/p2로 나뉘어 있음(ERM은 하드웨어가 항상 두 채널을 미러링해서 구동하므로 단일
    # 객체 그대로). 키 이름은 BLE 페이로드 크기를 줄이려고 축약돼 있음 — HapticProtocol.h 참고
    # (pv=protocol_version, emo=emotion, val=valence, aro=arousal, act=actuator_params,
    # i=intensity, dir=direction, ms=duration_ms).
    return {
        "pv": 1,
        "emo": args.emotion,
        "val": args.valence,
        "aro": args.arousal,
        "act": {
            "p1": {
                "i": args.peltier1_intensity,
                "dir": 1 if args.peltier1_direction == "heat" else -1,
                "ms": args.peltier1_duration_ms,
            },
            "p2": {
                "i": args.peltier2_intensity,
                "dir": 1 if args.peltier2_direction == "heat" else -1,
                "ms": args.peltier2_duration_ms,
            },
            "erm": {
                "i": args.erm_intensity,
                "ms": args.erm_duration_ms,
            },
        },
    }


def on_notify(_, data: bytearray):
    print(f"[XIAO->PC] {data.decode(errors='replace').rstrip()}")


async def main():
    args = parse_args()
    command = build_command(args)
    # OK 응답 + 가장 긴 duration_ms 경과 후 자동 OFF까지 지켜보기 위한 대기 시간(여유 2초 포함).
    wait_seconds = (
        max(args.peltier1_duration_ms, args.peltier2_duration_ms, args.erm_duration_ms) / 1000.0
        + 2.0
    )

    print(f"'{args.device_name}' 스캔 중...")
    device = await BleakScanner.find_device_by_name(args.device_name, timeout=15.0)
    if device is None:
        print("기기를 못 찾았습니다. 광고 중인지, 이미 다른 기기에 연결돼 있진 않은지 확인하세요.")
        return

    print(f"찾음: {device.address} — 연결 중...")
    async with BleakClient(device) as client:
        print("연결됨.")
        await client.start_notify(NUS_TX_CHAR_UUID, on_notify)

        line = json.dumps(command, separators=(",", ":")) + "\n"
        print(f"[PC->XIAO] {line.rstrip()}")
        data = line.encode("utf-8")
        for i in range(0, len(data), WRITE_CHUNK_SIZE):
            await client.write_gatt_char(NUS_RX_CHAR_UUID, data[i:i + WRITE_CHUNK_SIZE])

        await asyncio.sleep(wait_seconds)
        await client.stop_notify(NUS_TX_CHAR_UUID)
    print("연결 종료.")


if __name__ == "__main__":
    asyncio.run(main())
