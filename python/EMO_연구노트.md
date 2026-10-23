# EMO 제어 연구 노트 (2026-06-18)

> 목표: EMO 로봇(living.ai 데스크톱 펫)을 Mac에서 Python/BLE로 제어해서
> (1) 눈 화면에 커스텀 이미지/텍스트(DGIST 로고) 표시, (2) 움직임 제어.
>
> 이 문서는 지금까지의 조사·실험·판단을 한곳에 정리한 것이다.
> "어떤 코드가 어떤 일을 하는지 / 어떤 포맷을 써야 하는지 / 무엇이 되고 무엇이 안 되는지 /
> 어떤 .py를 언제 쓰는지 / 참고 repo와 거기서 얻은 정보 / 아직 안 써본 추가 기능"을 다룬다.

---

## 0. 한눈에 보는 결론 (TL;DR)

| 기능 | 채널 | 상태 |
|------|------|------|
| BLE 연결 (macOS) | GATT ffe0/ffe1 | ✅ **작동** (타깃 스캔 필수) |
| 움직임 (앞/좌/우/정지) | 바이너리 `0xDD 0xCC` | ✅ **작동** (fw 3.x에서 확인) |
| 후진 `back()` | 바이너리 `0xDD 0xCC` | ❓ 정의는 됨, 수동 드라이브에서 동작 미확인 |
| 상태 조회 `sta_req` | JSON `0xBB 0xAA` | ❌ **거부** (fw 3.x가 연결 끊음) |
| 커스터마이즈 진입 `customize_req{op:in}` | JSON `0xBB 0xAA` | ✅ **수락** (result:1) |
| 이미지 표시 `set_eye` | JSON + raw TCP 9090 | ✅ **표시됨** (PNG, 320×240) |
| 이미지 제거 | — | ⚠️ **미해결** (아래 5장 참고) |
| WiFi 설정 `wifi_set` | JSON `0xBB 0xAA` | ❓ 미확인 (폰 앱 대체 가능) |

**핵심 발견**
- EMO 펌웨어 3.x는 **JSON 채널 중 `sta_req`만 거부**하고, `customize_req`(디스플레이) 계열은 **수락**한다.
- 움직임이 되는 이유는 그게 **별도의 바이너리 채널(`0xDD 0xCC`)**이기 때문.
- 이미지 표시는 **EMO가 노트북의 서버에서 파일을 내려받는(pull)** 방식이다. BLE로 이미지 바이트를 직접 못 보낸다.
- EMO의 파일 다운로드는 **HTTP가 아니라 raw TCP** (파일명 한 줄 보내고 → 원시 바이트 받음).
- 화면 규격은 **320×240, PNG**. (JPEG는 거부됨.)

---

## 1. BLE 통신 구조

### 1.1 GATT 식별자 (`src/emoconnect/EmoConstants.py`)
```python
SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
WRITE_UUID   = "0000ffe1-0000-1000-8000-00805f9b34fb"  # 명령 쓰기
NOTIFY_UUID  = "0000ffe1-0000-1000-8000-00805f9b34fb"  # 응답 수신(notify)
```
- 쓰기/알림이 **같은 캐릭터리스틱(ffe1)**을 공유한다.
- MTU=200, write-without-response/write/notify/read 모두 지원.

### 1.2 두 개의 프로토콜 채널
EMO는 헤더 2바이트로 패킷 종류를 구분한다.

| 헤더 | 종류 | 용도 | 응답 |
|------|------|------|------|
| `0xBB 0xAA` | **JSON 요청** | 상태조회, WiFi, 디스플레이, 설정 | `eye_rsp`, `sta_rsp` 등 JSON 응답 |
| `0xDD 0xCC` | **바이너리 명령** | 움직임, 앱 진입/종료, 게임 | 보통 fire-and-forget |

**JSON 패킷 포맷** (`src/emoconnect/util/ByteUtil.py` → `encodePayload`):
```
[0xBB, 0xAA] + (본문 길이 2바이트, little-endian) + (UTF-8 JSON 본문)
```
`emo_eye.py`의 `encode_json()`이 이걸 직접 구현한 것:
```python
def encode_json(obj: dict) -> bytes:
    body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return bytes([0xBB, 0xAA]) + len(body).to_bytes(2, "little") + body
```

