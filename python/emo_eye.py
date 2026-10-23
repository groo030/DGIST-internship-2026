"""
EMO 눈 디스플레이에 커스텀 이미지/텍스트 띄우기 (BLE) — 2026-06-18

EMO 화면(눈)에 DGIST 글자나 로고 이미지를 띄우려는 시도.

⚠️ 중요한 전제 / 알려진 위험
  - 디스플레이 명령(customize_req/set_eye)은 'JSON 채널'(헤더 0xBB 0xAA)을 쓴다.
    그런데 펌웨어 3.x는 같은 JSON 채널의 sta_req를 받으면 연결을 끊어버린다.
    => 디스플레이 명령도 거부될 가능성이 높다. 이 스크립트는 그걸 '실제로' 확인한다.
  - 이동(w/a/d/s)이 되는 건 별도의 바이너리 채널(0xDD 0xCC)이라서다.

동작 (2단계)
  [1단계] customize_req {"op":"in"} 전송 → EMO가 연결을 끊는지 확인.
          끊으면 = fw3.x가 BLE 디스플레이를 막은 것 → 클라우드 프록시 방식 필요.
  [2단계] (1단계 통과 시) 로컬 HTTP 서버(포트 9090)를 띄우고 set_eye로
          이미지를 EMO에 푸시. EMO가 WiFi로 이 서버에서 이미지를 내려받아 표시.

사용법
  python3 emo_eye.py              # 기본: "DGIST" 텍스트 이미지 생성 후 표시
  python3 emo_eye.py text HELLO   # 원하는 글자 이미지 생성 후 표시
  python3 emo_eye.py volcano      # 화산 폭발 그래픽(절차적으로 그림) 생성 후 표시
  python3 emo_eye.py logo.png     # 직접 만든 PNG 파일을 표시
  python3 emo_eye.py --noclear    # (실험) 정리 단계 없이 표시 후 바로 연결 끊기
                                   #   → 연결 끊김만으로 원래 눈으로 돌아오는지 확인용

추가 실행 조건 (이동 스크립트의 조건에 더해)
  - EMO와 노트북이 '같은 WiFi 네트워크(2.4GHz)'에 있어야 한다.
    (EMO가 노트북의 HTTP 서버에 접속해 이미지를 내려받기 때문)
  - 방화벽이 포트 9090 인바운드를 막지 않아야 한다.
"""
import asyncio
import json
import os
import socket
import socketserver
import sys
import threading

# 저장소의 src 폴더를 import 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from emoconnect.EmoConnectManager import EmoConnectManager
# 연결 로직은 emo_move.py 것을 재사용 (타깃 ffe0 스캔 + 연결)
from emo_move import connect, _is_connected

EMO_HTTP_PORT = 9090
IMAGE_SIZE = (320, 240)  # EMO 화면 크기 (가로, 세로) = 320×240 가로형.
# 주: 단색 빨강이 240×320으로 꽉 찬 건 픽셀 수(76800)가 같았기 때문이고(균일색은 폭이
# 틀려도 똑같이 보임), 글자/로고가 가로로 ~3번 반복돼 깨진 건 실제 폭이 320이기 때문.


# ── JSON 패킷 인코딩 (라이브러리 ByteUtil.encodePayload 와 동일) ──────────────
def encode_json(obj: dict) -> bytes:
    """파이썬 dict를 EMO JSON 패킷(0xBB 0xAA + 길이 + UTF-8 본문)으로 만든다."""
    body = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    return bytes([0xBB, 0xAA]) + len(body).to_bytes(2, "little") + body


# ── 로컬 IP 알아내기 ────────────────────────────────────────────────────────
def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


