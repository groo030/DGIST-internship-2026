"""
HTTP 서버 도달 테스트 (BLE 없음) — 2026-06-18

emo_eye.py 의 이미지 전송이 안 될 때, 'EMO가 노트북 HTTP 서버에 접속할 수 있는가'를
BLE와 분리해서 확인하기 위한 스크립트.

이 스크립트는 BLE를 쓰지 않는다. 그냥 emo_eye.py 와 똑같은 HTTP 서버(포트 9090)를
띄우고, 접속이 들어올 때마다 로그를 찍는다.

테스트 방법
  1) 노트북에서 실행:   python3 http_test.py
     (처음 실행 시 '들어오는 연결을 허용하시겠습니까?' 팝업이 뜨면 반드시 '허용')
  2) EMO와 '같은 WiFi(2.4GHz)' 에 연결된 '휴대폰'의 브라우저에서 아래 주소 접속:
        http://<노트북IP>:9090/sticker.png
     - DGIST 이미지가 폰에 보이면 => HTTP 경로 정상 (EMO도 도달 가능)
     - 화면에 '[요청 들어옴]' 로그도 찍힘
     - 접속이 안 되거나 멈추면 => 방화벽이 막았거나, 폰/EMO가 다른 네트워크에 있음
  3) 확인이 끝나면 Ctrl+C 로 종료.
"""
import http.server
import socket
from io import BytesIO


def make_image() -> bytes:
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (240, 240), (0, 0, 0))
        d = ImageDraw.Draw(img)
        try:
            f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 80)
        except Exception:
            f = ImageFont.load_default()
        d.text((20, 90), "DGIST", fill=(255, 255, 255), font=f)
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        print(f"(PIL 없음 → 더미 데이터 사용: {e})")
        return b"DGIST-TEST-IMAGE"


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


DATA = make_image()


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"[요청 들어옴] {self.client_address[0]} → {self.path}")
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(DATA)))
        self.end_headers()
        self.wfile.write(DATA)

    def log_message(self, *a):
        pass


def main():
    ip = get_local_ip()
    port = 9090
    print(f"이미지 크기: {len(DATA)} bytes")
    print(f"HTTP 서버 시작: http://{ip}:{port}/sticker.png")
    print("\n같은 WiFi에 연결된 '휴대폰 브라우저'에서 위 주소로 접속해 보세요.")
    print("이미지가 뜨고 아래에 '[요청 들어옴]' 로그가 찍히면 성공입니다.")
    print("(종료: Ctrl+C)\n")
    srv = http.server.HTTPServer(("0.0.0.0", port), H)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
    finally:
        srv.shutdown()


if __name__ == "__main__":
    main()
