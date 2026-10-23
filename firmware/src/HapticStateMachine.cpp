#include "HapticStateMachine.h"

#include <Arduino.h>
#include <ArduinoJson.h>

#include <cstdio>
#include <cstring>

#include "BatteryMonitor.h"
#include "Config.h"
#include "ErmDriver.h"
#include "HapticProtocol.h"
#include "NetworkTransport.h"
#include "PeltierDriver.h"
#include "SafetyGuard.h"
#include "WavePlayer.h"

namespace {
enum class FwState : uint8_t { IDLE, ACTUATING, FAULT };
FwState state = FwState::IDLE;

bool peltier1Active = false;
bool peltier2Active = false;
bool ermActive = false;
bool peltier1Holding = false;
bool peltier2Holding = false;
bool ermHolding = false;
uint32_t peltier1ExpiresAt = 0;
uint32_t peltier2ExpiresAt = 0;
uint32_t ermExpiresAt = 0;
uint32_t lastCommandReceivedAt = 0;

void applyToHardware(const SafeCommand& cmd) {
  // "act" 경로는 항상 ErmDriver를 직접 건드리므로(ermDuty가 0이어도), WavePlayer가 재생
  // 중이었다면 여기서 확실히 넘겨받는다 — 두 경로가 동시에 ErmDriver를 쓰면 안 됨.
  WavePlayer::stop();

  uint8_t peltier1Duty = cmd.peltier1.duty;
  uint8_t peltier2Duty = cmd.peltier2.duty;
  uint8_t ermDuty = cmd.erm.duty;

  // 명령 적용 로그 — USB 연결 시 디버깅용(BLE 단독 운영 시엔 아무 영향 없음, 그냥 출력이 안 보일 뿐).
  Serial.print("[CMD] peltier1 duty=");
  Serial.print(peltier1Duty);
  Serial.print(" dir=");
  Serial.print(cmd.peltier1.direction);
  Serial.print(" | peltier2 duty=");
  Serial.print(peltier2Duty);
  Serial.print(" dir=");
  Serial.print(cmd.peltier2.direction);
  Serial.print(" | erm duty=");
  Serial.print(ermDuty);
  Serial.print(" battLow=");
  Serial.println(BatteryMonitor::isLow());

  PeltierDriver::setOutput1(peltier1Duty, cmd.peltier1.direction);
  PeltierDriver::setOutput2(peltier2Duty, cmd.peltier2.direction);
  delay(PWM_PHASE_OFFSET_MS);  // 원칙 6: Peltier/ERM PWM 시작 시점을 겹치지 않게 함
  ErmDriver::setOutput(ermDuty);

  uint32_t now = millis();
  peltier1Holding = cmd.peltier1.holdUntilNext;
  peltier2Holding = cmd.peltier2.holdUntilNext;
  ermHolding = cmd.erm.holdUntilNext;
  peltier1ExpiresAt = now + cmd.peltier1.durationMs;
  peltier2ExpiresAt = now + cmd.peltier2.durationMs;
  ermExpiresAt = now + cmd.erm.durationMs;
  peltier1Active = cmd.peltier1.duty != 0;
  peltier2Active = cmd.peltier2.duty != 0;
  ermActive = cmd.erm.duty != 0;
}

// 최상위 "t" 필드(생략 시 기본 "act")로 즉시 duty 적용 명령과 ERM 파형 재생 명령을 나눈다 —
// HapticProtocol.h 상단 주석의 와이어 스키마 참고. 둘 다 여기서 한 번만 deserializeJson()해서
// 이중 파싱을 피한다.
void handleLine(const char* line) {
  JsonDocument doc;
  DeserializationError jsonErr = deserializeJson(doc, line);
  if (jsonErr) {
    NetworkTransport::println("ERR: json_parse_error");
    return;
  }

  const char* type = doc["t"] | "act";
  const char* err = nullptr;

  if (strcmp(type, "act") == 0) {
    HapticCommand parsed;
    if (!parseHapticMessage(doc, parsed, &err)) {
      char errLine[64];
      snprintf(errLine, sizeof(errLine), "ERR: %s", err ? err : "unknown");
      NetworkTransport::println(errLine);
      return;
    }
    SafeCommand safe = SafetyGuard::enforce(parsed);
    applyToHardware(safe);
    lastCommandReceivedAt = millis();
    state = FwState::ACTUATING;
    NetworkTransport::println("OK");
    return;
  }

  if (!WavePlayer::handleCommand(type, doc, &err)) {
    char errLine[64];
    snprintf(errLine, sizeof(errLine), "ERR: %s", err ? err : "unknown");
    NetworkTransport::println(errLine);
    return;
  }
  if (strcmp(type, "wp") == 0) {
    // ERM 소유권이 WavePlayer로 넘어감 — act 경로의 만료 추적(updateExpiry)에서 제외해야
    // act 쪽 낡은 상태가 WavePlayer 재생 중인 ErmDriver 출력을 끼어들어 끄지 않음.
    ermActive = false;
  }
  lastCommandReceivedAt = millis();
  NetworkTransport::println("OK");
}

void pollNetwork() {
  String line;
  if (NetworkTransport::readLine(line)) {
    handleLine(line.c_str());
  }
}

void updateExpiry() {
  uint32_t now = millis();

  // ERM 파형 무기한 반복(rep) 재생 워치독 — act 채널의 FwState와 무관하게 항상 검사.
  // PC 연결이 끊긴 채로 반복 재생이 무한정 지속되는 상황을 방지(act 경로의 holdUntilNext
  // 워치독과 동일한 원칙).
  if (WavePlayer::isPlaying() && WavePlayer::isRepeating() &&
      (now - lastCommandReceivedAt) > MAX_DURATION_MS) {
    WavePlayer::stop();
  }

  if (state != FwState::ACTUATING) return;

  // Peltier1/2는 독립 제어라 만료도 각자 따로 처리 — off1()/off2()로 그 모듈만 끔
  // (반대쪽이 아직 holdUntilNext 상태로 살아있을 수 있으므로 PeltierDriver::off()로
  // 둘 다 꺼버리면 안 됨).
  if (peltier1Active && !peltier1Holding && static_cast<int32_t>(now - peltier1ExpiresAt) >= 0) {
    PeltierDriver::off1();
    peltier1Active = false;
  }
  if (peltier2Active && !peltier2Holding && static_cast<int32_t>(now - peltier2ExpiresAt) >= 0) {
    PeltierDriver::off2();
    peltier2Active = false;
  }
  if (ermActive && !ermHolding && static_cast<int32_t>(now - ermExpiresAt) >= 0) {
    ErmDriver::off();
    ermActive = false;
  }

  // 워치독: "다음 명령까지 유지"로 지정된 채널이 있어도, PC가 MAX_DURATION_MS 넘게 침묵하면
  // 강제로 OFF — 연결이 끊긴 채로 자극이 무기한 지속되는 상황을 방지.
  bool anyHolding = (peltier1Active && peltier1Holding) || (peltier2Active && peltier2Holding) ||
                     (ermActive && ermHolding);
  if (anyHolding && (now - lastCommandReceivedAt) > MAX_DURATION_MS) {
    PeltierDriver::off();
    ErmDriver::off();
    peltier1Active = false;
    peltier2Active = false;
    ermActive = false;
  }

  if (!peltier1Active && !peltier2Active && !ermActive) {
    state = FwState::IDLE;
  }
}
}  // namespace

