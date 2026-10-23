#pragma once
#include "HapticProtocol.h"

struct SafePeltierCommand {
  uint8_t duty = 0;  // 0-255 (Peltier는 안전상 SafetyGuard.cpp의 PELTIER_DUTY_SAFETY_CAP까지만)
  int8_t direction = 0;
  uint32_t durationMs = 0;
  bool holdUntilNext = false;  // true = durationMs==0으로 요청된 "다음 명령까지 유지"
};

struct SafeErmCommand {
  uint8_t duty = 0;  // 0-255, 상한 없음
  uint32_t durationMs = 0;
  bool holdUntilNext = false;
};

struct SafeCommand {
  SafePeltierCommand peltier1;
  SafePeltierCommand peltier2;
  SafeErmCommand erm;
};

namespace SafetyGuard {
// 파싱된 HapticCommand를 안전 불변식을 만족하는 SafeCommand로 변환한다.
// 모든 명령이 반드시 이 함수를 거쳐야만 하드웨어에 도달하도록 강제 — "사후 검사"가 아니라
// 파이프라인 자체가 금지 상태를 표현할 수 없게 만드는 지점.
//
// PC가 지정한 duty(0-255)를 양자화 없이 그대로 쓰기로 함(사용자 요청) — 대신:
// - 범위: 모든 duty를 0-255로 clamp.
// - 상한(Peltier만): 과열/과전류 방지를 위해 PELTIER_DUTY_SAFETY_CAP을 넘는 값은 캡을 씀
//   (기존 실측 "High" duty=98 근방 — 이 이상은 검증된 적 없음). ERM은 상한 없음.
// - 원칙 2: ERM과 Peltier 모듈(1, 2 각각)이 동시에 "높은 duty"를 "무기한 유지"로 요청하는
//   조합을 구조적으로 제거(그 Peltier 모듈을 저전압 캡 수준으로 강등). Peltier1/2는 독립
//   제어라 각각 따로 검사함.
// - 원칙 3: BatteryMonitor::isLow()가 true면 Peltier1/2 duty를 저전압 캡으로 강등.
SafeCommand enforce(const HapticCommand& cmd);
}  // namespace SafetyGuard
