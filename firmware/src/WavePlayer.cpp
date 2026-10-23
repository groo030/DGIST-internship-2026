#include "WavePlayer.h"

#include <Arduino.h>

#include <cstring>

#include "Config.h"
#include "ErmDriver.h"

namespace {
uint8_t buffer[ERM_WAVE_BUFFER_CAPACITY];
uint16_t totalSamples = 0;
uint32_t stepMs = 0;
bool repeatFlag = false;
bool playing = false;
uint16_t currentIndex = 0;
uint32_t lastStepAt = 0;

bool handleWaveBegin(JsonVariantConst doc, const char** errOut) {
  uint32_t n = doc["n"] | 0;
  uint32_t ms = doc["ms"] | 0;
  bool rep = (doc["rep"] | 0) != 0;
  if (n == 0 || n > ERM_WAVE_BUFFER_CAPACITY) {
    if (errOut) *errOut = "wave_bad_sample_count";
    return false;
  }
  if (ms == 0) {
    if (errOut) *errOut = "wave_bad_step_ms";
    return false;
  }

  playing = false;
  ErmDriver::off();
  totalSamples = static_cast<uint16_t>(n);
  stepMs = ms;
  repeatFlag = rep;
  currentIndex = 0;
  memset(buffer, 0, totalSamples);
  return true;
}

bool handleWaveChunk(JsonVariantConst doc, const char** errOut) {
  uint32_t offset = doc["off"] | 0;
  JsonArrayConst data = doc["d"];
  if (data.isNull()) {
    if (errOut) *errOut = "wave_missing_data";
    return false;
  }
  if (offset + data.size() > totalSamples) {
    if (errOut) *errOut = "wave_chunk_out_of_range";
    return false;
  }

  size_t i = offset;
  for (JsonVariantConst v : data) {
    int value = v | 0;
    if (value < 0) value = 0;
    if (value > 255) value = 255;
    buffer[i] = static_cast<uint8_t>(value);
    i++;
  }
  return true;
}

bool handleWavePlay(const char** errOut) {
  if (totalSamples == 0) {
    if (errOut) *errOut = "wave_not_uploaded";
    return false;
  }
  currentIndex = 0;
  playing = true;
  lastStepAt = millis();
  ErmDriver::setOutput(buffer[0]);
  return true;
}
}  // namespace

void WavePlayer::begin() {
  totalSamples = 0;
  playing = false;
}

bool WavePlayer::handleCommand(const char* type, JsonVariantConst doc, const char** errOut) {
  if (strcmp(type, "wb") == 0) return handleWaveBegin(doc, errOut);
  if (strcmp(type, "wc") == 0) return handleWaveChunk(doc, errOut);
  if (strcmp(type, "wp") == 0) return handleWavePlay(errOut);
  if (strcmp(type, "ws") == 0) {
    WavePlayer::stop();
    return true;
  }
  if (errOut) *errOut = "unknown_wave_type";
  return false;
}

void WavePlayer::update() {
  if (!playing) return;
  uint32_t now = millis();
  if (now - lastStepAt < stepMs) return;
  lastStepAt += stepMs;  // 드리프트 누적 방지 — now로 덮어쓰지 않고 스텝 간격만큼만 전진

  currentIndex++;
  if (currentIndex >= totalSamples) {
    if (repeatFlag) {
      currentIndex = 0;
    } else {
      WavePlayer::stop();
      return;
    }
  }
  ErmDriver::setOutput(buffer[currentIndex]);
}

void WavePlayer::stop() {
  playing = false;
  ErmDriver::off();
}

bool WavePlayer::isPlaying() { return playing; }
bool WavePlayer::isRepeating() { return repeatFlag; }