**바이너리 패킷 포맷** (`src/emoconnect/ble/command/CommandUtil.py` → `cmd`):
```
[0xDD, 0xCC, SEQ] + data... + (0으로 패딩하여 총 17바이트)
```

### 1.3 연결 매니저 (`src/emoconnect/EmoConnectManager.py`)
핵심 메서드:
- `connectToEmo(device=None)` — `device`를 주면 그 BLEDevice로 바로 연결(**macOS 필수**, 1.4 참고). 안 주면 라이브러리 기본 필터 스캔.
- `sendCommand(bytes)` — 응답을 안 기다리고 쓰기만 함 (움직임/바이너리용).
- `sendRequest(bytes)` — 쓰고 `_resonse`가 채워질 때까지 **무한 대기** (타임아웃 없음 → 직접 폴링 권장).
- 수신 콜백 `_handle_rx`가 들어온 패킷을 파싱해서:
  - `0xBB 0xAA` → JSON 디코드 후 `self._resonse`에 저장 (그래서 우리는 `ecm._resonse`를 폴링한다)
  - `0xDD 0xCC` → CommandParser로 파싱

### 1.4 macOS에서의 함정 (해결 완료)
1. **블루투스 권한**: 다른 셸이 아니라 **진짜 Terminal.app**에서 실행해야 함 (아니면 SIGABRT).
2. **타깃 스캔 필수**: macOS 일반 스캔은 advertisement에서 service_uuids를 숨겨서 라이브러리 기본 필터가 실패함. → `BleakScanner.discover(service_uuids=["0000ffe0-..."])`로 직접 찾아 `device=`로 주입.
   - 이 로직이 `emo_move.py`의 `find_emo_device()`.
3. **BLE는 1:1**: 폰의 공식 EMO 앱이 잡고 있으면 노트북이 못 잡음 → 앱 종료 필요.
4. EMO가 **깨어 있어 광고 중**일 때만 검색됨.

---

## 2. 루트의 실행 스크립트 (.py) 목록

| 파일 | 기능 | 언제 쓰나 |
|------|------|-----------|
| **`emo_move.py`** | BLE 연결 + 움직임(WASD/데모) | 움직임 제어. 연결 로직(`connect`, `find_emo_device`, `_is_connected`)을 다른 스크립트가 재사용 |
| **`emo_eye.py`** | 눈 화면에 이미지/텍스트 표시 | 디스플레이 (이 프로젝트의 메인 작업) |
| **`emo_wifi.py`** | BLE로 EMO를 WiFi에 연결 | `emo_eye.py` 전에 EMO를 노트북과 같은 WiFi에 붙일 때 |
| **`http_test.py`** | BLE 없이 포트 9090 서버만 띄움 | 이미지 전송 실패 시 "네트워크/방화벽 문제인지"를 분리 진단 |

### 2.1 `emo_move.py` (움직임 — ✅ 작동)
- `connect()` — 타깃 스캔으로 EMO 찾아 연결, `EmoConnectManager` 반환. **다른 스크립트가 import해서 재사용.**
- `enter_drive_mode()` — clear → enterApp(4) → startGame → resetting → status ON 시퀀스로 이동 모드 진입.
- 실행:
  - `python3 emo_move.py` — 데모(앞→좌→우→뒤돌기)
  - `python3 emo_move.py drive` — 키보드 실시간 조종 (W앞 A좌 D우 S뒤 space정지 Q종료)
- 명령 바이트는 emo-libre 문서와 대조 검증됨: forward=`0304 05`, left=`0304 07`, right=`0304 08`, stop=`0304 09`.
- **주의**: EMO는 충전대(스케이트보드)에서 내려야 움직임.

### 2.2 `emo_eye.py` (디스플레이 — 표시 ✅ / 제거 ⚠️)
3장에서 상세히 다룸.

### 2.3 `emo_wifi.py` (WiFi 설정)
- `WifiSetRequest.setWifi(ssid, pw)` → JSON `{"data":{"ssid","password"},"type":"wifi_set"}` 전송.
- **fw 3.x 수락 여부 미확인.** 안 되면 **폰 공식 앱으로 WiFi 설정 → 앱 종료(BLE 해제) → 노트북 스크립트 실행** (WiFi는 BLE 끊겨도 유지됨).
- EMO는 **2.4GHz만** 지원 (5GHz 불가).

