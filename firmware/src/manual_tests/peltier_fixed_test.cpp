#include <Adafruit_TinyUSB.h>  // nRF52 Adafruit 코어에서 USB CDC(Serial) 링크에 필요
#include <Arduino.h>

#include "Config.h"
#include "PeltierDriver.h"

// 전류 측정을 위해 duty를 램프 없이 고정 유지하는 테스트. 실제 PeltierDriver(SoftPwm)를
// 그대로 씀. 기본 duty는 OUT1-OUT2 ≈3V를 목표로 한 근사치(배터리 전압에 따라 실제 값은
// 달라질 수 있음) — 시리얼 모니터에 0~255 사이 숫자를 입력하면 그 값으로 즉시 바뀌어서,
// 멀티미터로 보면서 원하는 전압/전류 지점을 직접 맞출 수 있음.

namespace {
constexpr int8_t PELTIER_DIRECTION = 1;  // +1=가열, -1=냉각

// 배터리 ~7.8V 기준 OUT1-OUT2 ≈3V를 목표로 한 시작값(3/7.8*255 근사). 배터리 전압/부하에
// 따라 실제 전압은 달라지므로 시리얼로 조정해서 맞출 것.
constexpr uint8_t INITIAL_DUTY = 98;

uint8_t currentDuty = INITIAL_DUTY;
}  // namespace

void setup() {
  Serial.begin(115200);
  uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart) < 1500) {
  }

  PeltierDriver::begin();
  delay(STABILIZE_MS);
  PeltierDriver::wake();
  PeltierDriver::setOutput1(currentDuty, PELTIER_DIRECTION);
  PeltierDriver::setOutput2(currentDuty, PELTIER_DIRECTION);

  Serial.println("=== Peltier 고정 출력 테스트 ===");
  Serial.print("시작 duty = ");
  Serial.println(currentDuty);
  Serial.println("시리얼 모니터에 0~255 사이 숫자 입력 후 Enter -> 그 duty로 즉시 고정 전환");
}

void loop() {
  PeltierDriver::update();  // 소프트웨어 PWM 갱신 — 최대한 자주 호출

  if (Serial.available() > 0) {
    int value = Serial.parseInt();
    while (Serial.available() > 0) Serial.read();  // 남은 개행 등 비우기

    if (value >= 0 && value <= 255) {
      currentDuty = static_cast<uint8_t>(value);
      PeltierDriver::setOutput1(currentDuty, PELTIER_DIRECTION);
      PeltierDriver::setOutput2(currentDuty, PELTIER_DIRECTION);
      Serial.print("duty = ");
      Serial.println(currentDuty);
    }
  }
}
