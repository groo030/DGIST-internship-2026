# EMO 명령어 레퍼런스 — 파일·함수·값 전수 파싱 (2026-06-19)

> 대상 repo: **`emo-connect-python`** (Clark Scheff / 0xD34D, GPLv3) — 이 작업 디렉터리.
> 별도 "dance 레포지토리"는 없고, **댄스 기능은 이 repo의 `AnimationRequest`**가 담당한다.
> 이 문서는 repo 안의 모든 BLE 명령/함수와 각 값의 의미를 파일별로 정리한 것이다.
>
> 함께 보기: 전반적 구조·판단은 `EMO_연구노트.md`.

---

## 0. 전체 구조 한눈에

```
emo-connect-python/
├─ emo_move.py        ← (우리 작성) 움직임 제어
├─ emo_eye.py         ← (우리 작성) 눈 이미지 표시
├─ emo_wifi.py        ← (우리 작성) WiFi 설정
├─ http_test.py       ← (우리 작성) 서버 도달 진단
└─ src/emoconnect/
   ├─ EmoConstants.py         ← 모든 UUID·문자열 상수
   ├─ EmoConnectManager.py    ← BLE 연결/송수신 핵심
   ├─ util/ByteUtil.py        ← JSON 패킷 인코딩
   └─ ble/
      ├─ command/   ← 바이너리 명령 (0xDD 0xCC) — 움직임/게임
      │   ├─ CommandUtil.py       (명령 생성)
      │   ├─ CommandParser.py     (수신 명령 해석)
      │   ├─ StatusAlert.py       (상태 이벤트 enum)
      │   ├─ ChargeStatus.py      (배터리)
      │   └─ HuntResponse.py      (탐험게임 응답)
      ├─ config/    ← JSON 요청 본문 생성 (0xBB 0xAA)
      │   ├─ BaseConfig / AnimationConfig / StateConfig / SettingConfig
      │   ├─ CitySetConfig / TimezoneSetConfig / WifiSetConfig
      │   └─ PowerConfig / OtaConfig
      └─ request/   ← config를 감싼 사용자용 함수 (이걸 호출하면 됨)
          └─ (config와 1:1 대응)
```

**핵심 원리: config가 JSON 본문을 만들고, `getRequest()`가 `0xBB 0xAA` 헤더를 붙여 최종 BLE 바이트를 반환한다.**
사용자는 보통 `request/*` 함수만 부르면 됨 → 반환된 bytes를 `ecm.sendCommand()` 또는 `ecm.sendRequest()`로 전송.

---

## 1. 두 종류의 패킷 (가장 중요한 구분)

| | 바이너리 명령 | JSON 요청 |
|---|---|---|
| 헤더 | `0xDD 0xCC` | `0xBB 0xAA` |
| 만드는 곳 | `command/CommandUtil.py` | `config/*` + `ByteUtil.encodePayload` |
| 용도 | 움직임, 앱/게임 진입 | 상태, 설정, WiFi, 디스플레이, 댄스 |
| 응답 | 보통 없음(fire-and-forget) | JSON 응답(`_resonse`에 저장) |
| 전송 함수 | `sendCommand()` | `sendCommand()`/`sendRequest()` |
| fw 3.x | ✅ 작동 | ⚠️ 일부만 (sta_req 거부, customize_req 수락) |

### 패킷 포맷
**바이너리** (`CommandUtil.cmd`):
```
[0xDD, 0xCC, SEQ] + data바이트들 + (0으로 채워 총 17바이트)
```
- `SEQ` = 순번(1~254 순환). `sequential=False`면 0 고정(움직임은 0).

**JSON** (`ByteUtil.encodePayload`):
```
[0xBB, 0xAA] + (본문 길이 2바이트 little-endian) + (UTF-8 JSON)
```

---

## 2. command/ — 바이너리 명령 (움직임·게임) `0xDD 0xCC`

### 2.1 `CommandUtil.py` — 명령 생성 함수