### 2.4 `http_test.py` (진단용)
- BLE를 안 쓰고 포트 9090에 표준 HTTP 서버만 띄움.
- 같은 WiFi의 폰 브라우저로 `http://<노트북IP>:9090/sticker.png` 접속해서 이미지가 보이면 → 서버·방화벽·네트워크는 정상.
- **이미 검증 완료**: 폰에서 접속 성공 → 네트워크는 문제 아님이 밝혀짐.

---

## 3. 이미지 표시 메커니즘 (`emo_eye.py`)

### 3.1 전체 흐름 (3단계)
```
[1단계] customize_req {op:in}  → 커스터마이즈 모드 진입 (result:1 확인)
[2단계] set_eye               → EMO에게 "내 서버 ip:port에서 sticker.png 받아가" 라고 알림
        → EMO가 raw TCP로 노트북 9090 포트에 접속해 이미지 다운로드 → 화면 표시
[3단계] (정리) 오버레이 제거 시도 + customize_req {op:out}
```

### 3.2 `set_eye` JSON 구조
```python
set_eye = {
    "data": {
        "image": {"length": len(data), "name": "sticker.png", "tran": 100},
        "op": "set_eye",
        "server": {"ip": ip, "port": 9090},
    },
    "type": "customize_req",
}
```
- `length` — 이미지 바이트 수 (EMO는 이 숫자만큼 읽어감).
- `name` — 파일명 (EMO가 raw TCP로 이 이름을 보냄).
- `tran` — 처음엔 "투명도"로 추정했으나 **실험 결과 투명도가 아님** (tran:0으로도 이미지 그대로 표시됨). 정확한 의미 미상.
- `server.ip/port` — EMO가 접속할 노트북 주소.

### 3.3 EMO의 다운로드 = HTTP가 아니라 raw TCP ⭐
가장 중요한 발견. 처음엔 `http.server`로 띄웠더니:
```
code 400, message Bad request syntax ('sticker.png')
```
즉 EMO가 보낸 요청 첫 줄이 `GET /sticker.png HTTP/1.1`이 아니라 **그냥 `sticker.png`**였다.
→ EMO는 **표준 HTTP를 모른다.** 단순 프로토콜: 접속 → 파일명 한 줄 전송 → 원시 바이트 받기.

해결: `http.server`를 버리고 `socketserver.ThreadingTCPServer` 기반의 `RawImageHandler`로 교체.
```python
class RawImageHandler(socketserver.BaseRequestHandler):
    data: bytes = b""
    def handle(self):
        req = self.request.recv(2048)            # EMO가 보낸 파일명 읽고(로깅)
        self.request.sendall(RawImageHandler.data)  # 원시 이미지 바이트 전송
```
이걸 바꾼 뒤 **EMO가 실제로 접속해서 이미지를 받아가고 얼굴이 바뀜.**

### 3.4 이미지 포맷/규격 (실험으로 확정)
- **포맷: PNG만.** JPEG를 보냈더니 얼굴이 전혀 안 바뀜 → EMO가 헤더 검사에서 JPEG 거부.
- **크기: 320×240 (가로형).**
  - 단색 빨강이 240×320으로 "꽉 찬" 건 픽셀 수(76800)가 같아서 폭이 틀려도 똑같이 보였던 것(균일색은 stride 오류를 숨김).
  - 글자/로고가 가로로 ~3번 반복돼 깨진 건 **실제 폭이 320**이기 때문.
  - 구조가 있는 그림(로고/글자)이라야 폭 오류가 드러난다.
- 출처: emo-libre 펌웨어 분석에서 EMO 얼굴 = 320×240 MJPEG/AVI (K210 칩) 확인.

### 3.5 이미지 정규화 (`normalize_for_emo`)
임의 이미지를 EMO 규격으로 변환:
```python
# (현재 버전) 알파 보존 방식
src = Image.open(...).convert("RGBA")
canvas = Image.new("RGBA", (320,240), (0,0,0,0))  # 완전 투명 배경
fitted = src.copy(); fitted.thumbnail((320,240), LANCZOS)  # 비율 유지 축소
canvas.paste(fitted, (가운데 좌표), fitted)        # 레터박스 + 알파 마스크
canvas.save(buf, format="PNG")
```
- 이전: 알파를 검은 배경에 합성(평탄화)했음.
- 현재: **투명 배경 유지** — EMO가 PNG 알파를 인식하는지 검증 중 (5장 참고).

