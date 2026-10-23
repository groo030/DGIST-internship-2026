#include <Adafruit_TinyUSB.h>  // nRF52 Adafruit 코어에서 USB CDC(Serial) 링크에 필요
#include <Arduino.h>

#include "SoftPwm.h"

// D0에서 PWM 신호가 실제로 나오는지 확인하는 독립 테스트 (v2: 소프트웨어 PWM).
// 드라이버 보드 연결/fault 상태와 완전히 무관 — MCU 자체가 신호를 제대로 만들어내는지만
// 확인하는 게 목적. 멀티미터를 D0(XIAO nRF52840 헤더 핀) - GND에 대고 이 스케치만
// 업로드하면 됨(드라이버 보드를 연결할 필요 없음).
//
// v1(ESP32 LEDC/ledcSetup+ledcAttachPin)은 그 보드/코어 조합에서 D2-GND 단독 측정으로도
// 0V가 나오는 게 재현돼 LEDC 자체가 문제였음을 확인함 — SoftPwm(digitalWrite 기반)으로
// 교체(플랫폼 중립이라 XIAO nRF52840 교체 후에도 그대로 재사용).
//
// duty=128(50%)로 고정, 100Hz. DC 전압계로 재면 평균 전압이 나오는데, nRF52840 로직 레벨
// 3.3V 기준으로 duty 50%면 약 1.65V 근처가 나와야 정상.

SoftPwmChannel testPwm;
constexpr uint8_t TEST_PIN = D0;
constexpr uint32_t TEST_FREQ_HZ = 100;
constexpr uint8_t TEST_DUTY = 128;  // 50% duty -> 평균 약 1.65V 기대 (3.3V 기준)

void setup() {
  Serial.begin(115200);
  uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart) < 1500) {
  }

  testPwm.begin(TEST_PIN, TEST_FREQ_HZ);
  testPwm.setDuty(TEST_DUTY);

  Serial.println("=== PWM 신호 테스트 시작 (v2, SoftPwm) ===");
  Serial.println("D0 - GND 사이에 멀티미터(DC 전압) 대고 확인하세요.");
  Serial.println("duty 50% -> 평균 약 1.65V 근처가 나와야 정상.");
}

void loop() {
  testPwm.update();  // 최대한 자주 호출해야 파형이 유지됨
}
