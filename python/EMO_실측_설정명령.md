# EMO 설정 명령(`setting_req`) 실측 결과 — 2026-07-07

> 기존 `EMO_사용가능_전체정리.md` / `EMO_연구노트.md` / `EMO_명령어_레퍼런스.md`는 그대로 두고,
> 새로 확인된 실측 결과만 이 문서에 별도로 기록한다.

## 음소거 (`SettingRequest.setVolumeMute()`)

- 전송: BLE로 `setVolumeMute()` 전송하는 스크립트(`emo_volume.py`, 삭제됨)
- 결과: **연결 안 끊김** (fw3.x가 `sta_req`처럼 대놓고 거부하지는 않음)
- 그러나 이후 **EMO를 쓰다듬으면 반응음이 그대로 남** → 실제 음소거 효과 없음
- **결론: BLE `setting_req`로는 음소거 불가능 확인 → 스크립트 삭제.**
  대신 **폰 공식 앱에서 직접 음소거 설정 → 정상 동작 확인됨** (사용자 확인, 2026-07-07).

### 판단
`setting_req`(볼륨/온도/거리/자동업데이트 등 설정 계열)는 fw3.x가 **수락은 하되 조용히 무시**하는 것으로 보인다. 이는 다음 두 상태와 다른 제3의 패턴이다:
- `sta_req` — 거부(연결 끊음)
- `customize_req` — 수락 + 실제 동작(이미지 표시)

`setting_req`는 수락 + 무동작. 같은 채널(`setting_req`)을 쓰는 나머지 설정 함수(`setTemp`, `setLength`, `setAutoUpdate`, `setSchedule`, `setScheduleSound`)도 같은 이유로 효과 없을 가능성이 높다 (아직 개별 실측은 안 함).

### 대안 (확인됨)
BLE `setting_req`가 안 먹히므로 **폰 공식 앱에서 볼륨/설정 변경**이 정식 경로. 앱에서 설정 후 정상 적용됨을 확인함.

## 다음 확인 대상
- [ ] `setTemp`, `setLength`, `setAutoUpdate`, `setSchedule`, `setScheduleSound` 개별 실측 (같은 무효과 패턴인지)

---

## (추가) 후진 명령 `CommandUtil.back()` 실측 — 2026-07-07

- 채널: 바이너리 `0xDD 0xCC` (움직임 계열, `setting_req`와 무관)
- 기존 상태(레퍼런스 문서): 🟡 미확인 — "정의는 됨, 동작 미확인"
- 실측: `emo_move.py drive` 모드에서 `S`(뒤) 입력 시 아무 반응 없음 → **동작 안 함 확인**
- 조치: `drive()` 모드의 `s` 키를 `CommandUtil.back()` 직접 호출에서, 데모 모드와 동일한
  `turn_around()`(제자리 180° 회전 = `right()` 짧게)로 교체함 (`emo_move.py`).
  이제 데모/조종 모드 둘 다 "뒤로"는 실제로는 뒤돌기로 동작한다.

---

## (추가) 터치 센서 디버그 모드 `CommandUtil.debugTouchSensorsTest()` 실측 — 2026-07-07

- 채널: 하드웨어 디버그 (헤더 `0x55 0xAA 0x55 0xAA 0x33`), `emo_touch_debug.py`(신규 실험 스크립트)로 테스트
- 절차: `debugEnterTestMode()` → `debugTouchSensorsTest()` 전송 후 EMO 화면과 BLE 알림을 동시에 관찰
- **결과**:
  - EMO 화면에 **3자리 숫자 3개**가 실시간으로 표시됨 (터치 센서 3개 채널로 추정)
  - 평소엔 **900번대의 거의 일정한 기준값** 근처에서 미세하게 흔들림(노이즈) — 전형적인
    정전용량(capacitive) 원시 센서 값의 특징
  - 머리 위를 만지면 값이 바뀜 → **원시 센서 값 자체는 실제로 존재하고 살아있음**
  - 그러나 **관찰 20초 동안 BLE로는 새 알림이 단 하나도 안 옴** (raw dump 콜백으로 확인)
    → 이 값은 **EMO 화면에만 렌더링되는 로컬 진단 표시**이고 BLE로는 전송되지 않음
- **결론**: 터치 센서 원시 값은 존재하지만, 이 디버그 채널로는 **코드(BLE)로 읽어올 수 없음**
  확인됨. 읽으려면 화면을 카메라로 찍어 OCR 하거나, 기기를 분해해 센서 IC에 직접 접근하는
  수준의 하드웨어 접근이 필요 — 이 프로젝트(BLE 소프트웨어) 범위 밖.
