"""아두이노(XIAO nRF52840) 햅틱 펌웨어와의 BLE(Nordic UART Service) JSON 통신 클라이언트.

프로토콜: BLE GATT NUS(6E400001-...), JSON 한 줄(개행 구분) — haptic_serial.py/haptic_wifi.py와
스키마 동일, 전송 계층만 바뀐 것. XIAO nRF52840엔 WiFi가 없어 NetworkTransport가 BLE로
교체됐음(firmware: /Users/groo/Documents/PlatformIO/Projects/EMO, NetworkTransport.cpp).

bleak는 근본적으로 asyncio 기반이라, 이 클라이언트는 전용 백그라운드 스레드에서 자체
이벤트루프를 돌리고 open()/close()/send_haptic_command()를 그 루프로 위임하는 동기(블로킹)
래퍼로 노출한다 — haptic_dispatch.py가 asyncio.to_thread로 그대로 호출해서 씀.

Peltier는 이제 모듈별 독립 제어라 send_haptic_command()도 peltier1_*/peltier2_*로 나뉘어
있음(펌웨어 HapticProtocol.h의 actuator_params.p1/p2와 대응). ERM은 하드웨어가 항상 두
채널을 미러링해서 구동하므로 여기서도 하나만 받음.

와이어 JSON의 키는 BLE 페이로드 크기를 줄이려고 축약돼 있음(pv/act/p1/p2/i/dir/ms —
HapticProtocol.h 참고). emo/val/aro 필드는 펌웨어가 파싱만 하고 실제로 쓰지 않아서 아예
보내지 않음(생략해도 ArduinoJson 기본값 연산자로 정상 파싱됨).

send_haptic_command() 외에 upload_erm_wave()/play_erm_wave()/stop_erm_wave()도 제공함 —
ERM 파형(예: 오디오 엔벨로프)을 펌웨어 RAM에 통째로 올려두고 펌웨어가 로컬 타이머로
재생하게 하는 것("t":"wb"/"wc"/"wp"/"ws" 명령, WavePlayer.h 참고). send_haptic_command()로
매 스텝마다 BLE를 왕복하는 것보다 훨씬 매끄럽게 재생됨.
"""
from __future__ import annotations

import asyncio
import json
import threading
from typing import List, Optional

from bleak import BleakClient, BleakScanner

PROTOCOL_VERSION = 1

NUS_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # PC -> XIAO (write)
NUS_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # XIAO -> PC (notify, 디버그 로깅용)

# 협상된 BLE MTU를 넘는 한 번의 write는 조용히 잘리거나 유실될 수 있음(실측으로 확인됨 —
# peltier1/peltier2 추가로 페이로드가 ~190B에서 ~284B로 늘어나자 개행이 아예 도착 안 해서
# 펌웨어 readLine()이 계속 대기만 하는 문제가 발생했음). 안전하게 작은 청크로 나눠 순서대로
# 여러 번 write — 펌웨어는 bleuart에서 바이트 단위로 누적해 재조립하므로 문제없음.
WRITE_CHUNK_SIZE = 100

# 파형 업로드("wc") 한 줄(JSON 한 줄 = 펌웨어 라인 버퍼 한도, NetworkTransport.cpp의
# LINE_BUFFER_SIZE=512)에 담는 duty 샘플 개수. 100개면 값이 전부 3자리(최대 255)여도
# 대략 430바이트 선이라 여유 있음. WRITE_CHUNK_SIZE(BLE 한 번의 write 크기)와는 다른
# 레이어의 청크임 — 이건 그보다 큰 JSON 한 줄을 다시 WRITE_CHUNK_SIZE로 쪼개 전송함.
WAVE_CHUNK_SAMPLES = 100


