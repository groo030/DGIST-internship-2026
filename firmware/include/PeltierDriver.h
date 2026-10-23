#pragma once
#include <cstdint>

// Peltier 2채널(D9/D10, D7/D8)을 독립적으로 구동한다 — 각 모듈이 서로 다른 duty/방향을
// 가질 수 있음(예: 1번은 가열, 2번은 냉각). ERM과 달리 "항상 미러링"이 아님 — 이제 이
// 인터페이스를 쓰는 쪽(HapticStateMachine 등)이 모듈 1/2을 각각 명시적으로 제어해야 함.
namespace PeltierDriver {
// 부팅 시 안전 상태(0 duty, sleep)로 핀을 구성한다. DRV8871 전용 — sleep 핀 자체가 없음.
void begin();

// STABILIZE_MS 경과 후에만 호출 — sleep 핀을 깨운다.
// DRV8871엔 sleep 핀이 없어 no-op(항상 "awake" 상태인 하드웨어 한계).
void wake();

// 즉시 두 모듈 다 0 duty로 만들고, 가능하면 sleep 핀도 재차 low로 만든다
// (원칙 7의 belt-and-suspenders).
void sleep();

void off();   // 두 모듈 다 0 duty로
void off1();  // 1번 모듈만 0 duty로 (2번은 그대로 유지)
void off2();  // 2번 모듈만 0 duty로 (1번은 그대로 유지)

// duty: 0-255, SafetyGuard::enforce()가 clamp/상한(PELTIER_DUTY_SAFETY_CAP)을 적용한 값이어야 함.
// direction: -1 냉각 / +1 가열. 방향 전환 시 dead-time을 두고 전환한다(모듈별 독립 상태).
// (실제 IN1/IN2 중 어느 쪽이 PWM을 받는지는 실측 배선에 맞게 PeltierDriver.cpp 내부에서
// 뒤집혀 있음 — 이 인터페이스를 쓰는 쪽은 몰라도 됨.)
void setOutput1(uint8_t duty, int8_t direction);
void setOutput2(uint8_t duty, int8_t direction);

// 소프트웨어 PWM 갱신 — loop()에서 최대한 자주 호출해야 duty가 실제로 반영됨.
void update();
}  // namespace PeltierDriver
