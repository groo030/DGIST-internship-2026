// ============================================================
// 하우징 조립 - ERM 면 + Peltier 면
// ERM 면: 바닥 (XY 평면, world Z=0)
// Peltier 면: ERM 면의 +Y쪽 가장자리에서 수직으로 세움.
//   Peltier 면의 로컬 Y축(위<->아래) -> world Z축(위<->아래)
//   Peltier 면의 로컬 Z축(브라켓 돌출) -> world -Y축(하우징 안쪽으로 돌출)
// ============================================================

// ---------------- ERM 면 ----------------
module erm_face() {
    face_size      = 25;   // 면의 가로/세로 (정사각형)
    housing_t      = 1.2;  // 하우징 두께 (사방 테두리)
    border_gap     = 0.1;  // 테두리 안쪽 빈 공간 (Peltier 쪽 면과 동일한 규칙 적용)
    peltier_t      = 4;    // Peltier 고정 두께 (Z 깊이는 Peltier 면에서 결정)
    gap_1          = 2.05; // 빈 공간 (peltier_t 5.5->4 축소로 생긴 1.5mm를 ERM 링과 가까운 이 gap에 보충)
    erm_ring_t     = 1.5;  // ERM 고정 두께 (링 벽 두께)
    erm_hole_d     = 10;   // ERM 부품이 들어갈 원형 공간 지름
    gap_2          = 0.55; // 빈 공간 (ERM 링 두께 축소로 생긴 1mm 중 0.5mm 보충)
    motor_driver_t = 3;    // 모터 드라이버 고정 두께 (Z 깊이는 다른 면 설계 시 결정)

    erm_ring_z     = 2.6;  // ERM 고정 두께의 Z방향 깊이 (확정값)
    guide_h        = 0.01; // 참고용 2D 레이아웃 표시용 얇은 두께

    // --- Y축 경계 계산 (중심 원점, 위 -> 아래) ---
    y_top    = face_size / 2;
    y1 = y_top - housing_t;   // peltier 밴드 상단
    y2 = y1 - peltier_t;      // gap_1 상단
    y3 = y2 - gap_1;          // erm 링 위쪽 벽 상단
    y4 = y3 - erm_ring_t;     // erm 구멍 상단
    y5 = y4 - erm_hole_d;     // erm 구멍 하단 / 링 아래쪽 벽 상단
    y6 = y5 - erm_ring_t;     // gap_2 상단
    y7 = y6 - gap_2;          // 모터 드라이버 밴드 상단
    y8 = y7 - motor_driver_t; // 하우징 아래쪽 테두리 상단
    y_bottom = y8 - housing_t; // 검증용 (-face_size/2 와 같아야 함)

    erm_center_y = (y4 + y5) / 2;
    erm_inner_r  = erm_hole_d / 2;
    erm_outer_r  = erm_inner_r + erm_ring_t;

    frame_inner_w = face_size - 2 * housing_t;
    inner_w       = face_size - 2 * (housing_t + border_gap);

    echo("[ERM] y_bottom check =", y_bottom, " (should be", -face_size / 2, ")");
    echo("[ERM] ring center_y =", erm_center_y, " inner_r =", erm_inner_r, " outer_r =", erm_outer_r);

    // 하우징 바닥판 (면 전체, 실제 3D, 두께 1.2mm)
    // ERM 링이 뚫린 부분(9시 방향) 쪽, -X 가장자리에서 0.8mm 띄운 지점부터
    // (기존 0.2mm에서 ERM 링쪽으로 0.6mm 추가 이동)
    // 5mm(Y) x 1mm(X) 직사각형을 완전 관통(Z 1.2mm 전체). Y는 8.8mm씩 양쪽에서 띄워 중앙 정렬.
    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([-face_size / 2 + 0.8, -2.5, 0])
                cube([1, 5, housing_t]);
        }

    // 참고용 2D 레이아웃 (Z 깊이 미정 영역, 바닥판 위에 반투명 표시)
    color("orange", 0.3)
        translate([0, 0, housing_t])
            linear_extrude(height = guide_h)
                translate([0, y1 - peltier_t / 2])
                    square([inner_w, peltier_t], center = true);

    color("cyan", 0.3)
        translate([0, 0, housing_t])
            linear_extrude(height = guide_h)
                translate([0, y7 - motor_driver_t / 2])
                    square([inner_w, motor_driver_t], center = true);

    // ERM 링에서 잘라낼 구간: 9시 방향(180도) 기준 45도
    erm_gap_center_deg = 180;
    erm_gap_width_deg  = 45;
    erm_gap_r          = erm_outer_r + 1; // 확실히 잘리도록 여유

    // ERM 고정 링 (실제 3D, 바닥판 위에 Z 깊이 2.6mm 추가, 9시 방향 45도 절개)
    color("SteelBlue")
        translate([0, erm_center_y, housing_t])
            linear_extrude(height = erm_ring_z)
                difference() {
                    difference() {
                        circle(r = erm_outer_r, $fn = 100);
                        circle(r = erm_inner_r, $fn = 100);
                    }
                    polygon(points = [
                        [0, 0],
                        [erm_gap_r * cos(erm_gap_center_deg - erm_gap_width_deg / 2),
                         erm_gap_r * sin(erm_gap_center_deg - erm_gap_width_deg / 2)],
                        [erm_gap_r * cos(erm_gap_center_deg + erm_gap_width_deg / 2),
                         erm_gap_r * sin(erm_gap_center_deg + erm_gap_width_deg / 2)]
                    ]);
                }
}