# ── EMO 화면 규격에 맞게 이미지 정규화 (320×240 PNG) ─────────────────────────
# 실험으로 확정된 사실:
#   - EMO는 PNG만 받아들인다(JPEG를 보내면 헤더 검사에서 거부 → 얼굴 안 바뀜).
#   - EMO는 PIL PNG를 정상 디코딩한다(단색 빨강이 깨끗하게 꽉 찼음).
#   - 화면 실제 가로폭은 320 (240으로 보내면 구조 있는 그림이 ~3번 반복돼 깨짐).
# 해결:
#   (1) 알파 제거(검은 배경에 합성) → RGB,
#   (2) 비율 유지하며 320×240 안에 레터박스(여백은 검정),
#   (3) PNG로 인코딩.
def normalize_for_emo(png_bytes: bytes) -> bytes:
    """임의의 이미지 바이트를 EMO 화면용 320×240 RGBA PNG로 변환해 반환.
    알파(투명)를 '보존'한다. EMO가 알파를 인식한다면 여백/투명 영역으로 뒤의
    눈이 비쳐 보이게 되고, 완전 투명 이미지로 교체하면 오버레이를 지울 수 있다."""
    from io import BytesIO

    from PIL import Image

    src = Image.open(BytesIO(png_bytes)).convert("RGBA")

    # 비율 유지하며 IMAGE_SIZE 안에 들어가도록 축소 후 가운데 배치(레터박스).
    # 여백은 검정이 아니라 '완전 투명'으로 둔다 → 뒤의 눈이 보이도록.
    canvas = Image.new("RGBA", IMAGE_SIZE, (0, 0, 0, 0))
    fitted = src.copy()
    fitted.thumbnail(IMAGE_SIZE, Image.LANCZOS)
    x = (IMAGE_SIZE[0] - fitted.width) // 2
    y = (IMAGE_SIZE[1] - fitted.height) // 2
    canvas.paste(fitted, (x, y), fitted)

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def make_clear_image() -> bytes:
    """완전 투명한 320×240 RGBA PNG. 오버레이 제거용(투명 이미지로 교체)."""
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGBA", IMAGE_SIZE, (0, 0, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── 진단용 단색 이미지 ──────────────────────────────────────────────────────
# 화면 폭/색 형식 점검용. normalize_for_emo()가 JPEG로 재인코딩하므로 여기선
# 단순히 단색 캔버스를 만들어 넘긴다.
def make_solid_image(color_name: str) -> bytes:
    from io import BytesIO

    from PIL import Image

    colors = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "white": (255, 255, 255),
        "yellow": (255, 255, 0),
        "black": (0, 0, 0),
    }
    rgb = colors.get(color_name, (255, 0, 0))
    img = Image.new("RGB", IMAGE_SIZE, rgb)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── 화산 폭발 그래픽 (절차적 생성) ───────────────────────────────────────────