### 3.6 이미지 생성 헬퍼
- `make_text_image(text)` — 투명 배경에 흰 글자, 화면 폭에 맞춰 폰트 자동 크기.
- `make_solid_image(color)` — 단색 320×240 (진단용: red/green/blue/white/yellow/black).
- `make_clear_image()` — 완전 투명 320×240 (오버레이 제거 시도용).

### 3.7 실행법
```
python3 emo_eye.py              # 기본 "DGIST" 텍스트
python3 emo_eye.py text HELLO   # 원하는 글자
python3 emo_eye.py solid red    # 진단용 단색
python3 emo_eye.py dgist        # ~/Desktop/DGIST_UI.png
python3 emo_eye.py logo.png     # 임의 PNG 파일 경로
```
**전제조건**: EMO와 노트북이 같은 2.4GHz WiFi, 포트 9090 인바운드 허용.

---

## 4. 응답 코드 (emo-libre 문서 기준)
- `result:1` = 성공/시작 (op:in, op:out이 반환)
- `result:0` = 실패
- `result:3` = 완료(오류 포함) — 한때 set_eye가 result:3을 반환했는데, 이는 "다운로드 실패로 완료"였음(네트워크/HTTP 문제). raw TCP로 고친 뒤 정상 표시됨.

---

## 5. 이미지 "제거"가 안 되는 문제 (현재 진행 중) ⚠️

표시는 성공했지만, **떠 있는 이미지를 다시 치우는 것**이 미해결 과제다.
이미지는 **살아있는 눈 위에 얹히는 오버레이**이고, 우리 정규화가 만든 화면이 눈을 덮고 있다.

### 시도한 방법과 결과
| 시도 | 방법 | 결과 |
|------|------|------|
| 1 | `clear_eye` op (`{"op":"clear_eye","type":"customize_req"}`) | ❌ EMO가 무시 |
| 2 | 검은 화면으로 덮어쓰기 | ⚠️ 작동하지만 "눈이 안 보인다"고 사용자 거부 |
| 3 | `anim_req` in→out (애니메이션 모드 진입/해제로 얼굴 재그리기 유도) | ❌ 효과 없음 |
| 4 | 같은 이미지를 `tran:0`으로 재전송 (투명도 가설) | ❌ 이미지 그대로 → **tran은 투명도가 아님** |
| 5 (현재) | **완전 투명 PNG로 교체** + 정규화 시 투명 배경 사용 | ⏳ **테스트 대기 중** |

### 시도 5의 논리
- 시도 4에서 "tran:0 재전송해도 이미지가 바뀌어 그대로 떠 있음" → **set_eye 재전송은 오버레이를 '교체'한다**는 사실 확인.
- 그렇다면 **완전 투명 PNG로 교체**하면 → EMO가 PNG 알파를 인식할 경우 오버레이가 사라짐.
- 동시에 표시 단계도 투명 배경으로 바꿔서, **EMO가 알파를 인식하는지**를 한 번에 검증:
  - 로고 여백으로 눈이 비쳐 보이면 → 알파 인식 O → 제거도 성공
  - 여백이 검은색이면 → 알파 무시 → 다음은 "몇 초만 보이고 자동으로 사라지는" 방식으로 전환

### 관련 코드
- `restore_normal_eyes(ecm, ip)` — 현재는 `make_clear_image()`(완전 투명)를 push.
- `push_eye_image(ecm, ip, data, tran=100, wait_fetch)` — set_eye 재전송 헬퍼.
- 서버 종료(`httpd.shutdown()`)는 **제거 시도 후 마지막에** 실행해야 함 (재전송 시 서버가 살아 있어야 EMO가 받아감).

---

## 6. 참고한 GitHub Repo