// ---------------- Peltier 면 ----------------
module peltier_face() {
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

    frame_inner_w = face_size - 2 * housing_t;
    inner_w       = face_size - 2 * (housing_t + border_gap);

    // Y축 (위 -> 아래)
    y_top = face_size / 2;
    y1 = y_top - housing_t;
    y2 = y1 - top_gap;
    y3 = y2 - bracket_h;
    y4 = y3 - erm_link_h;
    y5 = y4 - mid_gap;
    y_bottom = y5 - housing_t;

    // X축 (왼쪽 -> 오른쪽)
    x_left = -face_size / 2;
    x1 = x_left + housing_t;
    x2 = x1 + border_gap;
    x3 = x2 + bracket_w;
    x4 = x3 + open_w;
    x5 = x4 + bracket_w;
    x_right_check = x5 + border_gap + housing_t;

    bracket_center_y = (y2 + y3) / 2;
    left_bracket_center_x  = (x2 + x3) / 2;
    right_bracket_center_x = (x4 + x5) / 2;

    echo("[Peltier] y_bottom check =", y_bottom, " (should be", -face_size / 2, ")");
    echo("[Peltier] x_right check =", x_right_check, " (should be", face_size / 2, ")");

    // 하우징 바닥판 (면 전체, 실제 3D, 두께 1.2mm)
    // 브라켓 자리(20mm x 20mm)를 관통 구멍으로 뚫음
    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([0, bracket_center_y, -0.1])
                linear_extrude(height = housing_t + 0.2)
                    square([open_w, bracket_h], center = true);
        }

    // ERM 연결부 (실제 3D, 바닥판 위에 Z 깊이 4mm 추가)
    color("green")
        translate([0, 0, housing_t])
            linear_extrude(height = bracket_z)
                translate([0, y3 - erm_link_h / 2])
                    square([inner_w, erm_link_h], center = true);

    // Peltier 고정 브라켓 (실제 3D, 바닥판 위에 Z 깊이 4mm 추가)
    color("SteelBlue")
        translate([0, 0, housing_t])
            linear_extrude(height = bracket_z) {
                translate([left_bracket_center_x, bracket_center_y])
                    square([bracket_w, bracket_h], center = true);
                translate([right_bracket_center_x, bracket_center_y])
                    square([bracket_w, bracket_h], center = true);
            }
}

// ---------------- 오른쪽(3시 방향) 면 ----------------
// 다른 부품 없이 1.2mm 두께 벽에 정가운데 직사각형 구멍만 있는 단순한 면.
module right_face() {
    face_size = 25;    // 면의 가로/세로 (정사각형, ERM/Peltier 면과 동일)
    housing_t = 1.2;   // 하우징 두께 (벽 두께)
    hole_w    = 12.42; // 정가운데 구멍 가로
    hole_h    = 5.75;  // 정가운데 구멍 세로

    color("gray")
        linear_extrude(height = housing_t)
            difference() {
                square([face_size, face_size], center = true);
                square([hole_w, hole_h], center = true);
            }
}

// ---------------- 모터 드라이버 쪽 면 ----------------
module motor_driver_face() {
    face_size = 25;   // 면의 가로/세로 (정사각형)
    housing_t = 1.2;  // 하우징 두께 (사방 테두리)

