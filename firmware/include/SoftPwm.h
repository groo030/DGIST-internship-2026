#pragma once
#include <cstdint>

// LEDC(ledcSetup/ledcAttachPin) 레거시 API가 이 보드/코어 조합(Arduino Nano ESP32,
// arduino-esp32 3.20017 계열)에서 실측으로 신호를 내지 않는 게 확인됨(드라이버 보드 없이
// D2-GND 단독 측정으로도 0V, digitalWrite는 정상 동작) — LEDC 페리페럴에 의존하지 않는
// digitalWrite 기반 소프트웨어 PWM으로 대체.
//
// update()를 loop()에서 최대한 자주 호출해야 duty가 제대로 반영됨. 정밀한 고주파 PWM용이
// 아니라, Config.h의 저주파(수백 Hz 이하) 햅틱 구동에는 충분한 수준.
class SoftPwmChannel {
 public:
  void begin(uint8_t pin, uint32_t frequencyHz);
  void setDuty(uint8_t duty);  // 0-255
  void update();               // loop()에서 자주 호출
  void off();

 private:
  uint8_t pin_ = 0;
  uint32_t periodUs_ = 0;
  volatile uint8_t duty_ = 0;
  uint32_t cycleStartUs_ = 0;
};
