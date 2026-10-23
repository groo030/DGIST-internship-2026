#include "SafetyGuard.h"

#include "BatteryMonitor.h"

namespace {
// 저전압 시 강등 대상 채널. 근거: 문헌상 arousal/진동 신호전달 신뢰도가 높고 Peltier가 전류를
// 더 먹음. 이건 UX/제품 판단이므로 MENTOR-REVIEW 대상 — 상수 하나로 노출해 재검토 시 한 줄만
// 바꾸면 되게 함.
constexpr bool LOW_BATTERY_DEPRIORITIZE_PELTIER = true;

// Peltier 안전 상한 — 과열/과전류 방지. 사용자 지정값(150) — PC가 더 큰 값을 보내도 여기서 캡을 씀.
constexpr uint8_t PELTIER_DUTY_SAFETY_CAP = 150;

// 저전압 시 강등 캡 — 예전 ActuatorMap.h의 "Low" duty 값과 동일한 기준으로 유지.
constexpr uint8_t LOW_BATTERY_PELTIER_DUTY_CAP = 76;
constexpr uint8_t LOW_BATTERY_ERM_DUTY_CAP = 125;

// 원칙 2 "무기한 최대 유지 금지" 판정 기준 — 예전 ActuatorMap.h의 High 문턱값과 동일하게 맞춤.
constexpr uint8_t HIGH_DUTY_THRESHOLD_PELTIER = 98;
constexpr uint8_t HIGH_DUTY_THRESHOLD_ERM = 255;

uint8_t clampDuty(float duty, uint8_t maxDuty) {
  if (duty < 0.0f) return 0;
  if (duty > static_cast<float>(maxDuty)) return maxDuty;
  return static_cast<uint8_t>(duty + 0.5f);  // 반올림
}

void buildPeltier(const ActuatorRequest& req, SafePeltierCommand& out) {
  out.duty = clampDuty(req.duty, PELTIER_DUTY_SAFETY_CAP);
  out.direction = req.direction >= 0 ? 1 : -1;
  out.durationMs = req.durationMs;
  out.holdUntilNext = (req.durationMs == 0);
}
}  // namespace

SafeCommand SafetyGuard::enforce(const HapticCommand& cmd) {
  SafeCommand out;

  buildPeltier(cmd.peltier1, out.peltier1);
  buildPeltier(cmd.peltier2, out.peltier2);

  out.erm.duty = clampDuty(cmd.erm.duty, 255);
  out.erm.durationMs = cmd.erm.durationMs;
  out.erm.holdUntilNext = (cmd.erm.durationMs == 0);

  // 원칙 2: ERM과 이 Peltier 모듈이 동시에 각자 높은 duty를 무기한 유지로 요청하는 조합은
  // 통과시키지 않는다 — 그 Peltier 모듈을 저전압 캡 수준으로 낮춘다. Peltier1/2 각각 독립
  // 검사 — 한쪽만 해당돼도 그쪽만 강등되고 반대쪽은 영향 없음.
  bool ermHighSustained = out.erm.duty >= HIGH_DUTY_THRESHOLD_ERM && out.erm.holdUntilNext;
  if (ermHighSustained && out.peltier1.duty >= HIGH_DUTY_THRESHOLD_PELTIER && out.peltier1.holdUntilNext) {
    out.peltier1.duty = LOW_BATTERY_PELTIER_DUTY_CAP;
  }
  if (ermHighSustained && out.peltier2.duty >= HIGH_DUTY_THRESHOLD_PELTIER && out.peltier2.holdUntilNext) {
    out.peltier2.duty = LOW_BATTERY_PELTIER_DUTY_CAP;
  }

  // 원칙 3 + 7: 저전압 시 다중 최대 조합 자체를 못 만들게 하고, zero-duty뿐 아니라 물리적
  // sleep도 함께 유도(원칙 7의 belt-and-suspenders는 HapticStateMachine이 sleep 핀을
  // 제어하는 지점에서 이 duty==0 여부를 참고해 처리한다).
  if (BatteryMonitor::isLow()) {
    if (LOW_BATTERY_DEPRIORITIZE_PELTIER) {
      if (out.peltier1.duty > LOW_BATTERY_PELTIER_DUTY_CAP) out.peltier1.duty = LOW_BATTERY_PELTIER_DUTY_CAP;
      if (out.peltier2.duty > LOW_BATTERY_PELTIER_DUTY_CAP) out.peltier2.duty = LOW_BATTERY_PELTIER_DUTY_CAP;
    } else {
      if (out.erm.duty > LOW_BATTERY_ERM_DUTY_CAP) out.erm.duty = LOW_BATTERY_ERM_DUTY_CAP;
    }
  }

  return out;
}