    gap_y     = 2.3;   // 위쪽 하우징 테두리 - 브라켓 사이 빈 공간
    bracket_h = 20.3;  // 세로 브라켓(모터 드라이버 고정) 세로 높이
    gap_x     = 2.2;   // 좌우 하우징 테두리 - 브라켓 사이 빈 공간
    bracket_w = 1.5;   // 세로 브라켓(모터 드라이버 고정) 가로 두께
    open_w    = 15.2;  // 브라켓 사이 뚫린 공간 가로 폭

    bracket_z = 3;     // 모터 드라이버 고정 두께의 Z방향 깊이 (ERM 면 스택의 3mm 재사용)

    // Y축 (위 -> 아래)
    y_top = face_size / 2;
    y1 = y_top - housing_t;
    y2 = y1 - gap_y;
    y3 = y2 - bracket_h;       // 브라켓 하단 = 아래쪽 테두리 상단 (ERM 연결)
    y_bottom = y3 - housing_t;

    // X축 (왼쪽 -> 오른쪽)
    x_left = -face_size / 2;
    x1 = x_left + housing_t;
    x2 = x1 + gap_x;
    x3 = x2 + bracket_w;
    x4 = x3 + open_w;
    x5 = x4 + bracket_w;
    x_right_check = x5 + gap_x + housing_t;

    bracket_center_y = (y2 + y3) / 2;
    left_bracket_center_x  = (x2 + x3) / 2;
    right_bracket_center_x = (x4 + x5) / 2;

    echo("[MotorDriver] y_bottom check =", y_bottom, " (should be", -face_size / 2, ")");
    echo("[MotorDriver] x_right check =", x_right_check, " (should be", face_size / 2, ")");

    // 하우징 바닥판 (면 전체, 실제 3D, 두께 1.2mm)
    color("gray")
        linear_extrude(height = housing_t)
            square([face_size, face_size], center = true);

    // 모터 드라이버 고정 브라켓 (실제 3D, 바닥판 위에 Z 깊이 3mm 추가)
    color("purple")
        translate([0, 0, housing_t])
            linear_extrude(height = bracket_z) {
                translate([left_bracket_center_x, bracket_center_y])
                    square([bracket_w, bracket_h], center = true);
                translate([right_bracket_center_x, bracket_center_y])
                    square([bracket_w, bracket_h], center = true);
            }
}

// ---------------- 조립 ----------------
erm_face();

// Peltier 면을 ERM 면의 +Y쪽 가장자리(y=12.5)에 수직으로 세움 (위치는 그대로).
// 면 안의 패턴(브라켓/연결부)만 왼쪽(반시계 방향)으로 90도 회전.
// 로컬 Y -> world Z, 로컬 Z(브라켓 돌출) -> world -Y
translate([0, 12.5, 12.5])
    rotate([90, 0, 0])
        rotate([0, 0, 90])
            peltier_face();

// 오른쪽 면을 ERM 면의 +X쪽 가장자리(x=12.5)에 수직으로 세움.
translate([12.5, 0, 12.5])
    rotate([0, -90, 0])
        right_face();

// 모터 드라이버 면을 ERM 면의 -Y쪽 가장자리(y=-12.5)에 수직으로 세움.
// Peltier 면과 같은 형태의 변환을 쓰고, world Z축 기준 180도 돌려서 반대쪽 가장자리에 배치.
// 면 안의 패턴(브라켓)만 제자리에서 90도 회전.
rotate([0, 0, 180])
    translate([0, 12.5, 12.5])
        rotate([90, 0, 0])
            rotate([0, 0, 90])
                motor_driver_face();

// ---------------- 윗면 ----------------
// 다른 부품 없이 1.2mm 두께 벽만 있는 단순한 면. 박스 맨 위(z=25)를 막음.
// 뚫린 면(-X쪽, 왼쪽) 방향으로 1.2mm 잘라내서 클로저 부품이 들어갈 자리를 남김.
// 클로저 하우징의 나사 구멍(윗면 안쪽 면 기준 Z로 1.2mm 아래)에 맞춰
// 지름 5mm 보스(가장자리에서 안쪽으로 1.5mm) 1개를 가운데에 붙이고, 나사 구멍은
// 클로저 구멍과 같은 방향(X축)으로 지름 2mm 관통.
module top_face() {
    face_size = 25;   // 면의 가로/세로 (정사각형)
    housing_t = 1.2;  // 하우징 두께 (벽 두께)

