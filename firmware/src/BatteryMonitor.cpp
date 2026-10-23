#include "BatteryMonitor.h"

#include <Arduino.h>
#include <cstddef>

#include "Config.h"

namespace {
// 부팅 직후 첫 샘플 전까지의 낙관적 초기값(완충 상태로 가정) — 저전압 오탐으로 인한
// 불필요한 강등을 부팅 초기부터 걸지 않기 위함.
float lastPackVoltage = 4.2f * BATTERY_SERIES_CELLS;
uint32_t lastCheckAt = 0;
bool hasCheckedOnce = false;

struct SocPoint {
  uint8_t socPercent;
  float cellVoltage;
};

// 표준 3.7V 리튬이온 셀의 무부하(OCV) 전압-SOC 근사 곡선(단일 셀 기준). Config.h 주석 참고 —
// 첨부 KC62133 인증서로 일반 리튬이온 화학임을 확인했으므로 이 범용 곡선을 그대로 사용.
constexpr SocPoint SOC_CURVE[] = {
    {0, 3.00f},  {10, 3.65f}, {20, 3.73f}, {30, 3.77f}, {40, 3.79f}, {50, 3.82f},
    {60, 3.87f}, {70, 3.92f}, {80, 3.98f}, {90, 4.06f}, {100, 4.20f},
};
constexpr size_t SOC_CURVE_LEN = sizeof(SOC_CURVE) / sizeof(SOC_CURVE[0]);
}  // namespace

void BatteryMonitor::begin() {
  analogReadResolution(12);
  analogReference(AR_DEFAULT);  // 0.6V 내부 기준 * 6 = 0-3.6V 풀스케일 (Config.h 참고)
  update();
}

bool BatteryMonitor::update() {
  uint32_t now = millis();
  if (hasCheckedOnce && (now - lastCheckAt) < BATTERY_CHECK_INTERVAL_MS) return false;
  lastCheckAt = now;
  hasCheckedOnce = true;

  uint32_t sumRaw = 0;
  for (uint8_t i = 0; i < BATTERY_ADC_SAMPLES; i++) {
    sumRaw += analogRead(BATTERY_SENSE_PIN);
  }
  float avgRaw = static_cast<float>(sumRaw) / BATTERY_ADC_SAMPLES;
  float avgVolts = (avgRaw * ADC_REFERENCE_MILLIVOLTS / 4095.0f) / 1000.0f;
  lastPackVoltage = avgVolts * BATTERY_DIVIDER_RATIO;
  return true;
}

float BatteryMonitor::packVoltage() { return lastPackVoltage; }

bool BatteryMonitor::isLow() { return lastPackVoltage <= BATTERY_LOW_PACK_VOLTAGE; }

uint8_t BatteryMonitor::estimateSocPercent() {
  float cellVoltage = lastPackVoltage / BATTERY_SERIES_CELLS;
  if (cellVoltage <= SOC_CURVE[0].cellVoltage) return 0;
  if (cellVoltage >= SOC_CURVE[SOC_CURVE_LEN - 1].cellVoltage) return 100;

  for (size_t i = 1; i < SOC_CURVE_LEN; i++) {
    if (cellVoltage <= SOC_CURVE[i].cellVoltage) {
      const SocPoint& lo = SOC_CURVE[i - 1];
      const SocPoint& hi = SOC_CURVE[i];
      float t = (cellVoltage - lo.cellVoltage) / (hi.cellVoltage - lo.cellVoltage);
      return static_cast<uint8_t>(lo.socPercent + t * (hi.socPercent - lo.socPercent));
    }
  }
  return 100;
}