| 함수 | 내부 data 바이트 | SEQ | 역할 |
|------|------------------|-----|------|
| `clear()` | `[]` (빈 명령) | 순번 | 화면/상태 초기화 |
| `statusOnOff(on)` | `[0, 0, 1/0]` | 순번 | 상태 업데이트 전송 ON/OFF |
| `chargeLevelOnOff(on)` | `[2, 0, 1/0]` | 순번 | 배터리 레벨 전송 ON/OFF |
| `enterApp(appId)` | `[3, 2, appId]` | 순번 | 앱/게임 진입 (**4 = 탐험/이동 게임**) |
| `exitApp()` | `[3, 1]` | 순번 | 앱 종료 |
| `startGame()` | `[3, 4, 1]` | 순번 | 게임 시작 |
| `resetting()` | `[3, 5, 7]` | 0 | 위치/자세 리셋 |
| `timeout()` | `[3, 5, 8]` | 0 | 타임아웃 |
| **`forward()`** | `[3, 4, 5]` | 0 | **앞으로** ✅ |
| **`back()`** | `[3, 4, 6]` | 0 | **후진** (fw3.x 동작 미확인) |
| **`left()`** | `[3, 4, 7]` | 0 | **좌회전** ✅ |
| **`right()`** | `[3, 4, 8]` | 0 | **우회전** ✅ |
| **`stop()`** | `[3, 4, 9]` | 0 | **정지** ✅ |

**값 해석**:
- 첫 바이트 `3` = "앱/동작 카테고리". 둘째 `4` = "이동 서브명령". 셋째가 방향(5앞/6뒤/7좌/8우/9정지).
- 움직임은 `sequential=False`(SEQ=0) — 순번 없이 즉시 반응해야 하므로.
- `enterApp(4)` 의 `4`가 "탐험(treasure-hunt)/이동 게임" 모드. 이 모드여야 이동 명령이 먹힌다.

**디버그/하드웨어 테스트** (헤더가 다름: `0x55 0xAA 0x55 0xAA 0x33`):
| 함수 | command 값 | 역할 |
|------|-----------|------|
| `debugEnterTestMode()` | 19 | 테스트 모드 진입 |
| `debugMicArrayTest()` | 20 | 마이크 어레이 |
| `debugCameraTest()` | 21 | 카메라 |
| `debugDistanceSensorTest()` | 22 | 거리 센서 |
| `debugCliffSensorTest()` | 23 | 낭떠러지 센서 |
| `debugTouchSensorsTest()` | 24 | 터치 센서 |
| `debugImuAndCompassTest()` | 25 | IMU/나침반 |
| `debugExitTestMode()` | 26 | 테스트 모드 종료 |
| `debug_cmd_27()` | 27 | (용도 미상) |

> 이동 모드 진입 표준 시퀀스 (movement_example.py / emo_move.py 공통):
> `clear()` → `enterApp(4)` → `startGame()` → `resetting()` → `statusOnOff(True)` → `chargeLevelOnOff(True)`

### 2.2 `CommandParser.py` — EMO가 보내는 바이너리 응답 해석
수신 payload 앞 2바이트로 분기:
| payload[0:2] | 해석 클래스 | 의미 |
|--------------|-------------|------|
| `[2, 0]` | `ChargeStatus(payload[2])` | 배터리 레벨 |
| `[0, 0]` | `StatusAlert(Status)` | 상태 이벤트 (아래 표) |
| `[3, 5]` | `HuntResponse(status, sub_status)` | 탐험게임 응답 |
| 그 외 | `None` | 미상 |

### 2.3 `StatusAlert.py` — EMO 상태 이벤트 enum (`Status`)
EMO가 자기 상태가 바뀔 때 보내주는 이벤트 코드. (statusOnOff(True)일 때 수신)

| 값 | 이름 | 의미 |
|----|------|------|
| 10 | BEING_SHAKEN | 흔들림 |
| 20 | BEING_PETTED | 쓰다듬어짐 |
| 31 | PICKED_UP | 들어올려짐 |
| 32 | FALLS_DOWN | 넘어짐 |
| 33 | CHARGING | 충전 중 |
| 34 | PUT_DOWN | 내려놓아짐 |
| 40 | EMERGING_FROM_CLIFF | 낭떠러지 회피 |
| 51 | HEADSET_CHANGE | 헤드셋 변경 |
| 52 | LOW_POWER | 배터리 부족 |
| 61 | OBSTACLE_DETECTED | 장애물 감지 |
| 62 | SOUND_DETECTED | 소리 감지 |
| 90 | PLAYING_GAMES | 게임 중 |
| 100 | HAVING_FUN | 즐거움 |
| 110 | LISTENING | 듣는 중 |
| 120 | SPEAKING | 말하는 중 |
| 130 | PLAYING_MUSIC | 음악 재생 |
| 140 | DANCING | 춤추는 중 |
| 150 | BEING_HELPFUL | 도움 행동 |
| 160 | MOVING | 이동 중 |
| 170 | LISTENING_CHATGPT | ChatGPT 듣기 |
| 180 | ANSWERING_QUESTIONS | 질문 답변 |
| 190 | MOVING_TO_TARGET | 목표로 이동 |
| 200/210 | LOOKING_AT_FACE | 얼굴 바라봄 |
| 220 | SEES_NON_HUMAN | 비인간 인식 |
| 230 | STAYING | 머무름 |
| 240 | SLEEPING | 수면 |
| 260 | REMOVED_FROM_CHARGER | 충전대에서 분리 |
| 270 | LOOKING_AROUND | 둘러봄 |
| 281/282 | BEING_HAPPY / BEING_SAD | 기쁨/슬픔 |
| 290 | EXPLORING | 탐험 |
| 300 | SEARCHING | 탐색 |
| 310 | PLAYING | 노는 중 |

