#pragma once
#include <ArduinoJson.h>
#include <cstdint>

// 문서 3절 기준 BLE JSON 프로토콜. Peltier는 모듈별 독립 제어라 p1/p2로 분리됨(ERM은 항상
// 미러링이라 하나만 있음). 변경 시 PC 쪽 haptic_ble.py의 페이로드 구성과 반드시 맞춰야 함.
//
// 필드명은 BLE 페이로드 크기를 줄이려고 축약돼 있음(실측으로 라인 버퍼 오버플로를 겪은 뒤
// 여유를 더 벌기 위함 — NetworkTransport.cpp 참고). 와이어 스키마:
//   {"pv":1,"emo":"anger","val":-0.8,"aro":0.9,
//    "act":{"p1":{"i":98,"dir":1,"ms":4000},
//           "p2":{"i":98,"dir":1,"ms":4000},
//           "erm":{"i":255,"ms":1500}}}
// pv=protocol_version, emo=emotion, val=valence, aro=arousal, act=actuator_params,
// i=duty(0-255, 아래 참고), dir=direction, ms=duration_ms.
//
// "i" 필드는 0.0-1.0 intensity가 아니라 PWM duty(0-255)를 그대로 나타낸다 — 예전에는
// ActuatorMap.h가 intensity를 Off/Low/High 3단계로 양자화해서 검증되지 않은 임의 duty가
// 하드웨어에 닿지 않게 막는 안전 계층이었는데, PC가 지정한 duty를 그대로 쓰도록
// 사용자 요청으로 그 계층을 제거함. 대신 SafetyGuard.cpp에서 범위 clamp(0-255)와
// Peltier 상한(과열/과전류 방지, PELTIER_DUTY_SAFETY_CAP)을 건다 — HapticProtocol
// 자체는 값 검증을 하지 않고 그대로 통과시킴.
//
// 최상위 "t" 필드(생략 가능)로 메시지 종류를 나눈다 — 생략 시 기본값은 위 "act"(즉시
// duty 적용/유지) 명령. ERM 파형 로컬 재생(WavePlayer.h)용 명령은 "t"로 구분됨:
//   "t":"wb" (wave_begin) {"pv":1,"t":"wb","n":<샘플수>,"ms":<샘플간격ms>,"rep":0|1}
//   "t":"wc" (wave_chunk) {"pv":1,"t":"wc","off":<시작offset>,"d":[<duty>,...]}
//   "t":"wp" (wave_play)  {"pv":1,"t":"wp"}
//   "t":"ws" (wave_stop)  {"pv":1,"t":"ws"}
// 파싱/디스패치는 HapticStateMachine.cpp가 "t" 값을 보고 이 파일(act) 또는
// WaveProtocol(wave)로 나눠 처리한다 — 이 파일은 "act" 스키마만 다룸.
constexpr uint16_t HAPTIC_PROTOCOL_VERSION = 1;

struct ActuatorRequest {
  float duty = 0.0f;        // 0-255 PWM duty 그대로(0.0-1.0 intensity 아님). 누락 시 0.
  int8_t direction = 0;     // Peltier: -1 냉각 / +1 가열. ERM: 항상 0(방향 없음, 파서가 강제).
  uint32_t durationMs = 0;  // 0 = 다음 명령까지 유지(단, 펌웨어 워치독 상한 적용됨).
};

struct HapticCommand {
  bool valid = false;
  uint16_t protocolVersion = 0;
  char emotion[16] = {0};
  float valence = 0.0f;
  float arousal = 0.0f;
  ActuatorRequest peltier1;
  ActuatorRequest peltier2;
  ActuatorRequest erm;
};

// JSON 한 줄(널 종료 문자열)을 파싱한다. 성공 시 true, result.valid=true.
// 실패 시 false, result.valid=false, errOut(null 허용)에 원인 문자열을 채운다.
bool parseHapticMessage(const char* jsonLine, HapticCommand& result, const char** errOut = nullptr);

// 위와 동일하지만 호출자가 이미 deserializeJson()해둔 문서를 그대로 받는다 — HapticStateMachine이
// "t" 필드로 act/wave 커맨드를 나누기 위해 먼저 한 번 파싱해두는데, 그걸 재사용해 이중 파싱을 피함.
bool parseHapticMessage(JsonVariantConst doc, HapticCommand& result, const char** errOut = nullptr);