### 6.1 `emo-connect-python` (Clark Scheff / 0xD34D, GPLv3) — **이 작업 디렉터리**
- 비공식 리버스 엔지니어링 BLE 라이브러리 (2022, 펌웨어 1.7.0 시대).
- **여기서 얻은 것**: BLE GATT 구조(ffe0/ffe1), JSON/바이너리 두 채널, 패킷 인코딩(`encodePayload`), 움직임 명령 바이트(`CommandUtil`), 상태/설정 요청 클래스.
- **한계**: 디스플레이용 request/config 클래스가 **없음** (EmoConstants에 `customize_req`/`eye_rsp` 문자열만 존재). → `set_eye` JSON은 우리가 직접 손으로 만들었다.

### 6.2 `emo-libre` 생태계 (waringer 등, 2026 활발) — **핵심 정보원**
- 최신 펌웨어 3.0.0 대상의 현대적 접근. 구성: Proxy(Go MITM 서버), Documentation, emo-proxy-docker, newFirmware, **esp32_image_parser**, WebUI.
- **여기서 얻은 결정적 정보**:
  - **`customize_req`/`set_eye`로 커스텀 눈 이미지 표시 가능** (Bluetooth/README.md). → 우리 이미지 목표의 근거.
  - 응답 코드 의미(1/0/3).
  - 화면 규격 320×240, 얼굴이 MJPEG/AVI(K210).
  - 움직임 바이너리 명령 포맷 대조 검증.
  - 정식 제어 경로로 **클라우드 프록시**(api.living.ai 트래픽을 자기 서버로 MITM)를 사용 = "Intents"(forward.json/right.json/dance.json...) + TTS 가로채기.

---

## 7. 아직 안 써봤지만 쓸 수 있는 라이브러리 기능

`src/emoconnect/ble/request/` 안에 이미 구현된, 우리가 아직 안 건드린 기능들.
(모두 JSON 채널이므로 fw 3.x 수락 여부는 `customize_req`처럼 **실행해 봐야** 확실하다.)

| 모듈 | 함수 | 기능 |
|------|------|------|
| `AnimationRequest` | `enterAnimationMode()` / `exitAnimationMode()` | 애니메이션 모드 진입/해제 |
| | `playEmoDance(n)` | 내장 댄스 재생 |
| `StateRequest` | `version()`, `network()`, `deviceid()`, `dancelist()`, `everything()` 등 | 상태 조회 (단, `sta_req` 계열은 fw3.x가 거부한 전례 있음) |
| `SettingRequest` | `setVolumeLow/Medium/High/Mute()` | 볼륨 조절 |
| | `setAutoUpdate(on)`, `setTemp(섭씨)`, `setLength(미터법)`, `setSchedule(on)` | 각종 설정 |
| | `enterSettingMode()` / `exitSettingMode()` | 설정 모드 |
| `CitySetRequest` | `setLocation(...)` | 도시/위치 설정 |
| `TimezoneSetRequest` | `setTimezone(...)` | 시간대 설정 |
| `WifiSetRequest` | `setWifi(ssid, pw)` | WiFi 설정 (emo_wifi.py가 사용) |
| `PowerRequest` | `powerOff()` | 전원 끄기 |
| `OtaRequest` | `setVersion(n)` | 펌웨어 버전 (OTA) |

바이너리(`CommandUtil`) 쪽 미사용 기능:
- `chargeLevelOnOff(on)`, `statusOnOff(on)` — 상태 표시 토글
- `enterApp(appId)` — 앱/게임 진입 (4=탐험/이동 게임)
- `debug*()` — 카메라/마이크/거리센서/IMU 등 **하드웨어 테스트 모드** (`cmd_debug`, 헤더 `0x55AA55AA33`)

`src/examples/`에 라이브러리 사용 예제도 있음:
- `movement_example.py`, `requests_example.py`, `charge_and_alerts_example.py`

---

## 8. 다음 단계 / 미해결 과제

1. **이미지 제거** (최우선): 투명 PNG 교체(시도 5) 테스트 → 실패 시 "몇 초 표시 후 자동 소멸" 방식.
2. **알파 인식 여부 확정**: 로고 여백으로 눈이 비치는지 확인.
3. (선택) `wifi_set`가 fw3.x에서 통과하는지 확인 (안 되면 폰 앱으로 대체).
4. (확장) emo-libre 클라우드 프록시 경로 — 더 복잡하지만 TTS/음성·인텐트까지 가능.
