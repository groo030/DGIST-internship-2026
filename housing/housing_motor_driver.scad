// ============================================================
// 모터 드라이버 쪽 면 - 평면도(XY, 정면에서 본 모습)
// 아래쪽 변이 ERM 면과 연결됨 (브라켓이 바로 아래쪽 하우징 테두리에 맞닿음).
// ============================================================

face_size = 25;   // 면의 가로/세로 (정사각형)
housing_t = 1.2;  // 하우징 두께 (사방 테두리)

gap_y     = 2.3;   // 위쪽 하우징 테두리 - 브라켓 사이 빈 공간
bracket_h = 20.3;  // 세로 브라켓(모터 드라이버 고정) 세로 높이
gap_x     = 2.2;   // 좌우 하우징 테두리 - 브라켓 사이 빈 공간
bracket_w = 1.5;   // 세로 브라켓(모터 드라이버 고정) 가로 두께
open_w    = 15.2;  // 브라켓 사이 뚫린 공간 가로 폭

bracket_z = 3;     // 모터 드라이버 고정 두께의 Z방향 깊이 (ERM 면 스택의 3mm 재사용)
guide_h   = 0.01;  // 참고용 2D 레이아웃 표시용 얇은 두께

frame_inner_w = face_size - 2 * housing_t; // 테두리 프레임 안쪽 폭 (22.6mm)

// Y축 (위 -> 아래)
y_top = face_size / 2;
y1 = y_top - housing_t;   // gap_y 상단
y2 = y1 - gap_y;          // 브라켓 상단
y3 = y2 - bracket_h;      // 브라켓 하단 = 아래쪽 하우징 테두리 상단 (ERM 연결)
y_bottom = y3 - housing_t; // 검증용 (-face_size/2 와 같아야 함)

// X축 (왼쪽 -> 오른쪽)
x_left = -face_size / 2;
x1 = x_left + housing_t;  // gap_x 오른쪽 끝
x2 = x1 + gap_x;          // 왼쪽 브라켓 오른쪽 끝
x3 = x2 + bracket_w;      // 뚫린 공간(open_w) 오른쪽 끝
x4 = x3 + open_w;         // 오른쪽 브라켓 왼쪽 끝
x5 = x4 + bracket_w;      // gap_x 오른쪽 끝
x_right_check = x5 + gap_x + housing_t; // 검증용 (face_size/2 와 같아야 함)

bracket_center_y = (y2 + y3) / 2;
left_bracket_center_x  = (x2 + x3) / 2;
right_bracket_center_x = (x4 + x5) / 2;

echo("y_bottom check =", y_bottom, " (should be", -face_size / 2, ")");
echo("x_right check =", x_right_check, " (should be", face_size / 2, ")");
echo("bracket centers: left =", left_bracket_center_x, " right =", right_bracket_center_x, " y =", bracket_center_y);

// --- 참고용 2D 레이아웃 ---
module face_reference_2d() {
    // 하우징 바닥판 (면 전체, 실제 3D, 두께 1.2mm)
    color("gray")
        linear_extrude(height = housing_t)
            square([face_size, face_size], center = true);
}

// --- 모터 드라이버 고정 브라켓 (실제 3D, 바닥판 위에 Z 깊이 3mm 추가) ---
module motor_driver_brackets() {
    color("purple")
        translate([0, 0, housing_t])
            linear_extrude(height = bracket_z) {
                translate([left_bracket_center_x, bracket_center_y])
                    square([bracket_w, bracket_h], center = true);
                translate([right_bracket_center_x, bracket_center_y])
                    square([bracket_w, bracket_h], center = true);
            }
}

face_reference_2d();
motor_driver_brackets();
