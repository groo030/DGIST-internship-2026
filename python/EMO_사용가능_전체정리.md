# EMO 사용 가능한 모든 코드·명령 전체 정리 (실전 카탈로그) — 2026-06-19

> "우리가 실제로 쓸 수 있는 모든 것"을 한곳에. 터미널 실행 명령 + 바로 붙여쓰는 Python 코드 + 작동 여부.
> 함께 보기: `EMO_연구노트.md`(구조·판단), `EMO_명령어_레퍼런스.md`(함수·값 전수 파싱).

---

## ★ 작동 여부 등급 (먼저 읽기)

| 등급 | 의미 |
|------|------|
| ✅ **확인됨** | 하드웨어에서 실제로 작동 확인 |
| 🟢 **수락됨** | EMO가 명령을 받고 연결 유지 (효과는 일부 확인) |
| 🟡 **미확인** | 라이브러리에 있으나 fw3.x에서 미테스트 (JSON 채널이라 거부 가능) |
| 🔴 **거부됨** | fw3.x가 거부 (연결 끊음) |
| ⚪ **미구현** | 문자열만 있고 코드 없음 → 직접 JSON 작성 필요 |

---

## 0. 공통 준비 (항상 먼저)

```bash
# 1) 폰의 공식 EMO 앱 종료 (BLE는 1:1)
# 2) EMO를 깨우고, 움직임은 충전대에서 내려놓기
# 3) 진짜 Terminal.app 에서 실행 (다른 셸 X — 블루투스 권한)

cd ~/emo-python-test          # (사용자 환경 경로)
source .venv/bin/activate     # bleak + Pillow 있는 venv
conda deactivate              # conda 베이스 비활성화
```

---

## 1. 터미널에서 바로 쓰는 실행 명령 (4개 스크립트)

### 1.1 움직임 — `emo_move.py` ✅
```bash
python3 emo_move.py            # 자동 데모: 앞→좌→우→뒤돌기
python3 emo_move.py drive      # 키보드 직접 조종
#   W=앞  A=좌  D=우  S=뒤  스페이스/X=정지  Q=종료
```

### 1.2 눈 이미지/텍스트 — `emo_eye.py` (표시 ✅ / 제거 ⚠️)
```bash
python3 emo_eye.py             # 기본 "DGIST" 텍스트
python3 emo_eye.py text HELLO  # 원하는 글자
python3 emo_eye.py dgist       # ~/Desktop/DGIST_UI.png
python3 emo_eye.py logo.png    # 임의 PNG 파일 경로
python3 emo_eye.py solid red   # 진단용 단색 (red/green/blue/white/yellow/black)
```
> 전제: EMO와 노트북이 **같은 2.4GHz WiFi**, 포트 9090 인바운드 허용.

### 1.3 WiFi 설정 — `emo_wifi.py` 🟡
```bash
python3 emo_wifi.py            # 실행 중 SSID/비밀번호 입력 (2.4GHz만!)
```
> 안 되면: 폰 앱으로 WiFi 설정 → 앱 종료 → 위 스크립트들 실행.

### 1.4 서버 도달 진단 (BLE 없음) — `http_test.py`
```bash
python3 http_test.py           # 포트 9090 서버만. 폰 브라우저로 접속 테스트
```

---

## 2. 코드에서 직접 호출하는 모든 명령

> 모든 예제는 아래 **공통 뼈대** 위에서 동작한다.

```python
import asyncio, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from emoconnect.ble.command import CommandUtil
from emoconnect.ble.request import (
    AnimationRequest, SettingRequest, StateRequest,
    CitySetRequest, TimezoneSetRequest, WifiSetRequest,
    PowerRequest, OtaRequest,
)
from emo_move import connect, _is_connected   # 연결 로직 재사용

async def main():
    ecm = await connect()                # 타깃 스캔 + 연결
    if ecm is None: return
    try:
        # ── 여기에 아래 명령들을 넣어 호출 ──
        pass
    finally:
        if _is_connected(ecm):
            await ecm.disconnect()

asyncio.run(main())
```

핵심 전송 함수 2가지:
- `await ecm.sendCommand(바이트)` — 응답 안 기다림 (움직임/대부분)
- `resp = await ecm.sendRequest(바이트)` — 응답 받을 때까지 대기 (⚠️ 타임아웃 없음)

---

