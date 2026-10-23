#pragma once
#include <ArduinoJson.h>
#include <cstdint>

// PC가 오디오 엔벨로프 등 임의 파형을 BLE로 통째로 업로드해두면, 여기서 그 배열을 로컬
// 타이머(millis())로 순서대로 ErmDriver에 흘려보낸다 — erm_ramp_test.cpp가 duty를 로컬
// 루프에서 1씩 증감시켰던 것과 같은 원리로, 매 스텝마다 BLE 왕복이 필요 없어 진짜 매끄러운
// 재생이 가능함(HapticProtocol.h의 "t":"wb"/"wc"/"wp"/"ws" 명령 참고).
//
// ERM 전용 — Peltier는 기존 "act" 경로로만 제어됨. "act" 경로로 ERM duty가 직접 지정되면
// (HapticStateMachine.cpp) 재생 중이던 파형은 stop()으로 취소된다 — 두 경로가 동시에
// ErmDriver를 건드리면 안 되므로.
namespace WavePlayer {
void begin();

// type: "wb"(wave_begin)/"wc"(wave_chunk)/"wp"(wave_play)/"ws"(wave_stop) 중 하나.
// 성공 시 true, 실패 시 false + errOut(null 허용)에 원인 문자열.
bool handleCommand(const char* type, JsonVariantConst doc, const char** errOut);

// loop()에서 매번 호출 — 재생 중이면 스텝 간격에 맞춰 다음 샘플을 ErmDriver로 내보낸다.
void update();

// 재생 중단 + ERM off. wave_stop 명령과 act 경로의 ERM 직접 제어, 워치독에서 공통으로 씀.
void stop();

bool isPlaying();
bool isRepeating();  // 워치독(HapticStateMachine)이 "rep"(무기한 반복) 재생을 판별하는 데 씀.
}  // namespace WavePlayer
