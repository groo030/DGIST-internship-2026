# EMO 감정 표현 햅틱 장치 — 반려로봇의 감정을 열과 진동으로 전달하는 하드웨어 프로토타입

> 반려로봇 EMO가 화난 표정(Devil 애니메이션)을 지을 때 머리 위 장치가 **뜨거워지고 떨리도록** 만든 1인 인턴 프로젝트 (DGIST 하계 인턴, 2026.07)

[![데모 영상](https://img.youtube.com/vi/ljaNLHdMVIE/hqdefault.jpg)](https://www.youtube.com/watch?v=ljaNLHdMVIE)

---

## 1. 저장소 소개

| 항목 | 내용 |
|---|---|
| 기간 | 2026.07.06 ~ 2026.07.31 |
| 유형 | 인턴 (DGIST 하계 인턴) |
| 팀 구성 | 1명 — 이상준 (전 과정 단독 수행) |
| 내 역할 | 기획, PC 제어 소프트웨어, 펌웨어, 회로, 3D 하우징 설계·출력, 하드웨어 조립까지 전부 |
| 수상/성과 | 해당 없음 |
| 원본 저장소 | 해당 없음 (EMO 제어에는 오픈소스 라이브러리를 가져다 사용, 8장 참고) |

### 내가 담당한 범위
- EMO 제어와 햅틱 연동 PC 소프트웨어 — `python/`
  - 두 BLE 기기(EMO, 햅틱 장치)에 동시 명령: `python/haptic_dispatch.py`
  - 햅틱 장치 BLE 통신: `python/haptic_ble.py`
  - 문장 감정 분류 호출: `python/emotion_classifier.py`, `python/haptic_chat_harness.py`
- 햅틱 장치 펌웨어(C++) — `firmware/`
- 회로도 — `pcb/EMO.kicad_sch`
- 3D 하우징 설계(OpenSCAD)와 3D 프린터 출력 — `housing/`
- EMO 동작 실측 정리 — `python/EMO_연구노트.md`, `python/EMO_명령어_레퍼런스.md`

### 팀원이 담당한 범위
- 해당 없음 (1인 프로젝트)

---

## 2. 문제 정의

- **누가, 어떤 상황에서 겪는 문제인가**: 반려로봇 EMO와 대화하는 사용자. EMO는 화면 표정과 동작으로 감정을 표현함.
- **왜 문제로 정의했는가**: 감정 표현에 햅틱(열, 진동)을 함께 더해 사용자에게 다양한 경험을 제공하고자 함.
- **목표**: 사용자가 부정적인 말을 하면 EMO의 Devil 애니메이션과 열·진동 자극이 함께 나오는 시연 가능한 프로토타입 완성. (정량 목표는 따로 세우지 않았음)

---

## 3. 해결 방법

### 전체 구조
```
사용자 문장 입력
   └─ Claude API로 anger / neutral 분류 (python/emotion_classifier.py)
        └─ anger일 때 PC가 BLE로 두 기기에 동시에 명령 (python/haptic_dispatch.py)
             ├─ EMO            : Devil 애니메이션 재생
             └─ 햅틱 장치(XIAO nRF52840) : JSON 명령 수신 → 안전 검사 → Peltier 가열 + ERM 진동
```

- **햅틱 구성**: Peltier(열) 2채널, ERM 진동모터 2채널, 2S 리튬이온 배터리. 하우징은 직접 설계해 3D 프린터로 출력하고 EMO 머리 위에 탑재.
- **anger 시연 타이밍**: Peltier는 명령 즉시 가열을 시작해 20초간 유지하고, 10초 뒤 ERM 진동과 EMO Devil 애니메이션이 함께 시작됨. ("먼저 열로 반응하다가 뒤늦게 부르르 떨며 화내는" 연출)

### 핵심 해결 사례 (문제 → 방법 → 결과)

**① 부품 고장으로 마이크로컨트롤러 교체, 통신 방식 전환**
- 문제 상황: 처음 쓴 Arduino Nano ESP32가 고장 났고, 원인은 분석하지 못함.
- 선택한 방법과 이유: BLE를 내장한 Seeed XIAO nRF52840으로 교체. 이 보드는 WiFi가 없어 PC와의 통신을 WiFi(TCP)에서 BLE(Nordic UART Service)로 바꿈. EMO도 BLE라 PC 한 대가 두 기기에 동시에 연결하는 구조가 됨.
- 결과: 교체 후 BLE 기반 JSON 라인 명령으로 EMO와 햅틱 장치를 PC 한 대에서 동시에 제어.
- 관련 코드: [firmware/platformio.ini](firmware/platformio.ini), [firmware/src/NetworkTransport.cpp](firmware/src/NetworkTransport.cpp), [python/haptic_ble.py](python/haptic_ble.py)

**② PWM 신호가 나오지 않는 문제를 소프트웨어 PWM으로 해결**
- 문제 상황: ESP32의 하드웨어 PWM(LEDC) 레거시 API에서 실제 신호가 출력되지 않음을 실측으로 확인.
- 선택한 방법과 이유: `digitalWrite`와 `micros()`만 쓰는 소프트웨어 PWM을 직접 구현. 특정 보드 기능에 기대지 않아 XIAO 교체 후에도 그대로 사용 가능. Peltier와 ERM의 PWM 주파수를 서로 다르게 두어(100Hz / 80Hz) 두 파형의 피크가 계속 겹치는 상황을 피함.
- 결과: 보드 교체 이후에도 코드 수정 없이 동작.
- 관련 코드: [firmware/src/SoftPwm.cpp](firmware/src/SoftPwm.cpp), [firmware/include/Config.h](firmware/include/Config.h)

**③ 키워드 매칭 대신 LLM으로 부정적인 문장 판별**
- 문제 상황: "화나" 같은 감정 단어가 들어간 문장만 감지하면 "못생겼어"처럼 단어 없이 놀리는 말을 놓침.
- 선택한 방법과 이유: Claude API로 문장 내용 자체가 부정적(놀림, 비하, 위협 등)인지 anger / neutral 두 값으로 분류. 실제로 연결된 동작이 anger 하나뿐이라 라벨을 두 개로 제한.
- 결과: "멍청아", "못생겼어" 같은 말에는 Devil 명령이 작동하고 "고마워", "안녕"에는 반응하지 않음 (직접 시연으로 확인, 정량 평가는 하지 않음).
- 관련 코드: [python/emotion_classifier.py](python/emotion_classifier.py), [python/haptic_chat_harness.py](python/haptic_chat_harness.py)

**④ 과열·과부하를 막는 안전 계층**
- 문제 상황: PC 명령이 그대로 하드웨어에 닿으면 Peltier 과열이나 연결 끊김 시 무한 구동 위험이 있음.
- 선택한 방법과 이유: 모든 명령이 반드시 `SafetyGuard`를 거치도록 설계. Peltier duty 상한(150), 최대 구동 시간 30초 워치독, 배터리 저전압 시 출력 제한, ERM과 Peltier가 동시에 높은 출력을 무기한 유지하는 조합 차단.
- 결과: 위 규칙이 PC 쪽 명령과 무관하게 펌웨어 코드에서 강제됨.
- 관련 코드: [firmware/src/SafetyGuard.cpp](firmware/src/SafetyGuard.cpp), [firmware/include/Config.h](firmware/include/Config.h)

### 핵심 코드
- [python/haptic_dispatch.py](python/haptic_dispatch.py) — anger 시 EMO 애니메이션과 햅틱 명령을 동시에 시간차로 발사
- [firmware/src/SafetyGuard.cpp](firmware/src/SafetyGuard.cpp) — 모든 명령을 안전 규칙 안으로 제한
- [firmware/src/WavePlayer.cpp](firmware/src/WavePlayer.cpp) — 업로드된 ERM 진동 파형을 펌웨어 타이머로 재생 (BLE 지연과 무관하게 매끄러움)
- [python/haptic_audio_erm.py](python/haptic_audio_erm.py) — 오디오의 진폭 엔벨로프를 ERM 진동 파형으로 변환
- [housing/](housing/) — OpenSCAD 하우징 설계와 STL/3MF 출력 파일

---

## 4. 성능 / 성과

정량 평가는 하지 않았고, 다음을 시연으로 확인함.

- 부정적인 문장에 EMO Devil 애니메이션 + Peltier 가열 + ERM 진동이 시간차로 함께 동작
- 긍정/중립 문장에는 반응하지 않음
- 직접 설계·출력한 하우징과 햅틱 모듈을 EMO 머리 위에 탑재한 하드웨어 프로토타입 완성

---

## 5. 기술 스택

| 분류 | 사용 기술 |
|---|---|
| Language | Python, C++ (Arduino framework), OpenSCAD |
| Model / Framework | Claude API (문장 감정 분류), PlatformIO, asyncio |
| Communication | BLE (bleak, Nordic UART Service), JSON 라인 프로토콜 |
| Hardware / Device | Seeed XIAO nRF52840, Peltier, ERM 진동모터, DRV8871 / DRV8833 모터 드라이버, 2S 리튬이온 배터리, EMO 반려로봇 |
| Tools | KiCad, OpenSCAD, 3D 프린터 |

---

## 6. 실행 방법

```bash
git clone https://github.com/groo030/DGIST-internship-2026
cd DGIST-internship-2026

# EMO 제어 라이브러리 설치 (이 저장소에 포함되어 있지 않음)
git clone https://github.com/0xD34D/emo-connect-python
pip install emo-connect-python/src/
pip install -r python/requirements-haptic.txt

# 펌웨어 업로드 (PlatformIO)
cd firmware && pio run -t upload && cd ..

# 감정 분류 + 동시 발사 데모
cd python
cp .env.example .env   # ANTHROPIC_API_KEY 입력
python3 haptic_chat_harness.py
```

- 필요한 환경 변수: `ANTHROPIC_API_KEY` (`python/.env.example` 참고, 실제 키는 올리지 않음)
- BLE 사용 시 공식 EMO 앱을 종료하고, macOS에서는 Terminal.app에 블루투스 권한이 필요함.
- 하드웨어: Seeed XIAO nRF52840, Peltier, ERM과 드라이버 보드가 필요하며 회로는 `pcb/EMO.kicad_sch` 참고.

---

## 7. 한계와 개선 방향

- 한계: 처음 해보는 하드웨어 영역이라 LRA, Fan 등 다양한 자극을 시도하지 못함. Arduino Nano ESP32가 고장 난 원인도 분석하지 못함. 감정 분류와 햅틱 효과는 정량 평가 없이 시연으로만 확인함.
- 개선 방향: LRA(순간 진동), Fan(바람) 등 자극 종류 확대. 이는 이후 학교 고급캡스톤디자인에서 영상 4D 효과 생성과 햅틱 인터페이스로 이어서 진행 중.

---

## 8. 라이선스 및 데이터 출처

- 라이선스: 별도 라이선스 파일 없음. 아래 외부 오픈소스는 각자의 라이선스를 따름.
- 이 저장소에 포함하지 않은 외부 자료:
  - [0xD34D/emo-connect-python](https://github.com/0xD34D/emo-connect-python) (GPL-3.0) — EMO BLE 제어 라이브러리 `emoconnect`. `python/`의 스크립트가 이 라이브러리를 가져다 씀.
  - [emo-libre/Documentation](https://github.com/emo-libre/Documentation) (BSD-3-Clause) — EMO 프로토콜·하드웨어 분석 문서. 참고만 함.
- 펌웨어 의존성: [ArduinoJson](https://github.com/bblanchon/ArduinoJson), [Seeed platform-seeedboards](https://github.com/Seeed-Studio/platform-seeedboards)

---

## Contact
- 이상준 / GitHub: [groo030](https://github.com/groo030)