    boss_d      = 4.4;  // 나사 보스 지름
    boss_depth  = 1.2;  // 나사 보스의 X방향 두께
    boss_x0     = -face_size / 2 + housing_t; // 가장자리(뚫린 부분)에서 안쪽으로 1.2mm 들어간 원래 지점
    boss_shift  = 0.6;   // ERM 면의 직사각형 구멍과 동일하게 0.6mm 안쪽으로 이동
    boss_x      = boss_x0 + boss_shift;
    screw_d     = 2;    // 나사 구멍 지름
    boss_y      = 0;    // 가운데 정렬
    boss_z      = -1.0; // 보스 맨 위(Z) 좌표가 판재 맨 위(z=housing_t=1.2)와 같도록 설정 (-1.0+4.4/2=1.2)

    difference() {
        union() {
            // 판재 자체 길이를 보스 이동분(0.6mm)만큼 더 줄임 (뚫린 가장자리에서 housing_t+boss_shift만큼 후퇴)
            color("gray")
                linear_extrude(height = housing_t)
                    translate([-face_size / 2 + housing_t + boss_shift, -face_size / 2])
                        square([face_size - housing_t - boss_shift, face_size], center = false);

            // 나사 보스 1개 (0.6mm 이동한 지점부터 안쪽으로 1.5mm, 구멍 축은 X방향)
            color("gray")
                translate([boss_x, boss_y, boss_z])
                    rotate([0, 90, 0])
                        cylinder(d = boss_d, h = boss_depth, $fn = 60);
        }

        // 나사 구멍 (X방향 관통, 보스를 지나 벽까지)
        translate([boss_x - 0.1, boss_y, boss_z])
            rotate([0, 90, 0])
                cylinder(d = screw_d, h = boss_depth + housing_t + 0.2, $fn = 40);
    }
}

translate([0, 0, 25 - 1.2])
    top_face();

// ---------------- 클로저 하우징 ----------------
// 뚫린 면(-X쪽)에 들어갈 평판. 조립체에 붙이지 않고 옆으로 떨어뜨려서 배치.
module closure_housing() {
    lid_w = 22.6;  // 평판 가로
    lid_h = 23.8;  // 평판 세로
    lid_t = 1.8;   // 평판 두께 (1.2 -> 1.8, 0.6mm 증가)
    plate_grow = lid_t - 1.2; // 두께 증가분 (0.6mm) - 바깥쪽(outer, z 음의 방향)으로 확장

    hole_d          = 2;   // 구멍 지름
    hole_y_from_top = 1.2; // 윗변 - 구멍 중심 거리 (가장 가까운 면의 모서리와 1.2mm 차이)

    hole_x = 0;                       // 가운데 정렬
    hole_y = lid_h / 2 - hole_y_from_top;

    tab_w    = 5;   // 하단 돌출부 가로
    tab_len  = 1.2; // 하단 돌출부가 평판 아래로 튀어나온 길이
    tab_z    = 1.0; // 돌출부의 Z방향 두께 (평판 바깥쪽 면과 밑면이 딱 맞음, 안쪽으로 0.8mm 단차)

    echo("[Closure] hole_x =", hole_x, " hole_y =", hole_y);

    // 메인 평판 (구멍 1개, 가운데). 안쪽면(z=1.2)은 고정, 바깥쪽면이 0.6mm 더 나감(z=-0.6)
    color("gray")
        translate([0, 0, -plate_grow])
            linear_extrude(height = lid_t)
                difference() {
                    square([lid_w, lid_h], center = true);
                    translate([hole_x, hole_y]) circle(d = hole_d, $fn = 50);
                }

    // 하단 돌출 탭 (평판 아래쪽 가장자리에서 1.2mm 튀어나옴).
    // Z방향으로는 평판 바깥쪽 면(z=-plate_grow)과 밑면이 딱 맞고, 두께는 1mm만
    // (평판 두께 1.8mm 중 안쪽으로 0.8mm는 단차로 비움)
    color("SlateGray")
        translate([0, -lid_h / 2 - tab_len / 2, -plate_grow])
            linear_extrude(height = tab_z)
                square([tab_w, tab_len], center = true);
}

// 조립체와 떨어뜨려서 배치 (뚫린 -X쪽 방향으로 멀리)
translate([-50, 0, 0])
    closure_housing();
