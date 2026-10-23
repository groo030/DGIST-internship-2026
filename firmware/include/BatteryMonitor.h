#pragma once
#include <cstdint>

namespace BatteryMonitor {
void begin();

// loop()에서 매번 호출해도 되도록 내부적으로 BATTERY_CHECK_INTERVAL_MS 주기를 스스로 판단한다
// (non-blocking, millis() 기반). 실제로 새 샘플을 읽었으면 true를 반환(호출 측 로깅 등에 사용).
bool update();

float packVoltage();
bool isLow();

// 표준 리튬이온 OCV-SOC 곡선(SOC_CURVE) 기준 추정 잔량(%). 정밀 계측이 아니라 경험적 튜닝을
// 돕기 위한 대략적인 참고값.
uint8_t estimateSocPercent();
}  // namespace BatteryMonitor
