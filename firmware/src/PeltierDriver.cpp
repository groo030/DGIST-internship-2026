#include "PeltierDriver.h"

#include <Arduino.h>

#include "Config.h"
#include "SoftPwm.h"

// 2채널(1번: D9/D10, 2번: D7/D8)을 독립적으로 구동 — 서로 다른 duty/방향 조합(예: 1번 가열 +
// 2번 냉각)이 가능해야 해서 ERM과 달리 미러링하지 않음. 각 모듈이 자기만의 방향 상태
// (currentDirection1/2)를 갖고, 방향 전환 dead-time도 그 모듈에만 적용된다.
namespace {
int8_t currentDirection1 = 0;
int8_t currentDirection2 = 0;
SoftPwmChannel in1PwmA;  // 1번 Peltier IN1 (D9)
SoftPwmChannel in2PwmA;  // 1번 Peltier IN2 (D10)
SoftPwmChannel in1PwmB;  // 2번 Peltier IN1 (D7)
SoftPwmChannel in2PwmB;  // 2번 Peltier IN2 (D8)

void applyModule(SoftPwmChannel& in1, SoftPwmChannel& in2, int8_t& currentDirection,
                  uint8_t duty, int8_t direction) {
  int8_t normalizedDirection = direction >= 0 ? 1 : -1;

  if (normalizedDirection != currentDirection) {
    // H-브릿지 shoot-through 방지를 위한 dead-time. 이 모듈만 껐다 켬 — 반대쪽 모듈은
    // 자기 방향을 그대로 유지(독립 제어이므로 서로 영향 없음).
    in1.off();
    in2.off();
    delay(DIRECTION_DEADTIME_MS);
    currentDirection = normalizedDirection;
  }

  // 실측으로 확인됨: 우리 배선에서는 IN2가 가열, IN1이 냉각 — 일반적인 DRV8871 IN1=가열
  // 가정과 반대라 여기서 뒤집어서 흡수한다. 외부 인터페이스(direction: +1=가열/-1=냉각)는
  // 그대로 유지 — HapticStateMachine/SafetyGuard/HapticProtocol은 이 반전을 몰라도 됨.
  if (currentDirection > 0) {
    in1.setDuty(0);
    in2.setDuty(duty);
  } else {
    in1.setDuty(duty);
    in2.setDuty(0);
  }
}
}  // namespace

void PeltierDriver::begin() {
  in1PwmA.begin(PELTIER1_IN1_PIN, PELTIER_PWM_FREQUENCY_HZ);
  in2PwmA.begin(PELTIER1_IN2_PIN, PELTIER_PWM_FREQUENCY_HZ);
  in1PwmB.begin(PELTIER2_IN1_PIN, PELTIER_PWM_FREQUENCY_HZ);
  in2PwmB.begin(PELTIER2_IN2_PIN, PELTIER_PWM_FREQUENCY_HZ);
  // DRV8871 전용 구성 — sleep 핀 자체가 없어 awake 상태 고정.
  currentDirection1 = 0;
  currentDirection2 = 0;
}

void PeltierDriver::wake() {
  // DRV8871엔 sleep 핀이 없어 이 함수가 할 수 있는 일이 없음 — 항상 "awake" 상태(하드웨어 한계).
}

void PeltierDriver::sleep() { off(); }

void PeltierDriver::off1() {
  in1PwmA.off();
  in2PwmA.off();
  currentDirection1 = 0;
}

void PeltierDriver::off2() {
  in1PwmB.off();
  in2PwmB.off();
  currentDirection2 = 0;
}

void PeltierDriver::off() {
  off1();
  off2();
}

void PeltierDriver::setOutput1(uint8_t duty, int8_t direction) {
  applyModule(in1PwmA, in2PwmA, currentDirection1, duty, direction);
}

void PeltierDriver::setOutput2(uint8_t duty, int8_t direction) {
  applyModule(in1PwmB, in2PwmB, currentDirection2, duty, direction);
}

void PeltierDriver::update() {
  in1PwmA.update();
  in2PwmA.update();
  in1PwmB.update();
  in2PwmB.update();
}
