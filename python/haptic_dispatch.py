"""anger 감지 시 EMO BLE(devil 애니메이션) + Arduino Serial(진동+열)을 동시에 발사하는 디스패치 로직.

기존 BLE 제어 코드(emo_devil.py 등)는 건드리지 않고, 같은 라이브러리 호출을 재사용해
새 모듈로만 작성함.
"""
from __future__ import annotations

import asyncio

from emoconnect.ble.config.AnimationConfig import AnimationConfig, Op
from emoconnect.ble.request import AnimationRequest

# anger 감정에 대한 채널별 자극 파라미터.
# 문헌 방향은 "낮은 valence → 냉각"이지만,
# 실측 반응을 직접 보기 위해 가열(direction=+1) 방향으로 테스트하기로 결정함 — 문헌과
# 다른 선택이므로 MENTOR-REVIEW 시 이 방향 선택 자체도 같이 재확인 필요.
# 연출: Peltier는 명령 즉시 발사해 전체 시나리오 내내(ANGER_TOTAL_DURATION_MS) 뜨거워진
# 상태를 유지하고, ERM 진동과 EMO devil 애니메이션은 ANGER_ERM_ANIMATION_DELAY_S만큼
# 늦게 함께 시작한다 — "먼저 열로 반응하다가 뒤늦게 부르르 떨며 화낸다"는 의도적 타이밍.
ANGER_TOTAL_DURATION_MS = 20000
ANGER_ERM_ANIMATION_DELAY_S = 10.0
ANGER_PELTIER_DUTY = 110
ANGER_PELTIER_DIRECTION = 1  # 가열 방향 (실측 테스트를 위해 문헌 권장 냉각 대신 선택)
ANGER_ERM_DUTY = 255
ANGER_ERM_DURATION_MS = 1500

# 반복 트리거 시 devil 애니메이션 모드를 몇 초 뒤에 종료할지 — dispatch_anger() 호출 시점
# (t=0) 기준. 애니메이션 자체가 ANGER_ERM_ANIMATION_DELAY_S(10초) 뒤에 시작하므로, 전체
# 시나리오 길이(ANGER_TOTAL_DURATION_MS)에 맞춰 20초로 잡아 애니메이션이 10초간 재생되게 함.
# MENTOR-REVIEW: 실사용 느낌 보고 조정.
ANIMATION_EXIT_DELAY_S = 20.0


async def dispatch_anger(ecm, haptic, *, enter_animation_mode: bool = True) -> None:
    """BLE devil 애니메이션 재생과 햅틱 명령을 발사한다.

    ecm: EmoConnectManager (이미 connectToEmo()가 완료된 상태여야 함) — None이면 EMO 쪽은
        건너뛰고 haptic 명령만 보낸다(EMO 연결 실패 시에도 XIAO 단독 테스트/운영이 가능하도록).
    haptic: HapticBleClient (이미 open()이 완료된 상태여야 함).

    anger 시나리오는 Peltier 두 모듈 다 가열 방향으로 유지(펌웨어가 모듈별 독립 제어를
    지원하게 됐어도, "화남 = 둘 다 뜨거워짐"이라는 기존 표현은 그대로 둠).

    Peltier는 호출 즉시 발사해 ANGER_TOTAL_DURATION_MS(20초) 동안 유지하고, ERM 진동과
    EMO devil 애니메이션은 ANGER_ERM_ANIMATION_DELAY_S(10초) 뒤에 함께 시작한다.

    프로토콜상 한 JSON 명령에 peltier1/peltier2/erm이 항상 같이 들어가야 해서(생략 불가),
    10초 시점의 ERM 명령에도 Peltier 필드를 같이 채워 보낸다 — 방향/duty가 그대로라
    PeltierDriver가 dead-time 없이 이어서 구동하고, duration_ms만 "남은 시간"으로
    다시 계산해 최종적으로 ANGER_TOTAL_DURATION_MS 시점에 맞춰 꺼지게 한다.

    EmoConnectManager.sendCommand()는 fire-and-forget(GATT write, 락 없음)이라
    haptic 쪽 전송과 asyncio.gather로 동시 실행해도 안전함.
    """

    async def _play_devil() -> None:
        if ecm is None:
            return
        await asyncio.sleep(ANGER_ERM_ANIMATION_DELAY_S)
        if enter_animation_mode:
            await ecm.sendCommand(AnimationRequest.enterAnimationMode())
        await ecm.sendCommand(AnimationConfig(op=Op.PLAY, name="devil").getRequest())

    async def _send_peltier_immediate() -> None:
        await asyncio.to_thread(
            haptic.send_haptic_command,
            # 두 Peltier 모듈 다 동일한 값 — anger는 "둘 다 가열"로 유지.
            peltier1_duty=ANGER_PELTIER_DUTY,
            peltier1_direction=ANGER_PELTIER_DIRECTION,
            peltier1_duration_ms=ANGER_TOTAL_DURATION_MS,
            peltier2_duty=ANGER_PELTIER_DUTY,
            peltier2_direction=ANGER_PELTIER_DIRECTION,
            peltier2_duration_ms=ANGER_TOTAL_DURATION_MS,
            erm_duty=0,  # Off — 아직 시작 안 함
            erm_duration_ms=0,
        )

    async def _send_erm_delayed() -> None:
        await asyncio.sleep(ANGER_ERM_ANIMATION_DELAY_S)
        remaining_peltier_ms = ANGER_TOTAL_DURATION_MS - int(ANGER_ERM_ANIMATION_DELAY_S * 1000)
        await asyncio.to_thread(
            haptic.send_haptic_command,
            peltier1_duty=ANGER_PELTIER_DUTY,
            peltier1_direction=ANGER_PELTIER_DIRECTION,
            peltier1_duration_ms=remaining_peltier_ms,
            peltier2_duty=ANGER_PELTIER_DUTY,
            peltier2_direction=ANGER_PELTIER_DIRECTION,
            peltier2_duration_ms=remaining_peltier_ms,
            erm_duty=ANGER_ERM_DUTY,
            erm_duration_ms=ANGER_ERM_DURATION_MS,
        )

    await asyncio.gather(_play_devil(), _send_peltier_immediate(), _send_erm_delayed())


async def exit_animation_mode(ecm) -> None:
    """devil 애니메이션 모드를 종료한다. ecm이 None(EMO 미연결)이면 아무 것도 안 함.

    MENTOR-REVIEW: 반복 트리거 시 이걸 언제 호출할지(매번 즉시? 대화가 끝날 때? 일정 시간 후?)
    정책이 미확정 상태 — 일부러 dispatch_anger()에 넣지 않고 별도 함수로 노출해서
    호출 시점 결정을 이 함수를 쓰는 쪽(챗 하니스/실제 LLM 연동부)에 맡김.
    """
    if ecm is None:
        return
    await ecm.sendCommand(AnimationRequest.exitAnimationMode())
