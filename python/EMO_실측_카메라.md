# EMO 카메라(`photo_req`/`face_req`) 조사 — 2026-07-07

> 기존 `EMO_사용가능_전체정리.md` / `EMO_연구노트.md` / `EMO_명령어_레퍼런스.md`는 그대로 두고,
> 카메라/사진 관련 새 조사 내용을 이 문서에 별도로 기록한다.

## 배경
사용자 표정 인식을 위해 EMO 카메라 접근 가능 여부를 조사. 이 저장소(`0xD34D/emo-connect-python`)와
로컬 문서에는 `photo_req`/`face_req` 문자열만 있고 request/config 클래스가 없어(⚪ 미구현),
JSON을 직접 짜야 했다.

## 1차 시도 (실패) — op 값을 추측
아래 3개 후보를 순서대로 실측:
1. `{"data":{"server":{ip,port}}, "type":"photo_req"}` → **응답 옴**: `{"type":"photo_rsp","data":{"result":0}}` (실패)
2. `{"data":{"op":"photo","server":{...}}, "type":"photo_req"}` → 응답 없음
3. `{"data":{"op":"take_photo","server":{...}}, "type":"photo_req"}` → 응답 없음

→ `photo_req` 자체는 fw3.x가 인식(응답을 준다는 것 자체가 근거)하지만, 우리가 추측한 `op` 값이
전부 틀렸다는 게 확인됨.

## 2차: emo-libre 공식 문서에서 정확한 스펙 확인 (프록시 아님, BLE 스펙)
`0xD34D/emo-connect-python`(이 저장소) GitHub에는 프록시 언급이 전혀 없음(확인 완료 — README/토픽/코드
검색 모두 무관). 대신 별도 커뮤니티 프로젝트 **`emo-libre` (github.com/emo-libre)**의
`Documentation` 저장소 `Bluetooth/README.md`에 정확한 BLE JSON 스펙이 문서화돼 있었음:

```json
// 1) 진입
{"data":{"op":"in"},"type":"photo_req"}          → {"type":"photo_rsp","data":{"result":1}}

// 2) 서버로 동기화(업로드)
{"data":{"op":"syn","server":{"ip":"IP","port":PORT}},"type":"photo_req"}
                                                   → result:1(시작) 후 result:3(완료/오류)

// 3) 종료
{"data":{"op":"out"},"type":"photo_req"}          → {"type":"photo_rsp","data":{"result":1}}
```

`customize_req`(op:in → set_eye → op:out, 이미 작동 확인됨)와 **완전히 동일한 3단계 패턴**.
`set_eye`가 "EMO가 서버에서 다운로드"였다면, `photo_req`의 `syn`은 반대로
**"EMO가 서버로 사진을 업로드"**하는 방식으로 추정.

`face_req`도 같은 문서에 있음(얼굴 인식 프로필 관리용 — 실시간 표정 분석이 아니라 등록된 얼굴
이름 매핑 add/del/rename/rescan/syn):
```json
{"data":{"op":"in"},"type":"face_req"}
{"data":{"op":"syn"},"type":"face_req"}   → {"type":"face_rsp","data":{"faces":{"0":"이름"...},"result":1}}
{"data":{"name":"이름","op":"add"},"type":"face_req"}
{"data":{"id":"0","op":"del"},"type":"face_req"}
{"data":{"id":"0","name":"이름","op":"rename"},"type":"face_req"}
{"data":{"id":"1","op":"rescan"},"type":"face_req"}
{"data":{"op":"out"},"type":"face_req"}
```
→ 표정 인식은 `face_req`가 아니라, `photo_req`로 사진을 받아온 뒤 **노트북에서 직접** 표정/감정
분석 모델을 돌리는 방향이 맞다.

## 3차: 올바른 스펙으로 재실측 — 결과 대기 중
`emo_photo.py`를 위 정확한 시퀀스로 재작성함 (op:in → op:syn(서버 ip/port) → raw TCP 업로드 관찰
→ op:out). 결과는 실행 후 추가 기록 예정.

## 결론 (중간)
- **프록시(emo-libre 클라우드 MITM)는 필요 없음** — 이 저장소도, 카메라 기능도 순수 BLE+WiFi로 가능한
  스펙이 이미 문서화돼 있었음.
- 처음 실패는 스펙을 몰라서 `op` 값을 잘못 추측했기 때문이었을 뿐, fw3.x가 거부한 게 아니었음.
