"""Arduino 햅틱 펌웨어와의 Serial JSON 통신을 담당하는 얇은 클라이언트.

프로토콜: USB Serial 115200bps, JSON 한 줄(개행 구분).
스키마는 반드시 firmware의 include/HapticProtocol.h와 맞아야 함
(PlatformIO 프로젝트: /Users/groo/Documents/PlatformIO/Projects/EMO,
심볼릭 링크: 아두이노제어코드/firmware).

pip install pyserial (또는 requirements-haptic.txt) 필요 — 기존 setup.py는 건드리지 않음.
"""
from __future__ import annotations

import json
import time
from typing import Optional

import serial

PROTOCOL_VERSION = 1


class HapticSerialClient:
    def __init__(self, port: str, baud: int = 115200, timeout: float = 1.0):
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._ser: Optional[serial.Serial] = None

    def open(self) -> None:
        self._ser = serial.Serial(self._port, self._baud, timeout=self._timeout)
        # Nano ESP32는 시리얼 포트가 열릴 때 리셋되는 경우가 있어, 펌웨어의 부팅/안정화
        # 시퀀스(원칙 5)가 끝날 때까지 여유를 둔다.
        time.sleep(2.0)

    def close(self) -> None:
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def send_haptic_command(
        self,
        *,
        emotion: str,
        valence: float,
        arousal: float,
        peltier_intensity: float,
        peltier_direction: int,
        peltier_duration_ms: int,
        erm_intensity: float,
        erm_duration_ms: int,
    ) -> None:
        if self._ser is None:
            raise RuntimeError("HapticSerialClient.open()을 먼저 호출해야 함")

        payload = {
            "protocol_version": PROTOCOL_VERSION,
            "emotion": emotion,
            "valence": valence,
            "arousal": arousal,
            "actuator_params": {
                "peltier": {
                    "intensity": peltier_intensity,
                    "direction": peltier_direction,
                    "duration_ms": peltier_duration_ms,
                },
                "erm": {
                    "intensity": erm_intensity,
                    "duration_ms": erm_duration_ms,
                },
            },
        }
        line = json.dumps(payload) + "\n"
        self._ser.write(line.encode("utf-8"))
