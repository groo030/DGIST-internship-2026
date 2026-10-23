#include <Arduino.h>
#include <bluefruit.h>

#include "Config.h"

// BLE(NUS) 광고/연결/수신만 테스트하는 최소 단위 스케치(구 wifi_connect_test.cpp의 BLE판).
// 액추에이터/드라이버/JSON 파싱 등 다른 코드는 전혀 안 건드리고, Bluefruit.begin()으로
// 실제 광고가 나가는지, 중앙 기기(PC)가 붙었을 때 데이터를 주고받을 수 있는지만 확인하는 용도.
// 연결 상태를 계속 반복 출력하고, NUS RX로 뭔가 들어오면 그대로 에코함.

namespace {
BLEUart bleuart;
bool wasConnected = false;
}  // namespace

void setup() {
  Serial.begin(115200);
  uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart) < 1500) {
  }

  Serial.println("=== BLE UART(NUS) 단독 테스트 ===");
  Serial.print("기기 이름: ");
  Serial.println(BLE_DEVICE_NAME);

  Bluefruit.begin();
  Bluefruit.setTxPower(4);
  Bluefruit.setName(BLE_DEVICE_NAME);

  bleuart.begin();

  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(bleuart);
  Bluefruit.ScanResponse.addName();  // 이름은 Scan Response로 — 기본 광고 패킷 31바이트가
                                      // Flags+TxPower+128bit UUID로 이미 꽉 차서 이름이 잘림
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);
  Bluefruit.Advertising.setFastTimeout(30);
  Bluefruit.Advertising.start(0);

  Serial.println("광고 시작 — PC에서 nRF Connect 등으로 스캔/연결해볼 것");
}

void loop() {
  bool connected = Bluefruit.connected();
  if (connected != wasConnected) {
    Serial.println(connected ? "연결됨" : "연결 끊김(재광고 중)");
    wasConnected = connected;
  }

  while (bleuart.available()) {
    Serial.write(static_cast<char>(bleuart.read()));  // 받은 바이트 그대로 USB Serial에 에코
  }

  delay(500);
}