### 2.4 `ChargeStatus.py` / `HuntResponse.py`
- `ChargeStatus(charge_level: int)` — 배터리 잔량.
- `HuntResponse(status, sub_status)` — 탐험게임 진행 상태(두 정수).

---

## 3. config/ + request/ — JSON 요청 (`0xBB 0xAA`)

> 패턴: `request/X.py`의 함수 → `config/XConfig.py`가 JSON 생성 → `getRequest()`가 헤더 붙여 bytes 반환.

### 3.1 AnimationRequest / AnimationConfig — **댄스/애니메이션** 🕺
`type: "anim_req"`. `Op` enum: `IN='in'`, `OUT='out'`, `PLAY='play'`.

| 함수 | 보내는 JSON | 역할 |
|------|-------------|------|
| `enterAnimationMode()` | `{"data":{"op":"in"},"type":"anim_req"}` | 애니메이션 모드 진입 |
| `exitAnimationMode()` | `{"data":{"op":"out"},"type":"anim_req"}` | 애니메이션 모드 종료 |
| `playEmoDance(n)` | `{"data":{"name":DANCE_LIST[n],"op":"play"},"type":"anim_req"}` | n번 댄스 재생 |

**`DANCE_LIST` (인덱스 → 댄스 이름)** — `playEmoDance(n)`의 `n`이 이 인덱스:
| n | 이름 |
|---|------|
| 0 | d1_EmoDance |
| 1 | d2_WontLetGo |
| 2 | d3_Blindless |
| 3 | d4_Click1 |
| 4 | d5_TimeOfMyLife |
| 5 | d6_Rollercoaster |
| 6 | d7_FlashBack |
| 7 | d8_Click2 |
| 8 | d9_BlameYourself |
| 9 | d10_CanITakeYouThere |
| 10 | d11_OceanBlue |

예) `playEmoDance(4)` → "d5_TimeOfMyLife" 춤. (PLAY일 때만 `name` 필드가 들어감.)

### 3.2 StateRequest / StateConfig — **상태 조회** (⚠️ fw3.x 거부)
`type: "sta_req"`. 본문 `{"data":{"request":[코드들]},"type":"sta_req"}`.
**주의: fw3.x에서 이 sta_req를 보내면 EMO가 연결을 끊는다.**

`State` enum (요청 코드):
| 코드 | 이름 | 조회 함수 |
|------|------|-----------|
| 0 | DEVICEID | `deviceid()` |
| 1 | VERSION | `version()` |
| 2 | NETWORK | `network()` |
| 3 | XIAOAI | `xiaoai()` |
| 4 | ALEXA | `alexa()` |
| 5 | LIGHT | `light()` |
| 6 | ALARM | `alarm()` |
| 7 | CITY | `city()` |
| 8 | TIMEZONE | `timezone()` |
| 9 | ACHIEVEMENTS | `achievements()` |
| 10 | DANCE_LIST | `dancelist()` |
| 11 | PERSONALITY | `personality()` / `versionAndPersonality()` |
| 12 | PREFERENCE | `preference()` |

- `everything()` — 0~12 전부 한 번에 요청.
- `versionAndPersonality()` — `[11, 1]` (성격 + 버전).

### 3.3 SettingRequest / SettingConfig — **설정**
`type: "setting_req"`. 본문 `{"data":{"op":...},"type":"setting_req"}`.

