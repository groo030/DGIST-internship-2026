"""
EMO anim_req 이름 스윕 (BLE) — 2026-07-23

emo_eye.py 때처럼 "일단 여러 후보를 다 던져보고 반응을 관찰"하는 방식으로,
anim_req(op:play, name:...)에 여러 후보 이름을 순서대로 보내며 하나씩 관찰한다.

사용자가 확보한 전체 애니메이션 이름 목록(카테고리별)을 그대로 담았다.
"angry"는 Emotions 카테고리 맨 앞에 있다.

사용법
    python3 emo_anim_sweep.py                     # 전체 124개 순서대로 시도
    python3 emo_anim_sweep.py --category emotions  # Emotions만 (angry 포함, 11개)
    python3 emo_anim_sweep.py --category emotions,cool  # 여러 카테고리 조합
    python3 emo_anim_sweep.py --names angry,devil,demon  # 원하는 이름만 직접 지정
    python3 emo_anim_sweep.py --wait 2             # 각 이름 사이 대기 시간(초) 줄이기

각 이름을 보낸 뒤 --wait초 동안 대기하니, 그 사이 EMO 화면/모터 반응을
직접 관찰하고 어떤 이름에서 반응이 있었는지(몇 번째인지) 메모해두면 된다.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from emoconnect.ble.config.AnimationConfig import AnimationConfig, Op
from emoconnect.ble.request import AnimationRequest
from emo_move import connect, _is_connected

CATEGORIES = {
    "emotions": [
        "angry", "excited", "happy", "upset", "sad", "scared", "startled",
        "what", "kiss", "hug", "hi",
    ],
    "daily": [
        "sleep", "wakeup", "boxing", "toothbrushing", "toast", "newspaper",
        "keyboard", "cook", "hamburger", "cleaning", "tea", "bartending",
        "mining", "jump_up", "parkour", "pinball", "aircraft_wars", "drone",
        "juggling", "rubiks_cube", "paint", "weaving", "noodle", "tv",
    ],
    "animals": [
        "cuckoo", "cicada", "cow", "elephant", "horse", "dog", "wolf", "fog",
        "chicken", "cat", "sheep", "snake", "tiger", "duck", "pig", "fox",
    ],
    "camping": ["tent", "fishing", "campfire", "barbecue"],
    "weapons": ["knife", "slingshot", "water_gun", "boomerang"],
    "music": [
        "piano", "trumpet", "tambourine", "drum_kit", "singing", "dj",
        "glow_sticks", "radio",
    ],
    "holidays": [
        "easter", "april_fools", "santa", "christmas", "new_year",
        "spring_festival", "fathers_day", "mothers_day", "valentines",
        "childrens_day", "thanksgiving", "moon_day", "halloween", "cyclops",
        "birthday",
    ],
    "games": [
        "rock", "scissors", "paper", "dice_1", "dice_2", "dice_3", "dice_4",
        "dice_5", "dice_6", "fireworks", "game",
    ],
    "cool": [
        "demon", "devil", "laser_eyes", "hands_up", "shot", "zombie",
        "photo", "alarm_anim", "light",
    ],
    "weather": ["cloudy", "sunny", "snowy", "rainy"],
    "zodiac": [
        "aquarius", "aries", "cancer", "capricorn", "gemini", "leo", "libra",
        "pisces", "sagittarius", "scorpio", "taurus", "virgo",
    ],
    "v3.1.0+": ["shower", "poop", "meditation", "banana", "hypnosis", "fried_chicken"],
}

DEFAULT_CANDIDATES = [name for names in CATEGORIES.values() for name in names]


def on_command(ecm, command):
    raw = bytes(getattr(ecm, "_packet", b"") or b"")
    print(f"  📡 [상태 이벤트 수신] {command}  raw={raw.hex()}")


async def send_and_capture(ecm, packet: bytes, wait: float = 1.5):
    ecm._resonse = None
    await ecm.sendCommand(packet)
    waited = 0.0
    while waited < wait:
        await asyncio.sleep(0.2)
        waited += 0.2
        if getattr(ecm, "_resonse", None) is not None:
            print(f"  ↩︎ EMO 응답: {ecm._resonse}")
            return ecm._resonse
    print("  ↩︎ EMO 응답 없음")
    return None


def playAnimationByName(name: str) -> bytes:
    return AnimationConfig(op=Op.PLAY, name=name).getRequest()


async def main():
    parser = argparse.ArgumentParser(description="EMO anim_req 이름 스윕")
    parser.add_argument(
        "--names", default=None,
        help="쉼표로 구분한 후보 이름 목록 (지정하면 --category 무시)",
    )
    parser.add_argument(
        "--category", default=None,
        help=f"쉼표로 구분한 카테고리 목록 (선택지: {', '.join(CATEGORIES)})",
    )
    parser.add_argument(
        "--wait", type=float, default=3.0,
        help="각 이름 재생 후 관찰 대기 시간(초, 기본 3)",
    )
    args = parser.parse_args()

    if args.names:
        candidates = args.names.split(",")
    elif args.category:
        candidates = []
        for cat in args.category.split(","):
            cat = cat.strip()
            if cat not in CATEGORIES:
                print(f"❌ 알 수 없는 카테고리: {cat!r} (선택지: {', '.join(CATEGORIES)})")
                return
            candidates.extend(CATEGORIES[cat])
    else:
        candidates = DEFAULT_CANDIDATES

    print(f"[준비] 시도할 이름 {len(candidates)}개")

    ecm = await connect()
    if ecm is None:
        return

    ecm.setCommandCallback(lambda command: on_command(ecm, command))

    try:
        print("\n[진입] anim_req(op:in) — 애니메이션 모드 진입")
        await send_and_capture(ecm, AnimationRequest.enterAnimationMode())
        if not _is_connected(ecm):
            print("❌ EMO가 연결을 끊었습니다 => anim_req(op:in) 자체가 거부됨.")
            return

        for i, name in enumerate(candidates, 1):
            if not _is_connected(ecm):
                print("⚠️  중간에 EMO가 연결을 끊었습니다. 스윕을 중단합니다.")
                break
            print(f"\n[{i}/{len(candidates)}] 이름 시도: {name!r}")
            await send_and_capture(ecm, playAnimationByName(name), wait=1.5)
            print(f"  → {args.wait}초간 관찰하세요 (반응 있으면 메모!)")
            await asyncio.sleep(args.wait)

    finally:
        try:
            if _is_connected(ecm):
                print("\n[정리] anim_req(op:out) — 애니메이션 모드 종료")
                await send_and_capture(ecm, AnimationRequest.exitAnimationMode())
                await ecm.disconnect()
                print("연결을 종료했습니다.")
            else:
                print("(EMO가 이미 연결을 끊은 상태입니다.)")
        except Exception as e:
            print(f"(종료 중 무시된 예외: {e})")


if __name__ == "__main__":
    asyncio.run(main())
