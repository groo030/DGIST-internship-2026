#include <Adafruit_TinyUSB.h>  // nRF52 Adafruit 코어에서 USB CDC(Serial) 링크에 필요
#include <Arduino.h>

#include "Config.h"
#include "ErmDriver.h"
#include "PeltierDriver.h"

// Peltier(D9/D10)와 ERM(D5/D6)을 동시에 구동해서 두 채널이 한 번에 문제없이 도는지 확인하는
// 테스트. 메인 펌웨어의 실제 ErmDriver/PeltierDriver를 그대로 쓰고, JSON/BLE는 거치지 않고
// 직접 구동함. Peltier duty는 peltier_ramp_test와 동일하게 100으로 상한(과열/과전류 방지,
// ActuatorMap.h 실사용 High 듀티 98보다 살짝 위). ERM은 0-255 전체 범위 그대로 램프.
//
// 각 램프 주기가 서로 다르게 어긋나도록 시작 방향/속도를 다르게 둬서, 두 채널이 매 순간
// 같은 위상으로 붙어있지 않게 함(Config.h 원칙 6과 같은 취지 — PWM 주파수 자체도
// Peltier 100Hz/ERM 80Hz로 이미 다름).

namespace {
constexpr uint32_t RAMP_STEP_INTERVAL_MS = 15;
constexpr int8_t PELTIER_DIRECTION = 1;  // +1=가열
constexpr uint8_t PELTIER_RAMP_MAX_DUTY = 100;

uint8_t peltierDuty = 0;
int8_t peltierRampDir = 1;
uint8_t ermDuty = 128;  // ERM은 중간값에서 시작해 Peltier와 위상이 겹치지 않게 함
int8_t ermRampDir = -1;
uint32_t lastStepAt = 0;
}  // namespace

void setup() {
  Serial.begin(115200);
  uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart) < 1500) {
  }

  // 원칙 5와 동일하게: 로직 먼저 안정화한 뒤에만 드라이버를 깨움.
  PeltierDriver::begin();
  ErmDriver::begin();
  delay(STABILIZE_MS);
  PeltierDriver::wake();  // DRV8871은 sleep 핀이 없어 no-op — 호출 자체는 유지(일관성)
  ErmDriver::wake();

  lastStepAt = millis();
  Serial.print("=== Peltier+ERM 동시 램프 테스트 시작 (Peltier 0~");
  Serial.print(PELTIER_RAMP_MAX_DUTY);
  Serial.println(", ERM 0~255) ===");
}

void loop() {
  PeltierDriver::update();  // 소프트웨어 PWM 갱신 — 최대한 자주 호출
  ErmDriver::update();

  uint32_t now = millis();
  if (now - lastStepAt >= RAMP_STEP_INTERVAL_MS) {
    lastStepAt = now;

    peltierDuty = static_cast<uint8_t>(peltierDuty + peltierRampDir);
    PeltierDriver::setOutput1(peltierDuty, PELTIER_DIRECTION);
    PeltierDriver::setOutput2(peltierDuty, PELTIER_DIRECTION);
    if (peltierDuty >= PELTIER_RAMP_MAX_DUTY) peltierRampDir = -1;
    if (peltierDuty == 0) peltierRampDir = 1;

    ermDuty = static_cast<uint8_t>(ermDuty + ermRampDir);
    ErmDriver::setOutput(ermDuty);
    if (ermDuty == 255) ermRampDir = -1;
    if (ermDuty == 0) ermRampDir = 1;
  }
}
