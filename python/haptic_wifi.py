"""아두이노 햅틱 펌웨어와의 WiFi(TCP) JSON 통신을 담당하는 얇은 클라이언트.

프로토콜: TCP 소켓, JSON 한 줄(개행 구분) — haptic_serial.py(Serial 버전)와 스키마 동일,
전송 계층만 USB Serial 대신 WiFi TCP로 바뀐 것. 아두이노는 부팅 후 시리얼 모니터(USB)에
자신의 IP를 출력하므로, 그 IP를 여기 host로 넘기면 됨(펌웨어: NetworkTransport.cpp).
"""
from __future__ import annotations

import json
import socket
from typing import Optional

PROTOCOL_VERSION = 1


class HapticWifiClient:
    def __init__(self, host: str, port: int = 3333, timeout: float = 5.0):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._sock: Optional[socket.socket] = None

    def open(self) -> None:
        self._sock = socket.create_connection((self._host, self._port), timeout=self._timeout)

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

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
        if self._sock is None:
            raise RuntimeError("HapticWifiClient.open()을 먼저 호출해야 함")

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
        self._sock.sendall(line.encode("utf-8"))