def make_volcano_image() -> bytes:
    """산/분화구/용암/연기를 도형으로 그려 화산 폭발 장면을 만든다.
    실제 사진이 아니라 PIL 도형(삼각형/타원/선)으로 조합한 단순 그래픽이다."""
    import random
    from io import BytesIO

    from PIL import Image, ImageDraw

    W, H = IMAGE_SIZE  # 320, 240
    img = Image.new("RGBA", (W, H), (10, 8, 25, 255))  # 어두운 밤하늘 배경
    draw = ImageDraw.Draw(img)

    peak = (W // 2, 110)

    # 산 (짙은 갈색 삼각형)
    draw.polygon([peak, (20, H), (W - 20, H)], fill=(60, 45, 40, 255))

    # 분화구 (정상 부근을 어둡게 파낸 삼각형)
    draw.polygon(
        [peak, (peak[0] - 18, peak[1] + 14), (peak[0] + 18, peak[1] + 14)],
        fill=(30, 20, 18, 255),
    )

    # 용암 흐름 (산 옆면을 타고 흐르는 주황 선)
    draw.line([peak, (peak[0] - 25, H - 10)], fill=(255, 100, 0, 255), width=4)
    draw.line([peak, (peak[0] + 20, H - 10)], fill=(255, 120, 0, 255), width=3)

    # 연기 (불기둥/용암 방울보다 먼저 그려서 가려지지 않게)
    for i in range(5):
        cx = peak[0] + random.randint(-25, 25)
        cy = peak[1] - 55 - i * 14
        r = 16 + i * 5
        gray = 55 + i * 18
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(gray, gray, gray, 190))

    # 중심 불기둥
    draw.polygon(
        [
            (peak[0] - 9, peak[1]),
            (peak[0] + 9, peak[1]),
            (peak[0] + 4, peak[1] - 55),
            (peak[0] - 4, peak[1] - 55),
        ],
        fill=(255, 90, 0, 255),
    )

    # 튀는 용암 방울
    for _ in range(14):
        rx = peak[0] + random.randint(-45, 45)
        ry = peak[1] - random.randint(5, 70)
        r = random.randint(2, 5)
        draw.ellipse(
            [rx - r, ry - r, rx + r, ry + r],
            fill=(255, random.randint(90, 190), 0, 255),
        )

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── 텍스트 → PNG 이미지 ─────────────────────────────────────────────────────
def make_text_image(text: str) -> bytes:
    """투명 배경에 흰 글자를 가운데 정렬해 PNG 바이트로 반환(알파 보존)."""
    from io import BytesIO

    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", IMAGE_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 글자 크기를 화면 너비에 맞춰 자동으로 키운다.
    font = None
    for size in range(120, 10, -4):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
        except Exception:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
            except Exception:
                font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if w <= IMAGE_SIZE[0] * 0.9 and h <= IMAGE_SIZE[1] * 0.9:
            break

    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (IMAGE_SIZE[0] - w) / 2 - bbox[0]
    y = (IMAGE_SIZE[1] - h) / 2 - bbox[1]
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── EMO 전용 raw TCP 파일 서버 ──────────────────────────────────────────────
# EMO는 표준 HTTP가 아니라 "파일 이름 한 줄을 보내고 원시 바이트를 받는" 단순
# 프로토콜을 쓴다 (실험에서 확인: 요청 첫 줄이 그냥 'sticker.png' 였음).
# 그래서 http.server 대신, 접속하면 그냥 이미지 바이트를 흘려보내는 서버를 쓴다.
class RawImageHandler(socketserver.BaseRequestHandler):
    data: bytes = b""

    def handle(self):
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"  [TCP] 연결 들어옴: {peer}")
        # EMO가 보내는 요청(파일 이름 등)을 잠깐 읽어서 그대로 기록한다.
        try:
            self.request.settimeout(3.0)
            req = self.request.recv(2048)
            print(f"  [TCP] {peer} 요청(raw): {req!r}")
        except Exception as e:
            print(f"  [TCP] {peer} recv: {e}")
        # 원시 이미지 바이트 전송 (EMO는 set_eye 의 length 만큼 읽어간다)
        try:
            self.request.sendall(RawImageHandler.data)
            print(f"  [TCP] {peer} 이미지 {len(RawImageHandler.data)} bytes 전송 완료")
        except Exception as e:
            print(f"  [TCP] {peer} send: {e}")


class ReuseTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def prepare_image() -> bytes:
    """인자에 따라 표시할 PNG 바이트를 준비한다.
    어떤 경로든 마지막에 normalize_for_emo()로 EMO 화면 규격(320×240 PNG)에 맞춘다."""
    args = sys.argv[1:]
    if not args:
        print('[이미지] 기본 "DGIST" 텍스트 이미지를 생성합니다.')
        return normalize_for_emo(make_text_image("DGIST"))
    if args[0] == "text":
        word = args[1] if len(args) > 1 else "DGIST"
        print(f'[이미지] "{word}" 텍스트 이미지를 생성합니다.')
        return normalize_for_emo(make_text_image(word))
    if args[0] == "solid":
        color = args[1] if len(args) > 1 else "red"
        print(f'[진단] 단색 "{color}" 320×240 이미지를 생성합니다.')
        return normalize_for_emo(make_solid_image(color))
    if args[0] == "volcano":
        print("[이미지] 화산 폭발 그래픽을 생성합니다.")
        return normalize_for_emo(make_volcano_image())
    if args[0] == "dgist":
        # 바탕화면의 DGIST_UI.png 를 사용
        path = os.path.expanduser("~/Desktop/DGIST_UI.png")
    else:
        path = args[0]
    if not os.path.isfile(path):
        print(f"❌ 파일을 찾을 수 없습니다: {path}")
        sys.exit(1)
    print(f"[이미지] 파일을 사용합니다: {path}")
    with open(path, "rb") as f:
        raw = f.read()
    print("[이미지] EMO 화면 규격(320×240 PNG)으로 변환합니다.")
    return normalize_for_emo(raw)


