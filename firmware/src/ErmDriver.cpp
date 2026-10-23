#include "ErmDriver.h"

#include <Arduino.h>

#include "Config.h"
#include "SoftPwm.h"

// 2채널(1번: D2/D3, 2번: D8/D9)을 항상 같은 duty로 동시 구동 — Peltier와 동일한 이유로
// 두 ERM을 "하나처럼" 다룸(Config.h 참고). 외부 인터페이스는 1채널이던 때와 동일.
namespace {
SoftPwmChannel in1PwmA;  // 1번 ERM IN1 (D2)
SoftPwmChannel in1PwmB;  // 2번 ERM IN1 (D8)
}  // namespace

void ErmDriver::begin() {
  in1PwmA.begin(ERM1_IN1_PIN, ERM_PWM_FREQUENCY_HZ);
  in1PwmB.begin(ERM2_IN1_PIN, ERM_PWM_FREQUENCY_HZ);

  pinMode(ERM1_SLEEP_PIN, OUTPUT);
  digitalWrite(ERM1_SLEEP_PIN, LOW);  // sleep. HIGH=awake로 확인됨(인투피온 DRV8833 모듈 스펙).
  pinMode(ERM2_SLEEP_PIN, OUTPUT);
  digitalWrite(ERM2_SLEEP_PIN, LOW);
}

void ErmDriver::wake() {
  digitalWrite(ERM1_SLEEP_PIN, HIGH);
  digitalWrite(ERM2_SLEEP_PIN, HIGH);
}

void ErmDriver::sleep() {
  off();
  digitalWrite(ERM1_SLEEP_PIN, LOW);
  digitalWrite(ERM2_SLEEP_PIN, LOW);
}

void ErmDriver::off() {
  in1PwmA.off();
  in1PwmB.off();
}

void ErmDriver::setOutput(uint8_t duty) {
  in1PwmA.setDuty(duty);
  in1PwmB.setDuty(duty);
}

void ErmDriver::update() {
  in1PwmA.update();
  in1PwmB.update();
}