void HapticStateMachine::begin() {
  Serial.begin(115200);
  uint32_t serialWaitStart = millis();
  // PC가 연결돼 있으면 부팅 초기 로그를 놓치지 않도록 짧게만 대기 — 무한 대기는 아님
  // (배터리로만 단독 구동될 수도 있는 웨어러블이므로).
  while (!Serial && (millis() - serialWaitStart) < 1500) {
  }

  // 원칙 5 (콜드스타트 인러시 방지) 1단계: 로직/핀을 안전 상태(0 duty, sleep)로 먼저 구성.
  PeltierDriver::begin();
  ErmDriver::begin();
  WavePlayer::begin();
  BatteryMonitor::begin();
  NetworkTransport::begin();  // BLE 광고 시작 (로직 초기화의 일부로 취급)

  delay(STABILIZE_MS);

  // 원칙 5 2단계: 로직이 완전히 안정화된 뒤에만 파워단(sleep 핀)을 순차 기동.
  PeltierDriver::wake();
  ErmDriver::wake();

  lastCommandReceivedAt = millis();
  state = FwState::IDLE;
  Serial.println("READY");
}

void HapticStateMachine::loop() {
  // 소프트웨어 PWM 갱신 — LEDC 대신 digitalWrite로 duty를 흉내내므로 최대한 자주 호출해야
  // 파형이 유지됨. loop() 맨 앞에서 매번 호출.
  PeltierDriver::update();
  ErmDriver::update();
  WavePlayer::update();

  NetworkTransport::poll();  // 새 클라이언트 연결 수락 등 유지보수

  if (BatteryMonitor::update()) {
    // 멀티미터 없이 경험적으로 배터리 근사치를 확인할 수 있도록 새 샘플이 있을 때만 로그.
    // (이 로그는 USB Serial에만 남김 — Config.h/NetworkTransport 참고)
    Serial.print("BATT ");
    Serial.print(BatteryMonitor::packVoltage(), 2);
    Serial.print("V ~");
    Serial.print(BatteryMonitor::estimateSocPercent());
    Serial.println("%");
  }
  pollNetwork();
  updateExpiry();
}
