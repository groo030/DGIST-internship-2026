#include "HapticProtocol.h"

#include <ArduinoJson.h>
#include <cstring>

namespace {
bool parseActuator(JsonVariantConst obj, ActuatorRequest& out) {
  if (obj.isNull()) return false;
  out.duty = obj["i"] | 0.0f;  // "i" = duty(0-255) 그대로. 범위 clamp는 SafetyGuard 책임.
  out.direction = obj["dir"] | 0;
  out.durationMs = obj["ms"] | 0;
  return true;
}

bool parseHapticMessageFromDoc(JsonVariantConst doc, HapticCommand& result, const char** errOut) {
  result = HapticCommand{};

  uint16_t version = doc["pv"] | 0;
  if (version != HAPTIC_PROTOCOL_VERSION) {
    if (errOut) *errOut = "unsupported_protocol_version";
    return false;
  }

  JsonVariantConst actuatorParams = doc["act"];
  if (actuatorParams.isNull()) {
    if (errOut) *errOut = "missing_actuator_params";
    return false;
  }
  if (!parseActuator(actuatorParams["p1"], result.peltier1)) {
    if (errOut) *errOut = "missing_peltier1_params";
    return false;
  }
  if (!parseActuator(actuatorParams["p2"], result.peltier2)) {
    if (errOut) *errOut = "missing_peltier2_params";
    return false;
  }
  if (!parseActuator(actuatorParams["erm"], result.erm)) {
    if (errOut) *errOut = "missing_erm_params";
    return false;
  }
  result.erm.direction = 0;  // ERM은 방향 자유도가 하드웨어에 없음 — 파서 단계에서 아예 고정.

  result.protocolVersion = version;
  const char* emotion = doc["emo"] | "";
  strncpy(result.emotion, emotion, sizeof(result.emotion) - 1);
  result.valence = doc["val"] | 0.0f;
  result.arousal = doc["aro"] | 0.0f;
  result.valid = true;
  return true;
}
}  // namespace

bool parseHapticMessage(const char* jsonLine, HapticCommand& result, const char** errOut) {
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, jsonLine);
  if (err) {
    result = HapticCommand{};
    if (errOut) *errOut = "json_parse_error";
    return false;
  }
  return parseHapticMessageFromDoc(doc, result, errOut);
}

bool parseHapticMessage(JsonVariantConst doc, HapticCommand& result, const char** errOut) {
  return parseHapticMessageFromDoc(doc, result, errOut);
}
