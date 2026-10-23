#include "SoftPwm.h"

#include <Arduino.h>

void SoftPwmChannel::begin(uint8_t pin, uint32_t frequencyHz) {
  pin_ = pin;
  periodUs_ = 1000000UL / frequencyHz;
  duty_ = 0;
  cycleStartUs_ = micros();
  pinMode(pin_, OUTPUT);
  digitalWrite(pin_, LOW);
}

void SoftPwmChannel::setDuty(uint8_t duty) { duty_ = duty; }

void SoftPwmChannel::off() {
  duty_ = 0;
  digitalWrite(pin_, LOW);
}

void SoftPwmChannel::update() {
  uint32_t now = micros();
  uint32_t elapsed = now - cycleStartUs_;
  if (elapsed >= periodUs_) {
    cycleStartUs_ = now;
    elapsed = 0;
  }

  uint8_t duty = duty_;
  if (duty == 0) {
    digitalWrite(pin_, LOW);
    return;
  }
  if (duty >= 255) {
    digitalWrite(pin_, HIGH);
    return;
  }

  uint32_t onTimeUs = (periodUs_ * duty) / 255;
  digitalWrite(pin_, elapsed < onTimeUs ? HIGH : LOW);
}
