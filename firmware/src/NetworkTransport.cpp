#include "NetworkTransport.h"

#include <bluefruit.h>

#include "Config.h"

namespace {
BLEUart bleuart;

// 한 줄이 여러 BLE 패킷(ATT MTU 단위)에 걸쳐 나뉘어 도착할 수 있어, '\n'을 만날 때까지
// 바이트를 계속 누적하는 정적 버퍼. readLine()을 얼마나 자주 부르든 블로킹 없이 동작.
// 256으로는 부족했던 걸 실측으로 확인함 — Peltier가 모듈별 독립 제어(peltier1/peltier2)로
// 나뉘면서 실제 JSON 명령이 ~283바이트까지 늘어나자 뒤쪽이 조용히 잘려서 json_parse_error가
// 났었음. 512로 넉넉하게 올려서 향후 필드가 좀 더 늘어나도 여유 있게 함.
constexpr size_t LINE_BUFFER_SIZE = 512;
char lineBuffer[LINE_BUFFER_SIZE];
size_t lineLength = 0;

bool wasConnected = false;
}  // namespace

void NetworkTransport::begin() {
  Bluefruit.begin();
  Bluefruit.setTxPower(4);
  Bluefruit.setName(BLE_DEVICE_NAME);

  bleuart.begin();

  // 광고 페이로드에 NUS 서비스를 포함시켜야 PC 쪽 스캐너가 이 기기를 UART 서비스로 인식함.
  // 기본 광고 패킷은 31바이트 한도라 Flags+TxPower+128bit 서비스 UUID만으로 이미 24바이트를
  // 써버려서 이름 넣을 자리가 5바이트("EMO-H"까지)밖에 안 남음(실측으로 확인됨) — 전체 이름은
  // Scan Response 패킷(별도의 31바이트 예산)에 넣어야 "EMO-Haptic"이 안 잘리고 그대로 보임.
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(bleuart);
  Bluefruit.ScanResponse.addName();

  // 연결 끊기면 자동으로 재광고 시작(기본 동작) — WiFi 쪽의 "재시도 없음" 원칙과 달리
  // BLE는 애초에 대기 전력이 낮아 계속 광고 상태를 유지해도 발열/전력 문제가 없음.
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);  // 20ms ~ 152.5ms
  Bluefruit.Advertising.setFastTimeout(30);
  Bluefruit.Advertising.start(0);  // 0 = 무기한 광고

  Serial.print("BLE 광고 시작: ");
  Serial.println(BLE_DEVICE_NAME);
}

void NetworkTransport::poll() {
  bool connected = Bluefruit.connected();
  if (connected != wasConnected) {
    Serial.println(connected ? "PC(BLE) 연결됨" : "PC(BLE) 연결 끊김");
    wasConnected = connected;
    lineLength = 0;  // 연결이 바뀌면 이전 세션의 미완성 라인은 버림
  }
}

bool NetworkTransport::readLine(String& outLine) {
  while (bleuart.available()) {
    char c = static_cast<char>(bleuart.read());
    if (c == '\n') {
      lineBuffer[lineLength] = '\0';
      outLine = lineBuffer;
      outLine.trim();  // '\r' 등 개행 앞 공백류 제거
      lineLength = 0;
      if (outLine.length() > 0) return true;
      continue;  // 빈 줄이면 계속 다음 데이터를 봄
    }
    if (lineLength < LINE_BUFFER_SIZE - 1) {
      lineBuffer[lineLength++] = c;
    }
    // 버퍼 초과분은 조용히 버림 — 다음 '\n'까지 계속 누적 시도(오작동 방지용 상한).
  }
  return false;
}

void NetworkTransport::println(const char* line) {
  Serial.println(line);  // 로컬 디버그용 — USB 연결돼 있으면 항상 같이 확인 가능
  if (Bluefruit.connected()) {
    bleuart.write(line);
    bleuart.write("\n");
  }
}
