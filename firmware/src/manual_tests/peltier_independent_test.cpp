#include <Adafruit_TinyUSB.h>  // nRF52 Adafruit 코어에서 USB CDC(Serial) 링크에 필요
#include <Arduino.h>

#include "Config.h"
#include "PeltierDriver.h"

// Peltier 독립 방향 제어 확인용 테스트 — 1번(D9/D10)은 가열, 2번(D7/D8)은 냉각으로 동시에
// 고정 구동한다. 두 모듈이 서로 다른 방향을 유지한 채 문제없이 도는지(예: 방향 전환
// dead-time이 서로 간섭 안 하는지) 손으로 만져보고 확인하는 용도. duty는 peltier_ramp_test와
// 동일하게 100으로 상한(과열/과전류 방지, ActuatorMap.h 실사용 High 듀티 98보다 살짝 위).

namespace {
constexpr uint8_t TEST_DUTY = 100;
constexpr int8_t PELTIER1_DIRECTION = 1;   // 가열
constexpr int8_t PELTIER2_DIRECTION = -1;  // 냉각
}  // namespace

void setup() {
  Serial.begin(115200);
  uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart) < 1500) {
  }

  PeltierDriver::begin();
  delay(STABILIZE_MS);
  PeltierDriver::wake();  // DRV8871은 sleep 핀이 없어 no-op — 호출 자체는 유지(일관성)

  PeltierDriver::setOutput1(TEST_DUTY, PELTIER1_DIRECTION);
  PeltierDriver::setOutput2(TEST_DUTY, PELTIER2_DIRECTION);

  Serial.println("=== Peltier 독립 방향 테스트 시작 (1번=가열, 2번=냉각, duty 고정) ===");
  Serial.println("D9/D10 쪽은 뜨거워지고 D7/D8 쪽은 차가워지는지 만져서 확인하세요.");
}

void loop() {
  PeltierDriver::update();  // 소프트웨어 PWM 갱신 — 최대한 자주 호출
}