### 2.A 움직임 (바이너리 `0xDD 0xCC`) ✅
```python
# 먼저 이동 모드 진입 (필수 시퀀스)
await ecm.sendCommand(CommandUtil.clear());        await asyncio.sleep(0.5)
await ecm.sendCommand(CommandUtil.enterApp(4));    await asyncio.sleep(0.5)  # 4=탐험/이동
await ecm.sendCommand(CommandUtil.startGame());    await asyncio.sleep(0.5)
await ecm.sendCommand(CommandUtil.resetting());    await asyncio.sleep(0.5)
await ecm.sendCommand(CommandUtil.statusOnOff(True))

# 이동
await ecm.sendCommand(CommandUtil.forward())   # 앞     ✅
await ecm.sendCommand(CommandUtil.left())      # 좌회전 ✅
await ecm.sendCommand(CommandUtil.right())     # 우회전 ✅
await ecm.sendCommand(CommandUtil.back())      # 후진   🟡(미확인)
await ecm.sendCommand(CommandUtil.stop())      # 정지   ✅

# 종료
await ecm.sendCommand(CommandUtil.exitApp())
```
| 함수 | 바이트 | 상태 |
|------|--------|------|
| `forward()` | `03 04 05` | ✅ |
| `left()` | `03 04 07` | ✅ |
| `right()` | `03 04 08` | ✅ |
| `back()` | `03 04 06` | 🟡 |
| `stop()` | `03 04 09` | ✅ |

---

### 2.B 댄스/애니메이션 (`anim_req`) 🟡
```python
await ecm.sendCommand(AnimationRequest.enterAnimationMode())   # 진입
await ecm.sendCommand(AnimationRequest.playEmoDance(0))        # 0~10번 댄스
await ecm.sendCommand(AnimationRequest.exitAnimationMode())    # 종료
```
| n | 곡 | n | 곡 |
|---|----|----|----|
| 0 | d1_EmoDance | 6 | d7_FlashBack |
| 1 | d2_WontLetGo | 7 | d8_Click2 |
| 2 | d3_Blindless | 8 | d9_BlameYourself |
| 3 | d4_Click1 | 9 | d10_CanITakeYouThere |
| 4 | d5_TimeOfMyLife | 10 | d11_OceanBlue |
| 5 | d6_Rollercoaster | | |

---

### 2.C 눈 이미지 표시 (`customize_req`/`set_eye`) ✅표시
> 라이브러리에 함수 없음 → `emo_eye.py`가 직접 구현. 코드로 쓰려면 emo_eye의 함수 재사용:
```python
from emo_eye import (prepare_image, push_eye_image, restore_normal_eyes,
                     get_local_ip, RawImageHandler, ReuseTCPServer,
                     encode_json, EMO_HTTP_PORT)
# 핵심: op:in → set_eye(서버 IP:9090에서 PNG 다운로드) → op:out
```
- 포맷 **PNG**, 크기 **320×240** (JPEG 거부).
- 전송 방식: EMO가 노트북 raw TCP 서버(9090)에서 다운로드.
- ⚠️ 제거(다시 끄기)는 미해결 — 투명 PNG 교체 방식 테스트 중.

---

### 2.D 설정 (`setting_req`) 🟡
```python
await ecm.sendCommand(SettingRequest.setVolumeMute())     # 음소거
await ecm.sendCommand(SettingRequest.setVolumeLow())      # 낮음
await ecm.sendCommand(SettingRequest.setVolumeMedium())   # 중간
await ecm.sendCommand(SettingRequest.setVolumeHigh())     # 높음
await ecm.sendCommand(SettingRequest.setTemp(True))       # 온도: 섭씨(False=화씨)
await ecm.sendCommand(SettingRequest.setLength(True))     # 거리: 미터법(False=야드법)
await ecm.sendCommand(SettingRequest.setAutoUpdate(True)) # 자동 업데이트
await ecm.sendCommand(SettingRequest.setSchedule(True))   # 스케줄
await ecm.sendCommand(SettingRequest.setScheduleSound(True))
await ecm.sendCommand(SettingRequest.enterSettingMode())  # / exitSettingMode()
```

---

### 2.E 위치·시간대 🟡
```python
await ecm.sendCommand(CitySetRequest.setLocation("Daegu", country="KR", lat=35.87, lon=128.60))
await ecm.sendCommand(TimezoneSetRequest.setTimezone("Asia/Seoul", code="KST", offset=540))
```

---

### 2.F WiFi / 전원 / 펌웨어 🟡
```python
await ecm.sendCommand(WifiSetRequest.setWifi("SSID_2.4G", "비밀번호"))  # 🟡
await ecm.sendCommand(PowerRequest.powerOff())                          # 🟡 전원 끔
await ecm.sendCommand(OtaRequest.setVersion(300))                       # 🟡 OTA(위험)
```

---

### 2.G 상태 조회 (`sta_req`) 🔴 거부됨
```python
# ⚠️ fw3.x가 이걸 받으면 연결을 끊는다. 사실상 사용 불가.
resp = await ecm.sendRequest(StateRequest.version())
resp = await ecm.sendRequest(StateRequest.everything())  # 0~12 전부
```
조회 항목: deviceid/version/network/xiaoai/alexa/light/alarm/city/timezone/achievements/dancelist/personality/preference