| 함수 | op 값 | 역할 |
|------|-------|------|
| `enterSettingMode()` | `in` | 설정 모드 진입 |
| `exitSettingMode()` | `out` | 설정 모드 종료 |
| `setAutoUpdate(on)` | `auto_update_on/off` | 자동 업데이트 |
| `setLength(useMetric)` | `length_metric/imperial` | 거리 단위 (미터법/야드법) |
| `setTemp(useCelsius)` | `temp_c/temp_f` | 온도 단위 (섭씨/화씨) |
| `setSchedule(on)` | `schedule_on/off` | 스케줄 |
| `setScheduleSound(on)` | `schedule_s_on/off` | 스케줄 소리 |
| `setVolumeMute()` | `volume_mute` | 음소거 |
| `setVolumeLow()` | `volume_low` | 볼륨 낮음 |
| `setVolumeMedium()` | `volume_med` | 볼륨 중간 |
| `setVolumeHigh()` | `volume_high` | 볼륨 높음 |

### 3.4 WifiSetRequest / WifiSetConfig — **WiFi 설정**
`type: "wifi_set"`. 본문 `{"data":{"ssid":...,"password":...},"type":"wifi_set"}`.
- `setWifi(ssid, password)` — EMO를 WiFi에 연결. **EMO는 2.4GHz만 지원.**
- `emo_wifi.py`가 이걸 사용. fw3.x 수락 여부 미확인 → 안 되면 폰 앱으로 대체.

### 3.5 CitySetRequest / CitySetConfig — **도시/위치 설정**
`type: "city_set"`.
- `setLocation(name, country='', state='', id=0, lat=0.0, lon=0.0)`
- 날씨 등에 쓰는 위치. `coord: {lat, lon}` 좌표 포함.

### 3.6 TimezoneSetRequest / TimezoneSetConfig — **시간대 설정**
`type: "timezone_set"`.
- `setTimezone(name, code='', offset=0)`
- `offset` = UTC 기준 오프셋(분/초 단위는 펌웨어 정의).

### 3.7 PowerRequest / PowerConfig — **전원 끄기**
`type: "off_req"`. 본문 `{"type":"off_req"}` (data 없음).
- `powerOff()` — EMO 전원 종료.

### 3.8 OtaRequest / OtaConfig — **펌웨어(OTA)**
`type: "ota"`. 본문 `{"num":버전,"type":"ota"}`.
- `setVersion(versionNum)` — OTA 버전 지정. (위험, 일반 사용 X)

### 3.9 customize_req / set_eye — **눈 이미지 표시** (라이브러리에 없음, 우리가 직접 구현)
> **이 repo에는 디스플레이용 config/request 클래스가 없다.** EmoConstants에 문자열만 존재.
> 그래서 `emo_eye.py`에서 JSON을 손으로 만들었다. 상세는 `EMO_연구노트.md` 3장.

`type: "customize_req"`. 응답은 `eye_rsp`.
| 단계 | JSON | 역할 |
|------|------|------|
| 진입 | `{"data":{"op":"in"},"type":"customize_req"}` | 커스터마이즈 모드 (result:1) |
| 표시 | `{"data":{"image":{"length":N,"name":"sticker.png","tran":100},"op":"set_eye","server":{"ip":IP,"port":9090}},"type":"customize_req"}` | EMO가 IP:9090에서 이미지 다운로드 |
| 종료 | `{"data":{"op":"out"},"type":"customize_req"}` | 모드 종료 |

값 의미:
- `length` = 이미지 바이트 수 (EMO가 이만큼 읽음)
- `name` = 파일명 (EMO가 raw TCP로 이 이름을 보냄)
- `tran` = 추정 "투명도"였으나 **실험상 투명도 아님**(의미 미상)
- `server.ip/port` = 노트북 주소 (포트 9090)
- 다운로드는 **HTTP 아님, raw TCP** / 이미지는 **320×240 PNG**.

---

## 4. EmoConstants.py — 모든 문자열/UUID 상수

### 4.1 GATT UUID
```
SERVICE_UUID = 0000ffe0-0000-1000-8000-00805f9b34fb
WRITE_UUID   = 0000ffe1-...   (명령 쓰기)
NOTIFY_UUID  = 0000ffe1-...   (응답 수신)
```

