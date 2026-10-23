#pragma once
#include <Arduino.h>

// ===== ERM 모듈 — 2채널(D0/D1, D5/D6), 항상 동시에 같은 duty로 구동 =====
// 데모가 단일 시나리오라 두 ERM을 개별 제어할 필요가 없어 — 하나의 명령이 둘 다에 똑같이 적용됨
// (JSON 프로토콜/SafetyGuard는 그대로, ErmDriver 내부에서만 2채널로 나감).
// 핀 배정은 XIAO nRF52840 최종 배선 기준.
constexpr uint8_t ERM1_IN1_PIN = D0;  // 1번 ERM, PWM. IN2는 보드에서 GND 직결(고정) — GPIO 아님.
// sleep/enable(nSLEEP) 핀. 인투피온 이 보드는 "EEP"라고 찍힌 핀이 실제 nSLEEP이고, "ULT"라고
// 찍힌 핀이 실제 nFAULT임(일반적인 DRV8833 브레이크아웃 라벨과 반대) — 실측으로 확인됨.
// 이 GPIO는 반드시 보드의 "EEP" 핀에 물려야 함, "ULT" 핀 아님.
constexpr uint8_t ERM1_SLEEP_PIN = D1;
constexpr uint8_t ERM2_IN1_PIN = D5;    // 2번 ERM, PWM
constexpr uint8_t ERM2_SLEEP_PIN = D6;  // 2번 ERM, 위와 동일하게 "EEP" 핀에 연결할 것

// ===== Peltier 모듈 — 2채널(D9/D10, D7/D8), 모듈별 독립 duty/방향 제어 =====
// 제품 요구사항으로 두 Peltier를 서로 다른 방향(예: 1번 가열 + 2번 냉각)으로 동시에
// 구동할 수 있어야 함 — ERM과 달리 미러링하지 않음(PeltierDriver::setOutput1/2 참고).
// IN1=냉각/IN2=가열로 실측 확인됨(일반적인 DRV8871 IN1=가열 가정과 반대) — 방향 반전은
// PeltierDriver.cpp의 setOutput() 내부에서 흡수하므로 여기 핀 자체의 의미는 그대로 IN1/IN2.
constexpr uint8_t PELTIER1_IN1_PIN = D9;   // 1번 Peltier, PWM (냉각 방향)
constexpr uint8_t PELTIER1_IN2_PIN = D10;  // 1번 Peltier, PWM (가열 방향)
constexpr uint8_t PELTIER2_IN1_PIN = D7;   // 2번 Peltier, PWM (냉각 방향)
constexpr uint8_t PELTIER2_IN2_PIN = D8;   // 2번 Peltier, PWM (가열 방향)

// Peltier는 DRV8871만 쓰기로 확정(sleep 핀 불필요) — DRV8833은 안 씀. 2채널 다 이 전제로 설계.
#if !defined(PELTIER_DRIVER_DRV8871)
#error "Peltier는 DRV8871 전용 — platformio.ini에서 PELTIER_DRIVER_DRV8871 지정할 것"
#endif

// ===== 배터리 전압 감지 =====
constexpr uint8_t BATTERY_SENSE_PIN = D4;  // XIAO nRF52840의 A4/D4 겸용 핀

// ===== BLE 통신 =====
// USB Serial 대신 BLE(Nordic UART Service)로 PC와 JSON 라인을 주고받는다
// (NetworkTransport.h/.cpp). XIAO nRF52840엔 WiFi가 없어 이전 WiFi/TCP 전송을 대체함 —
// 서비스/캐릭터리스틱 UUID는 Adafruit Bluefruit의 BLEUart가 표준 NUS UUID를 그대로 쓰므로
// 별도 UUID 정의가 필요 없다.
constexpr const char* BLE_DEVICE_NAME = "EMO-Haptic";

// ===== PWM =====
// 예전 ESP32 보드에서 LEDC(ledcSetup/ledcAttachPin) 레거시 API가 실측으로 신호를 안 내는 게
// 확인돼 digitalWrite 기반 소프트웨어 PWM(SoftPwm.h)으로 대체했었음. XIAO nRF52840으로
// 교체된 뒤에도 SoftPwm은 Arduino 표준 API(digitalWrite/micros)만 쓰는 플랫폼 중립 구현이라
// 그대로 재사용— 코어 종속 페리페럴에 기대지 않는 방식의 이점이 이번 보드 교체에서도 유효함.
// duty는 항상 0-255 범위(PC가 지정한 값을 SafetyGuard가 clamp/상한 적용해서 그대로 사용).

// 원칙 6(PWM 위상 오프셋): 오실로스코프/로직 애널라이저가 없어 실제 위상을 측정할 수 없으므로,
// Peltier와 ERM의 PWM 주파수 자체를 다르게 둔다. 소프트웨어 PWM이라 각 채널이 독립된
// micros() 기준 주기로 스스로 토글하는데, 주파수가 다르면 두 파형의 상승 에지가 계속 같은
// 지점에 고정될 수 없다(주기가 다르므로 상대 위상이 끊임없이 흘러감) — 장비로 측정하지 않아도
// 수학적으로 "매 순간 피크가 겹치는" 상황을 구조적으로 배제할 수 있는 방법.
//
// 값 자체는 데이터시트 대조 없이 "가장 보수적인 값에서 시작해 조금씩 올리는" 경험적 방식으로
// 정하기로 함. 아래는 그 시작값 — 낮은 주파수일수록 개별 스위칭 이벤트가 뜸해서 디버깅하기
// 쉽고 드라이버 스위칭 스트레스도 작음. 이 상태로 문제(과열, 이상 소음, 반응 이상) 없으면
// 두 값 다 같은 비율로 올려가되, 항상 서로 정수배가 아니게 차이를 유지할 것.
//   1단계(현재): Peltier 100Hz / ERM  80Hz
//   2단계:       Peltier 250Hz / ERM 200Hz
//   3단계:       Peltier 500Hz / ERM 400Hz
//   4단계:       Peltier 1000Hz / ERM 800Hz  (여기까지 문제 없으면 충분— 더 올릴 이유 적음)
constexpr uint32_t PELTIER_PWM_FREQUENCY_HZ = 100;
constexpr uint32_t ERM_PWM_FREQUENCY_HZ = 80;

