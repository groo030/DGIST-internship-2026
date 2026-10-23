// ============================================================
// Peltier 쪽 면 - 평면도(XY, 정면에서 본 모습)
// 아래쪽 변("erm_link" 부분)이 ERM 면과 연결됨.
// ============================================================

face_size  = 25;   // 면의 가로/세로 (정사각형)
housing_t  = 1.2;  // 하우징 두께 (사방 테두리)
border_gap = 0.1;  // 테두리 안쪽 빈 공간 (X방향: 좌우 브라켓/연결부 폭 계산용)
top_gap    = 1.3;  // 위쪽 테두리 - 브라켓 사이 Y방향 빈 공간 (bracket_h 1.2mm 축소분 보충: 0.1 -> 1.3)

bracket_w  = 1.2;   // 세로 브라켓(Peltier 고정) 가로 두께
bracket_h  = 20;    // 세로 브라켓(Peltier 고정) 세로 높이
open_w     = 20;    // 브라켓 사이 뚫린 공간 가로 폭
erm_link_h = 1.2;   // ERM 면과 연결되는 부분의 세로 두께 (브라켓과 바로 붙음)
mid_gap    = 0.1;   // ERM 연결부 - 바깥 하우징 테두리 사이 빈 공간

bracket_z  = 4;     // Peltier 고정 두께의 Z방향 깊이
guide_h    = 0.01;  // 참고용 2D 레이아웃 표시용 얇은 두께

// --- 경계 계산 (중심 원점) ---
frame_inner_w = face_size - 2 * housing_t;              // 테두리 프레임 안쪽 폭 (22.6mm)
inner_w       = face_size - 2 * (housing_t + border_gap); // 테두리+갭 안쪽 폭 (22.4mm)

// Y축 (위 -> 아래)
y_top       = face_size / 2;
y1 = y_top - housing_t;      // top_gap 상단
y2 = y1 - top_gap;           // 브라켓 상단
y3 = y2 - bracket_h;         // ERM 연결부 상단 (브라켓과 바로 붙음)
y4 = y3 - erm_link_h;        // mid_gap 상단
y5 = y4 - mid_gap;           // 하우징 아래쪽 테두리 상단
y_bottom = y5 - housing_t;   // 검증용 (-face_size/2 와 같아야 함)

// X축 (왼쪽 -> 오른쪽)
x_left        = -face_size / 2;
x1 = x_left + housing_t;         // border_gap 오른쪽 끝
x2 = x1 + border_gap;            // 왼쪽 브라켓 오른쪽 끝
x3 = x2 + bracket_w;             // 뚫린 공간(open_w) 오른쪽 끝
x4 = x3 + open_w;                // 오른쪽 브라켓 왼쪽 끝
x5 = x4 + bracket_w;             // border_gap 오른쪽 끝
x_right_check = x5 + border_gap + housing_t; // 검증용 (face_size/2 와 같아야 함)

bracket_center_y = (y2 + y3) / 2;
left_bracket_center_x  = (x2 + x3) / 2;
right_bracket_center_x = (x4 + x5) / 2;

echo("y_bottom check =", y_bottom, " (should be", -face_size / 2, ")");
echo("x_right check =", x_right_check, " (should be", face_size / 2, ")");
echo("bracket centers: left =", left_bracket_center_x, " right =", right_bracket_center_x, " y =", bracket_center_y);

// --- 참고용 2D 레이아웃 (Z 깊이 미정 영역, 반투명 표시) ---
// 브라켓 자리(20mm x 20mm)를 관통 구멍으로 뚫음
module face_reference_2d() {
    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([0, bracket_center_y, -0.1])
                linear_extrude(height = housing_t + 0.2)
                    square([open_w, bracket_h], center = true);
        }
}

// --- ERM 연결부 (실제 3D, 바닥판 위에 Z 깊이 4mm 추가) ---
module erm_link() {
    color("green")
        translate([0, 0, housing_t])
            linear_extrude(height = bracket_z)
                translate([0, y3 - erm_link_h / 2])
                    square([inner_w, erm_link_h], center = true);
}

// --- Peltier 고정 브라켓 (실제 3D, 바닥판 위에 Z 깊이 4mm 추가) ---
module peltier_brackets() {
    color("SteelBlue")
        translate([0, 0, housing_t])
            linear_extrude(height = bracket_z) {
                translate([left_bracket_center_x, bracket_center_y])
                    square([bracket_w, bracket_h], center = true);
                translate([right_bracket_center_x, bracket_center_y])
                    square([bracket_w, bracket_h], center = true);
            }
}

face_reference_2d();
erm_link();
peltier_brackets();