### 4.2 요청/응답 타입 문자열 (req → rsp 쌍)
| 요청 (보냄) | 응답 (받음) | 기능 |
|-------------|-------------|------|
| `customize_req` | `eye_rsp` | 눈 이미지 |
| `anim_req` | `anim_rsp` | 댄스/애니메이션 |
| `sta_req` | `sta_rsp` | 상태 조회 |
| `setting_req` | `setting_rsp` | 설정 |
| `wifi_set` / `wifi_syn` | `wifi_rsp` | WiFi |
| `city_set` | `city_rsp` | 도시 |
| `timezone_set` | `timezone_rsp` | 시간대 |
| `alarm_set` | `alarm_rsp` | 알람 |
| `light_set` | `light_rsp` | 조명 |
| `off_req` | `off_rsp` | 전원 |
| `photo_req` | `photo_rsp` | 사진 (set_eye와 유사한 서버 푸시) |
| `face_req` | `face_rsp` | 얼굴 인식 |
| `edit_info_req` | `edit_info_rsp` | 정보 편집(이름 등) |
| `xiaoai_set` | `xiaoai_rsp` | 샤오아이 |
| `ota` | `ota_rsp` | 펌웨어 |

> **참고**: `photo_req`, `face_req`, `edit_info_req`, `alarm_set`, `light_set`은 EmoConstants에 문자열만 있고 **request/config 클래스가 없다** → 쓰려면 customize_req처럼 직접 JSON을 만들어야 함. (아직 안 써봄)

### 4.3 앱 타입 상수
```
EMO_APP_TYPE_WIFI = 1, XIAOAI = 2, VERSION_UPDATE = 3, CITY = 5
```

---

## 5. 핵심 인프라 파일

### 5.1 `EmoConnectManager.py`
| 메서드 | 역할 |
|--------|------|
| `connectToEmo(device=None)` | 연결. macOS는 `device`(타깃 스캔 결과) 주입 필수 |
| `sendCommand(bytes)` | 쓰기만(응답 대기 X) — 움직임/바이너리 |
| `sendRequest(bytes)` | 쓰고 `_resonse` 채워질 때까지 대기 (타임아웃 없음 ⚠️) |
| `setCommandCallback(fn)` | 수신 바이너리 명령 콜백 등록 |
| `_handle_rx` | 수신 라우터: `0xBBAA`→JSON→`_resonse`, `0xDDCC`→CommandParser |

### 5.2 `util/ByteUtil.py`
- `encodePayload(json문자열)` → `[0xBB,0xAA] + 길이2바이트(LE) + UTF-8` 반환.

### 5.3 `ble/config/BaseConfig.py`
- 모든 Config의 부모. `toJson()`(자식 구현) + `getRequest()`(= `encodePayload(toJson())`).

---

## 6. 우리가 만든 4개 스크립트와 호출 관계

| 스크립트 | 핵심 호출 | 채널 | 상태 |
|----------|-----------|------|------|
| `emo_move.py` | `CommandUtil.forward/left/right/stop` + `enterApp(4)` | 0xDDCC | ✅ |
| `emo_eye.py` | 직접 만든 `customize_req`/`set_eye` JSON + raw TCP 서버 | 0xBBAA+TCP | 표시✅/제거⚠️ |
| `emo_wifi.py` | `WifiSetRequest.setWifi()` | 0xBBAA | ❓ |
| `http_test.py` | (BLE 없음) 포트 9090 서버만 | — | 진단용 |

---

## 7. 아직 안 써본, 바로 쓸 수 있는 기능 (정리)

**라이브러리에 구현돼 있어 함수 호출만 하면 되는 것** (단, JSON 채널이라 fw3.x 수락 여부는 실행 확인 필요):
- **댄스**: `AnimationRequest.playEmoDance(0~10)` — 11개 내장 댄스 (위 3.1 표)
- **볼륨/설정**: `SettingRequest.setVolume*/setTemp/setLength/...`
- **위치/시간대**: `CitySetRequest.setLocation`, `TimezoneSetRequest.setTimezone`
- **전원**: `PowerRequest.powerOff()`
- **상태조회**: `StateRequest.*` (단 sta_req는 fw3.x 거부 전례)

**문자열만 있고 클래스가 없어 직접 JSON을 짜야 하는 것** (미구현, 잠재 기능):
- `photo_req` (카메라 사진 — set_eye처럼 서버 푸시 방식 추정)
- `face_req` (얼굴 인식), `edit_info_req` (이름 편집)
- `alarm_set` (알람), `light_set` (조명)

**바이너리 디버그 기능**: `CommandUtil.debug*` — 카메라/마이크/거리/IMU 등 하드웨어 테스트 (위 2.1).