// 위 주파수 차이만으로도 충분하지만, 시작 시점에 추가로 짧게 지연을 두는 것도 비용이 없어 유지
// (belt-and-suspenders, 필수 아님).
constexpr uint32_t PWM_PHASE_OFFSET_MS = 3;

// ===== 안전 타이밍 =====
constexpr uint32_t STABILIZE_MS = 100;         // 원칙 5: 로직 안정화 후에만 드라이버 sleep 해제
constexpr uint32_t DIRECTION_DEADTIME_MS = 5;  // Peltier 방향 반전 시 shoot-through 방지 (H-브릿지 기본 안전, 7원칙과 별개)
constexpr uint32_t BATTERY_CHECK_INTERVAL_MS = 1000;

// MENTOR-REVIEW: PC 연결이 끊긴 채로 "다음 명령까지 유지" 채널이 무한정 계속되지 않도록 하는
// 워치독 상한. 임시값. (이것도 "무한정 지속 금지"를 위한 상한이지 재시도 로직이 아님)
constexpr uint32_t MAX_DURATION_MS = 30000;

// ===== ERM 파형 재생(WavePlayer) =====
// PC가 오디오 엔벨로프 등 임의 파형을 BLE로 통째로 업로드해두면, 펌웨어가 자체 타이머로
// 그 배열을 순서대로 재생한다(erm_ramp_test.cpp처럼 BLE 왕복 지연과 무관하게 로컬에서
// 매끄럽게 재생하기 위함 — WavePlayer.h/.cpp 참고). nRF52840 RAM(237KB) 대비 8KB는
// 여유 있는 크기이고, 최소 재생 간격(수 ms) 기준으로도 수 분 분량이라 충분함.
constexpr uint16_t ERM_WAVE_BUFFER_CAPACITY = 8192;

// ===== 배터리 전압 감지 회로 상수 =====
// 분압비 1/3 (R1=20kΩ, R2=10kΩ) 역산: packVoltage = adcVoltage * BATTERY_DIVIDER_RATIO
// (분압 회로 자체는 보드 교체와 무관 — 그대로 유지).
// ADC 절대전압 보정: ESP32의 eFuse 보정 analogReadMilliVolts()는 nRF52840엔 없는 API라
// BatteryMonitor.cpp에서 analogRead() 원시값 * ADC_REFERENCE_MILLIVOLTS / 4095로 환산한다.
// nRF52 Adafruit 코어의 기본 아날로그 기준전압(AR_DEFAULT)은 0.6V 내부 기준 × 6 = 0-3.6V
// 풀스케일(코어 소스로 확인) — BatteryMonitor::begin()에서 analogReference(AR_DEFAULT)로
// 명시적으로 고정해 이 값을 그대로 사용.
// 수동 크로스체크(선택): 배터리를 완충한 직후(충전기 완충 LED 켜짐 시점) packVoltage()가
// 충전기 스펙상 완충 컷오프 전압(2S 기준 보통 8.4V 근방)과 비슷한지 비교해보면 멀티미터 없이도
// 대략적인 보정 확인이 가능함.
constexpr float BATTERY_DIVIDER_RATIO = 3.0f;  // 1 / (R2/(R1+R2))
constexpr uint16_t ADC_REFERENCE_MILLIVOLTS = 3600;  // AR_DEFAULT 풀스케일 (0.6V * 6)
constexpr uint8_t BATTERY_ADC_SAMPLES = 16;
constexpr uint8_t BATTERY_SERIES_CELLS = 2;  // 2S 팩

// 저전압 임계값: "6.0~8.4V 선형 SOC" 근사 대신, 표준 3.7V 리튬이온 셀의 일반적인 OCV(무부하)-SOC
// 곡선을 사용한다(BatteryMonitor.cpp의 SOC_CURVE). 첨부된 KC 안전인증서(XU100690-16004K,
// Shenzhen Taiwoo Battery, KC62133)로 이 배터리가 표준 리튬이온 셀 계열임을 확인함 —
// LiFePO4 등 방전 곡선이 다른 특이 화학이 아니므로 범용 Li-ion 곡선을 그대로 적용해도 무리 없음.
// 단일 셀 20% SOC ≈ 3.73V → 2S 팩 기준 7.46V.
// MENTOR-REVIEW: 그래도 셀 모델별 정확한 곡선은 아니므로 실사용 중 estimateSocPercent() 값과
// 체감(사용 가능 시간)을 비교해 필요시 SOC_CURVE 자체를 조정할 것.
constexpr float BATTERY_LOW_PACK_VOLTAGE = 7.46f;