- 참고: 진입 직후 `dd cc 00 00 00 09 00...` 형태의 알림이 한 번 옴(=`debugEnterTestMode()`
  응답으로 추정). `CommandParser`가 인식 못 하는 패턴(`payload[0:2]`가 `[0,0]`/`[2,0]`/`[3,5]`
  중 어디에도 안 맞음)이라 라이브러리 기본 파서로는 "미상"으로 버려짐.

---

## (추가) 상태 이벤트(`StatusAlert`) PC 수신 실측 — 2026-07-13

- 질문: `EMO_명령어_레퍼런스.md` 2.3절의 `StatusAlert` 상태 이벤트 코드를 PC(노트북)로 실제로
  받을 수 있는지 확인.
- 조치: `emo_move.py`에 `commandRx()` 콜백을 추가하고, 연결 직후 `ecm.setCommandCallback(commandRx)`를
  등록해 EMO가 보내는 `0xDDCC` 이벤트를 화면에 출력하도록 함 (원본 이동 로직은 그대로, 관측 코드만 추가).
- **결과**: 실행 중 아래가 정상 출력됨 → **PC 수신 확인됨**.
  ```
  📡 [상태 이벤트 수신] ChargeStatus(charge_level=100)
  📡 [상태 이벤트 수신] StatusAlert(status=<Status.STAYING: 230>)
  ```
- **결론**: `statusOnOff(True)`/`chargeLevelOnOff(True)` 전송 후 EMO가 보내는 상태 이벤트는
  `EmoConnectManager._handle_rx` → `CommandParser.parse()` → `setCommandCallback`으로 등록한 콜백
  경로를 통해 PC에서 정상적으로 받을 수 있다. BLE notify 파이프라인 자체는 문제없음.

## (추가) 이동 명령(forward/left/right/turn_around) 재검증 — 2026-07-13

- 조건: EMO를 충전대(스케이트보드)에서 완전히 내려 바닥에 둔 상태.
- 절차: `clear → enterApp(4) → startGame → resetting → statusOnOff(True) → chargeLevelOnOff(True)` 진입 후
  `forward()/left()/right()/turn_around()` 데모 실행 (`emo_move.py` 기본 실행).
- **결과**: 스크립트는 "✅ 데모 완료 — BLE 이동 명령이 정상 동작합니다"를 출력했지만
  (이 판정은 "BLE 연결이 안 끊겼다"만 확인하는 것), **실제로는 소리·진동·바퀴 회전 시도 등
  물리적 반응이 전혀 없었음** (완전 정지 상태 유지) — 사용자 육안 확인.
- **추가 관찰**: `enterApp(4)`/`startGame()` 전송 이후 `[3,5]` 헤더의 `HuntResponse`
  (탐험/이동 게임 진입 확인 응답)가 **한 번도 수신되지 않음** → "이동 게임" 모드 진입 자체가
  조용히 실패했을 가능성.
- **판단**:
  - `EMO_명령어_레퍼런스.md`/`EMO_연구노트.md`의 기존 "움직임 ✅ 작동" 판정은 연결 유지 여부만으로
    내린 false positive였을 가능성이 있음 (이동 명령은 fire-and-forget이라 원래 ack가 없어서,
    콜백을 붙여 로봇의 실제 반응을 직접 관찰한 것은 이번이 처음).
  - `EMO_연구노트.md` 6.2절의 emo-libre 조사에 따르면 최신 펌웨어(3.0.0)의 정식 이동 제어 경로는
    **클라우드 프록시 Intent**(`api.living.ai` MITM, `forward.json` 등) 방식이라는 단서가 있음.
    이 레포의 `0xDDCC` 바이너리 명령은 **펌웨어 1.7.0 시대에 리버스 엔지니어링된 로컬 경로**라서,
    지금 로봇 펌웨어에서는 패킷이 파싱되어 연결은 안 끊기지만 실제 모터 제어에는 더 이상
    연결되어 있지 않을 수 있다는 가설.
- **다음 확인 대상 (미착수, 사용자가 이 경로로 진행 선택함)**: emo-libre 방식대로 클라우드
  프록시를 세워 `api.living.ai` 트래픽을 MITM하고 Intent(`forward.json` 등)로 직접 이동을
  시도 — 이게 되면 위 가설이 맞다는 뜻.
- **코드 변경**: `emo_move.py`에 `commandRx()` 콜백 추가 + `connect()`에서
  `ecm.setCommandCallback(commandRx)` 등록 (관측용 추가 코드, 기존 이동 로직 변경 없음).
