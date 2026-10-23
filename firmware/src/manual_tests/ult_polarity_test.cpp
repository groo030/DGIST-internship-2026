#include <Adafruit_TinyUSB.h>  // nRF52 Adafruit 코어에서 USB CDC(Serial) 링크에 필요
#include <Arduino.h>

// sleep(nSLEEP)=HIGH, IN1=HIGH를 계속 고정해서 OUT1-OUT2에 안정적으로 전압이 나오는지
// 멀티미터로 확인하기 위한 테스트.
//
// 중요: 인투피온 이 DRV8833 보드는 board 라벨 "ULT"가 실제로는 nFAULT이고, "EEP"라고 찍힌
// 핀이 실제 nSLEEP(enable)임 — 일반적인 DRV8833 브레이크아웃과 라벨이 반대라 실측으로
// 뒤늦게 확인됨. 아래 TEST_SLEEP_PIN은 반드시 보드의 "EEP" 핀에 연결할 것("ULT" 핀 아님).
//
// 메인 펌웨어(main.cpp 등)와는 별도의 PlatformIO 환경(env:ult_test_erm / env:ult_test_peltier)
// 에서만 빌드되며, 다른 소스 파일과 무관하게 이 파일 하나로 완결됨. PWM(LEDC/SoftPwm) 없이
// digitalWrite만 사용 — 최대 출력(풀파워) 상태를 그대로 유지.
//
// 사용법(XIAO nRF52840 배선 기준):
//   1. 기본값은 ERM1 모듈(D1→EEP, D0=IN1) 기준. ERM2를 테스트하려면
//      env:ult_test_peltier로 업로드(build_flags에서 TEST_TARGET_PELTIER 지정, D6→EEP, D5=IN1).
//      (Peltier는 DRV8871이라 EEP/sleep 핀 자체가 없음 — 이 TEST_TARGET_PELTIER 브랜치는
//      실제 Peltier가 아니라 두 번째 DRV8833(ERM2) 배선 확인용으로만 씀.)
//   2. 멀티미터를 해당 모듈의 OUT1-OUT2(모터 리드) 사이에 대고 이 스케치를 업로드.
//   3. VCC 근처 전압이 계속 안정적으로 유지되는지 확인.

#if defined(TEST_TARGET_PELTIER)
constexpr uint8_t TEST_SLEEP_PIN = D6;  // ERM2, 보드의 "EEP" 핀에 연결
constexpr uint8_t TEST_PWM_PIN = D5;    // ERM2 IN1
#else
constexpr uint8_t TEST_SLEEP_PIN = D1;  // ERM1, 보드의 "EEP" 핀에 연결 (기본값)
constexpr uint8_t TEST_PWM_PIN = D0;    // ERM1 IN1
#endif

void setup() {
  Serial.begin(115200);
  uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart) < 1500) {
  }

  pinMode(TEST_SLEEP_PIN, OUTPUT);
  digitalWrite(TEST_SLEEP_PIN, HIGH);  // 계속 awake 유지

  pinMode(TEST_PWM_PIN, OUTPUT);
  digitalWrite(TEST_PWM_PIN, HIGH);  // 계속 최대 출력 유지

  Serial.println("=== nSLEEP(EEP)=HIGH, IN1=HIGH 고정 (토글 없음) ===");
  Serial.println("OUT1-OUT2에 멀티미터 대고 전압이 안정적으로 나오는지 확인하세요.");
}

void loop() {
  delay(1000);  // 상태 계속 유지, 아무 것도 안 함
}