---

### 2.H 하드웨어 디버그 (바이너리, 헤더 `55AA55AA33`) 🟡
```python
await ecm.sendCommand(CommandUtil.debugEnterTestMode())      # 19
await ecm.sendCommand(CommandUtil.debugCameraTest())         # 21
await ecm.sendCommand(CommandUtil.debugDistanceSensorTest()) # 22
await ecm.sendCommand(CommandUtil.debugTouchSensorsTest())   # 24
await ecm.sendCommand(CommandUtil.debugImuAndCompassTest())  # 25
await ecm.sendCommand(CommandUtil.debugExitTestMode())       # 26
# 그 외: debugMicArrayTest(20), debugCliffSensorTest(23)
```

---

## 3. EMO가 보내주는 정보 받기 (수신)

### 3.1 상태 이벤트 콜백 (바이너리)
```python
async def on_cmd(c):
    print("EMO 이벤트:", c)   # StatusAlert / ChargeStatus / HuntResponse
ecm.setCommandCallback(on_cmd)
await ecm.sendCommand(CommandUtil.statusOnOff(True))      # 상태 전송 ON
await ecm.sendCommand(CommandUtil.chargeLevelOnOff(True)) # 배터리 전송 ON
```
주요 상태값(`StatusAlert.Status`): 10흔들림 20쓰다듬 31들림 33충전 52배터리부족 61장애물 62소리 110듣기 120말하기 140춤 240수면 260충전대분리 … (전체는 레퍼런스 2.3)

### 3.2 JSON 응답
- `ecm._resonse` 에 마지막 JSON 응답이 저장됨 → 폴링해서 읽음 (emo_eye/emo_wifi의 `send_and_capture` 패턴).

---

## 4. 라이브러리에 없어 직접 JSON을 짜야 하는 것 ⚪

`encode_json()`(emo_eye) 또는 `ByteUtil.encodePayload()`로 직접 만들어 `sendCommand` 전송.
```python
from emo_eye import encode_json
await ecm.sendCommand(encode_json({"data": {...}, "type": "photo_req"}))
```
| type | 추정 기능 | 비고 |
|------|-----------|------|
| `photo_req` | 카메라 사진 | set_eye처럼 서버 푸시 추정 |
| `face_req` | 얼굴 인식 | 미탐색 |
| `edit_info_req` | 이름/정보 편집 | 미탐색 |
| `alarm_set` | 알람 | 미탐색 |
| `light_set` | 조명 | 미탐색 |
| `customize_req`+`set_eye` | 눈 이미지 | ✅ emo_eye가 이미 구현 |

---

## 5. 새 명령을 추가하는 표준 템플릿

라이브러리에 없는 기능을 만들 때:
```python
# 1) JSON 채널이면:
packet = encode_json({"data": {"op": "원하는op"}, "type": "원하는type"})
await ecm.sendCommand(packet)              # 또는 sendRequest로 응답 확인

# 2) 바이너리 채널이면 (CommandUtil.cmd 패턴):
from emoconnect.ble.command.CommandUtil import cmd
await ecm.sendCommand(cmd([3, 4, 5]))      # data 바이트 리스트
```
규칙:
- JSON: `0xBB 0xAA` + 길이(LE 2바이트) + UTF-8 본문. fw3.x 수락 여부는 **보내봐야** 안다(연결 끊기면 거부).
- 바이너리: `0xDD 0xCC SEQ` + data + 0패딩(17바이트). 움직임은 `sequential=False`.

---

## 6. 우리가 확실히 쓸 수 있는 것 vs 실험 필요한 것 (최종 요약)

**지금 바로 확실히 쓸 수 있는 것** ✅
- 움직임: 앞/좌/우/정지 (`emo_move.py` 또는 CommandUtil)
- 눈 이미지 표시 (`emo_eye.py`, 320×240 PNG)

**라이브러리에 있어 시도하면 될 가능성 높은 것** 🟡 (JSON 채널, 미테스트)
- 댄스 11종, 볼륨/설정, 위치/시간대, WiFi, 전원, 디버그 센서 테스트

**안 되는 것** 🔴
- 상태 조회(`sta_req`) — fw3.x 거부

**더 만들어야 쓰는 것** ⚪
- photo_req/face_req/alarm_set/light_set (직접 JSON), 눈 이미지 "제거"(진행 중)

**BLE로 불가능 → 프록시 필요**
- EMO에게 임의 문장 말하기(TTS), 음성 인식 반응 (emo-libre 클라우드 프록시 경로)
