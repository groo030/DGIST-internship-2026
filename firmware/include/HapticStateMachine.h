#pragma once

namespace HapticStateMachine {
// BOOT: 핀/PWM을 안전 상태로 구성하고, STABILIZE_MS 경과 후에만 드라이버를 깨운다(원칙 5).
void begin();

// setup() 이후 매 loop() 호출마다 실행 — Serial 폴링, 채널 만료/워치독 처리, 배터리 체크.
void loop();
}  // namespace HapticStateMachine
