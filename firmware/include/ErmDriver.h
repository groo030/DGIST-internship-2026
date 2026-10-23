#pragma once
#include <cstdint>

// ERM 2채널(D2/D3, D8/D9)을 항상 같은 duty로 동시 구동한다 — 내부적으로만 2채널이고
// 이 인터페이스(1채널 시절과 동일)를 쓰는 쪽(HapticStateMachine 등)은 몰라도 됨.
namespace ErmDriver {
void begin();
void wake();
void sleep();
void off();

// duty: 0-255, SafetyGuard::enforce()가 clamp한 값이어야 함(ERM은 상한 없음).
void setOutput(uint8_t duty);

// 소프트웨어 PWM 갱신 — loop()에서 최대한 자주 호출해야 duty가 실제로 반영됨.
void update();
}  // namespace ErmDriver
