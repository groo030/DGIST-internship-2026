#include <Adafruit_TinyUSB.h>  // nRF52 Adafruit 코어에서 USB CDC(Serial) 링크에 필요
#include <Arduino.h>

#include "Config.h"
#include "PeltierDriver.h"

// 메인 펌웨어의 실제 PeltierDriver(SoftPwm 기반)를 그대로 써서 duty를 0->RAMP_MAX_DUTY->0으로
// 계속 반복 램프하는 테스트. JSON/네트워크는 거치지 않고 PeltierDriver를 직접 구동함.
// DRV8871은 sleep 핀이 없어 wake()가 no-op — ERM 때 겪은 EEP/ULT 배선 문제가 애초에
// 해당 없음.
//
// 방향은 가열(+1)로 고정 — 방향까지 같이 테스트하고 싶으면 PELTIER_DIRECTION만 -1로 바꾸면 됨.
// 상한을 255가 아니라 100으로 제한(ActuatorMap.h의 실사용 High 듀티 98보다 살짝 위) — 과열/과전류
// 방지를 위해 실제 제품 동작 범위를 넘어서는 값까지는 올리지 않는다.

namespace {
constexpr uint32_t RAMP_STEP_INTERVAL_MS = 15;  // duty 1씩 바뀌는 간격
constexpr int8_t PELTIER_DIRECTION = 1;         // +1=가열, -1=냉각
constexpr uint8_t RAMP_MAX_DUTY = 100;          // 실사용 범위(최대 98) 초과 방지용 상한
uint8_t duty = 0;
int8_t rampDirection = 1;
uint32_t lastStepAt = 0;
}  // namespace

void setup() {
  Serial.begin(115200);
  uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart) < 1500) {
  }

  // 원칙 5와 동일하게: 로직 먼저 안정화한 뒤에만 드라이버를 깨움.
  PeltierDriver::begin();
  delay(STABILIZE_MS);
  PeltierDriver::wake();  // DRV8871은 sleep 핀이 없어 no-op — 호출 자체는 유지(일관성)

  lastStepAt = millis();
  Serial.print("=== Peltier 램프 테스트 시작 (duty 0 -> ");
  Serial.print(RAMP_MAX_DUTY);
  Serial.println(" -> 0 반복, 방향 고정) ===");
}

void loop() {
  PeltierDriver::update();  // 소프트웨어 PWM 갱신 — 최대한 자주 호출

  uint32_t now = millis();
  if (now - lastStepAt >= RAMP_STEP_INTERVAL_MS) {
    lastStepAt = now;

    duty = static_cast<uint8_t>(duty + rampDirection);
    PeltierDriver::setOutput1(duty, PELTIER_DIRECTION);
    PeltierDriver::setOutput2(duty, PELTIER_DIRECTION);

    if (duty >= RAMP_MAX_DUTY) rampDirection = -1;
    if (duty == 0) rampDirection = 1;
  }
}