async def send_and_capture(ecm, packet: bytes, wait: float = 2.0):
    """JSON 패킷을 보내고, EMO가 BLE로 돌려주는 응답(eye_rsp 등)을 잡아서 출력한다.
    EmoConnectManager._handle_rx 가 응답을 self._resonse 에 저장하므로 그걸 폴링한다."""
    ecm._resonse = None
    await ecm.sendCommand(packet)
    waited = 0.0
    while waited < wait:
        await asyncio.sleep(0.2)
        waited += 0.2
        if getattr(ecm, "_resonse", None) is not None:
            print(f"  ↩︎ EMO 응답: {ecm._resonse}")
            return ecm._resonse
    print("  ↩︎ EMO 응답 없음 (응답을 보내지 않음)")
    return None


async def push_eye_image(ecm, ip: str, data: bytes, tran: int = 100, wait_fetch: float = 4.0):
    """주어진 이미지 바이트를 EMO에 set_eye로 푸시한다(서버 데이터 교체 후 전송).
    tran 은 set_eye 의 투명도로 추정되는 값(100=불투명, 0=투명)."""
    RawImageHandler.data = data
    set_eye = {
        "data": {
            "image": {"length": len(data), "name": "sticker.png", "tran": tran},
            "op": "set_eye",
            "server": {"ip": ip, "port": EMO_HTTP_PORT},
        },
        "type": "customize_req",
    }
    await send_and_capture(ecm, encode_json(set_eye), wait=3.0)
    # EMO가 받아갈 시간을 준다
    waited = 0.0
    while waited < wait_fetch:
        await asyncio.sleep(0.5)
        waited += 0.5
        if not _is_connected(ecm):
            break


async def restore_normal_eyes(ecm, ip: str):
    """눈 위에 덮인 커스텀 이미지(오버레이)를 치워서 뒤에 있는 평소 눈이 보이게 한다.
    이미지는 살아있는 눈 위에 얹히는 오버레이이므로, '복원'이 아니라 '오버레이 제거'가
    필요하다. set_eye 재전송이 오버레이를 '교체'한다는 점을 이용해,
    완전 투명한 이미지로 교체한다 → EMO가 알파를 인식하면 오버레이가 사라진다."""
    if not _is_connected(ecm):
        return

    print("\n[정리] 완전 투명한 이미지로 교체해 오버레이를 지웁니다...")
    # 같은 sticker.png 자리에 완전 투명 PNG를 다시 푸시 → 오버레이 제거
    await push_eye_image(ecm, ip, make_clear_image(), tran=100, wait_fetch=3.0)
    # 커스터마이즈 모드 종료
    if _is_connected(ecm):
        await send_and_capture(ecm, encode_json({"data": {"op": "out"}, "type": "customize_req"}), wait=2.0)
    print("   투명 이미지 교체 완료. EMO 눈이 다시 보이는지 확인하세요.")


