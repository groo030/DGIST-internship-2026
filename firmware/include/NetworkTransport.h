#pragma once
#include <Arduino.h>

// Serial(USB) 대신 BLE(Nordic UART Service)로 PC와 JSON 라인을 주고받기 위한 전송 계층.
// 기존 Serial 기반 프로토콜(한 줄 JSON, \n 구분)과 스키마는 동일 — 전송 수단만 교체.
// XIAO nRF52840엔 WiFi가 없어 이전 WiFi/TCP 구현을 대체(이 인터페이스 자체는 무변경이라
// 상위 레이어(HapticStateMachine)는 이 전환을 몰라도 됨). PC 1대(중앙 기기)만 접속한다고
// 가정, 여러 기기 동시 접속은 지원하지 않음.
namespace NetworkTransport {
// BLE 스택 초기화 + NUS(BLEUart) 서비스로 광고 시작.
void begin();

// loop()에서 매번 호출 — 연결 상태 점검 등 non-blocking 유지보수.
void poll();

// 연결돼 있고 개행(\n)까지 도착한 한 줄이 있으면 outLine에 채우고 true 반환.
// 아직 줄이 완성되지 않았으면 내부 버퍼에 누적만 하고 false(블로킹 없음).
bool readLine(String& outLine);

// 중앙 기기로 한 줄 전송(NUS TX notify) + 디버그용으로 USB Serial에도 그대로 출력.
void println(const char* line);
}  // namespace NetworkTransport