class HapticBleClient:
    def __init__(self, device_name: str = "EMO-Haptic", timeout: float = 15.0):
        self._device_name = device_name
        self._timeout = timeout
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._client: Optional[BleakClient] = None

    def open(self) -> None:
        ready = threading.Event()
        errors: List[BaseException] = []

        def _run_loop() -> None:
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._connect())
            except BaseException as e:  # noqa: BLE001 — 스레드 경계 넘겨서 open()에 다시 던짐
                errors.append(e)
            finally:
                ready.set()
            if not errors:
                loop.run_forever()

        self._thread = threading.Thread(target=_run_loop, daemon=True)
        self._thread.start()
        if not ready.wait(self._timeout + 5.0):
            raise RuntimeError("HapticBleClient 연결이 시간 내에 끝나지 않았습니다.")
        if errors:
            raise errors[0]

    async def _connect(self) -> None:
        device = await BleakScanner.find_device_by_name(self._device_name, timeout=self._timeout)
        if device is None:
            raise RuntimeError(f"'{self._device_name}' 기기를 찾지 못했습니다(광고 중인지 확인).")
        client = BleakClient(device)
        await client.connect()
        await client.start_notify(NUS_TX_CHAR_UUID, self._on_notify)
        self._client = client

    def _on_notify(self, _, data: bytearray) -> None:
        text = data.decode(errors="replace").rstrip()
        if text:
            print(f"[XIAO->PC] {text}")

    async def _write_chunked(self, data: bytes) -> None:
        for i in range(0, len(data), WRITE_CHUNK_SIZE):
            await self._client.write_gatt_char(NUS_RX_CHAR_UUID, data[i:i + WRITE_CHUNK_SIZE])

    def _send_payload(self, payload: dict) -> None:
        if self._client is None or self._loop is None:
            raise RuntimeError("HapticBleClient.open()을 먼저 호출해야 함")
        line = json.dumps(payload, separators=(",", ":")) + "\n"
        fut = asyncio.run_coroutine_threadsafe(
            self._write_chunked(line.encode("utf-8")),
            self._loop,
        )
        fut.result(timeout=self._timeout)

    def close(self) -> None:
        if self._loop is None or self._client is None:
            return
        fut = asyncio.run_coroutine_threadsafe(self._client.disconnect(), self._loop)
        try:
            fut.result(timeout=self._timeout)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=self._timeout)
            self._loop = None
            self._client = None

    def send_haptic_command(
        self,
        *,
        peltier1_duty: int,
        peltier1_direction: int,
        peltier1_duration_ms: int,
        peltier2_duty: int,
        peltier2_direction: int,
        peltier2_duration_ms: int,
        erm_duty: int,
        erm_duration_ms: int,
    ) -> None:
        """duty는 0-255 PWM duty 값 그대로(양자화 없음). Peltier는 펌웨어
        SafetyGuard.cpp의 PELTIER_DUTY_SAFETY_CAP(130)까지만 적용되고 그 이상은
        펌웨어에서 클램프됨. ERM은 상한 없이 0-255 그대로 나감.

        emotion/valence/arousal는 펌웨어가 파싱만 하고 실제 액추에이터 제어에는
        쓰지 않아서(HapticStateMachine.cpp 참고) 제거함 — ArduinoJson의 기본값
        연산자(`doc["emo"] | ""`)로 필드가 아예 없어도 파싱은 정상 동작함."""
        self._send_payload({
            "pv": PROTOCOL_VERSION,
            "act": {
                "p1": {
                    "i": peltier1_duty,
                    "dir": peltier1_direction,
                    "ms": peltier1_duration_ms,
                },
                "p2": {
                    "i": peltier2_duty,
                    "dir": peltier2_direction,
                    "ms": peltier2_duration_ms,
                },
                "erm": {
                    "i": erm_duty,
                    "ms": erm_duration_ms,
                },
            },
        })

    def upload_erm_wave(
        self,
        duty_values: list[int],
        *,
        step_ms: int,
        repeat: bool = False,
        autoplay: bool = True,
    ) -> None:
        """ERM 파형 전체를 펌웨어 RAM(WavePlayer, ERM_WAVE_BUFFER_CAPACITY=8192 샘플)에
        업로드하고, autoplay면 곧바로 재생을 시작한다.

        BLE 왕복 없이 펌웨어가 로컬 타이머(step_ms 간격)로 duty_values를 순서대로
        재생하므로 send_haptic_command()를 매 스텝 반복 호출하는 것보다 훨씬 매끄럽다
        (erm_ramp_test.cpp와 동일한 원리 — WavePlayer.h 참고). repeat=True면 끝에서
        처음으로 되돌아가 반복 재생하고, 펌웨어 워치독(MAX_DURATION_MS)이 PC가
        오래 침묵하면 강제로 멈춘다.

        Peltier와는 무관 — Peltier 제어는 send_haptic_command()로 별도 전송."""
        n = len(duty_values)
        if n == 0:
            raise ValueError("duty_values가 비어 있음")
        if n > 8192:
            raise ValueError(f"duty_values가 펌웨어 버퍼 용량(8192)을 초과함: {n}")

        self._send_payload({"pv": PROTOCOL_VERSION, "t": "wb", "n": n, "ms": step_ms, "rep": 1 if repeat else 0})
        for offset in range(0, n, WAVE_CHUNK_SAMPLES):
            chunk = duty_values[offset:offset + WAVE_CHUNK_SAMPLES]
            self._send_payload({"pv": PROTOCOL_VERSION, "t": "wc", "off": offset, "d": chunk})
        if autoplay:
            self.play_erm_wave()

    def play_erm_wave(self) -> None:
        """업로드해둔 ERM 파형 재생을 (재)시작한다(처음부터)."""
        self._send_payload({"pv": PROTOCOL_VERSION, "t": "wp"})

    def stop_erm_wave(self) -> None:
        """ERM 파형 재생을 중단하고 ERM을 끈다."""
        self._send_payload({"pv": PROTOCOL_VERSION, "t": "ws"})