async def main():
    # --noclear: 정리(투명 이미지 재전송 + op:out) 단계를 건너뛰고 바로 BLE 연결을
    # 끊어본다. set_eye 재전송으로 오버레이를 지우는 시도가 계속 무응답이었으므로,
    # "그냥 연결을 끊으면 EMO가 세션 종료로 인식해 자동 복귀하는지"를 확인하기 위함.
    no_clear = "--noclear" in sys.argv
    if no_clear:
        sys.argv.remove("--noclear")

    img_bytes = prepare_image()
    print(f"[이미지] 준비 완료 ({len(img_bytes)} bytes)")

    ecm = await connect()
    if ecm is None:
        return

    # 먼저 raw TCP 서버부터 띄운다 (EMO가 op:in 직후 바로 받으러 올 수도 있으므로).
    ip = get_local_ip()
    RawImageHandler.data = img_bytes
    httpd = None
    try:
        httpd = ReuseTCPServer(("0.0.0.0", EMO_HTTP_PORT), RawImageHandler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        print(f"[서버] raw TCP 이미지 서버 시작: {ip}:{EMO_HTTP_PORT}  ({len(img_bytes)} bytes)")
    except OSError as e:
        print(f"❌ 포트 {EMO_HTTP_PORT} 사용 중입니다 ({e}). 다른 서버를 끄고 다시 실행하세요.")
        print(f"   (정리: lsof -tiTCP:{EMO_HTTP_PORT} -sTCP:LISTEN | xargs kill -9)")
        await ecm.disconnect()
        return

    try:
        # ── 1단계: 커스터마이즈 모드 진입 (op:in 이 result:1 을 줘야 정상) ──
        print("\n[1단계] customize_req(op:in) — 커스터마이즈 모드 진입 (result:1 이어야 성공)")
        rsp = await send_and_capture(ecm, encode_json({"data": {"op": "in"}, "type": "customize_req"}), wait=6.0)
        if not _is_connected(ecm):
            print("❌ EMO가 연결을 끊었습니다 => fw3.x가 이 JSON 명령을 거부.")
            return
        result_in = (rsp or {}).get("data", {}).get("result")
        if result_in == 1:
            print("✅ op:in 성공 (result:1) — 커스터마이즈 모드 진입됨.")
        else:
            print(f"⚠️  op:in 응답이 result:1 이 아닙니다 (받은 값: {result_in}).")
            print("    그래도 set_eye 를 계속 시도해 봅니다.")

        # ── 2단계: set_eye 전송 → EMO가 HTTP로 이미지를 가지러 오는지 확인 ──
        set_eye = {
            "data": {
                "image": {"length": len(img_bytes), "name": "sticker.png", "tran": 100},
                "op": "set_eye",
                "server": {"ip": ip, "port": EMO_HTTP_PORT},
            },
            "type": "customize_req",
        }
        print("\n[2단계] set_eye 전송 — EMO가 이미지를 내려받는지 관찰")
        print(f"   서버 주소를 EMO에게 알림: {ip}:{EMO_HTTP_PORT}")
        await send_and_capture(ecm, encode_json(set_eye), wait=3.0)
        print("   (아래에 '[TCP] 연결 들어옴' 이 찍히면 EMO가 실제로 받으러 온 것)")

        # 이미지를 약 8초간 화면에 띄워 두고 확인 (그 후 자동으로 끈다)
        print("\n[표시] 약 8초간 EMO 눈 화면을 확인하세요. (이후 자동으로 평소 얼굴로 복귀)")
        for _ in range(16):
            await asyncio.sleep(0.5)
            if getattr(ecm, "_resonse", None) is not None:
                print(f"   ↩︎ EMO 추가 응답: {ecm._resonse}")
                ecm._resonse = None
            if not _is_connected(ecm):
                print("⚠️  대기 중 EMO가 연결을 끊었습니다.")
                break

        # ── 3단계: 이미지를 지우기 (검은 화면 덮어쓰기) ──
        #    서버가 아직 살아 있어야 EMO가 검은 화면을 받아갈 수 있으므로 여기서 수행.
        if no_clear:
            print("\n[정리 건너뜀] --noclear: 정리 명령 없이 바로 연결을 끊습니다.")
        else:
            await restore_normal_eyes(ecm, ip)

    finally:
        try:
            if _is_connected(ecm):
                await ecm.disconnect()
                print("연결을 종료했습니다.")
            else:
                print("(EMO가 이미 연결을 끊은 상태입니다.)")
        except Exception as e:
            print(f"(종료 중 무시된 예외: {e})")
        finally:
            if httpd is not None:
                httpd.shutdown()  # 서버는 지우기까지 끝난 뒤 마지막에 닫는다


if __name__ == "__main__":
    asyncio.run(main())
