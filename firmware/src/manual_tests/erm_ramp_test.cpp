#include <Adafruit_TinyUSB.h>  // nRF52 Adafruit 코어에서 USB CDC(Serial) 링크에 필요
#include <Arduino.h>

#include "Config.h"
#include "ErmDriver.h"

// 메인 펌웨어의 실제 ErmDriver(SoftPwm 기반, EEP/ULT 배선 수정 반영)를 그대로 써서
// duty를 0->255->0으로 계속 반복 램프하는 테스트. JSON/상태머신은 거치지 않고
// ErmDriver를 직접 구동함 — PWM이 전체 범위에서 매끄럽게 동작하는지 시각/촉각/멀티미터로
// 확인하는 용도.

namespace {
constexpr uint32_t RAMP_STEP_INTERVAL_MS = 15;  // duty 1씩 바뀌는 간격 -> 전체 왕복 주기 약 7.6초
uint8_t duty = 0;
int8_t direction = 1;
uint32_t lastStepAt = 0;
}  // namespace

void setup() {
  Serial.begin(115200);
  uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart) < 1500) {
  }

  // 원칙 5와 동일하게: 로직 먼저 안정화한 뒤에만 드라이버를 깨움.
  ErmDriver::begin();
  delay(STABILIZE_MS);
  ErmDriver::wake();

  lastStepAt = millis();
  Serial.println("=== ERM 램프 테스트 시작 (duty 0 -> 255 -> 0 반복) ===");
}

void loop() {
  ErmDriver::update();  // 소프트웨어 PWM 갱신 — 최대한 자주 호출

  uint32_t now = millis();
  if (now - lastStepAt >= RAMP_STEP_INTERVAL_MS) {
    lastStepAt = now;

    duty = static_cast<uint8_t>(duty + direction);
    ErmDriver::setOutput(duty);

    if (duty == 255) direction = -1;
    if (duty == 0) direction = 1;
  }
}
