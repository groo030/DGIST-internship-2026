// ============================================================
// 플랫폼 v2 - 밑면 평면도(XY, 위에서 본 모습)
// 55mm x 55mm 정사각형, 사방 1.2mm 테두리, 안쪽에 세로 립(1mm 두께) 배치.
// ============================================================

module platform_v2_bottom() {
    face_size = 55;   // 면의 가로/세로 (정사각형)
    housing_t = 1.2;  // 하우징 두께 (사방 테두리)

    rib_w      = 1;      // 세로 립 두께 (X방향)
    left_w     = 40.08;  // 안쪽 왼쪽 구간 폭 (내부 왼쪽 테두리 - 립)
    right_w    = 11.52;  // 안쪽 오른쪽 구간 폭 (립 - 내부 오른쪽 테두리)

    rib_gap    = 1.3;    // 립 위/아래 빈 공간 (안쪽 테두리 기준)
    rib_len    = 50;     // 세로 립 길이

    rib_z      = 1.2;    // 립의 Z방향 돌출 깊이 (바닥판 위에 추가)

    inner_size = face_size - 2 * housing_t; // 안쪽 치수 (52.6mm)

    echo("[PlatformV2] inner_size check =", inner_size,
         " (should be", left_w + rib_w + right_w, ")");
    echo("[PlatformV2] inner_size check(Y) =", inner_size,
         " (should be", rib_gap + rib_len + rib_gap, ")");

    // --- X축 경계 (왼쪽 -> 오른쪽, 중심 원점) ---
    x_left       = -face_size / 2;
    x_inner_l    = x_left + housing_t;      // 안쪽 왼쪽 테두리
    x_rib_l      = x_inner_l + left_w;      // 립 왼쪽 면
    x_rib_r      = x_rib_l + rib_w;         // 립 오른쪽 면
    x_inner_r    = x_rib_r + right_w;       // 안쪽 오른쪽 테두리 (face_size/2 - housing_t 와 같아야 함)

    // --- Y축 경계 (립 길이 방향, 중심 원점) ---
    y_top        = face_size / 2;
    y_inner_top  = y_top - housing_t;       // 안쪽 위쪽 테두리
    y_rib_top    = y_inner_top - rib_gap;   // 립 윗면
    y_rib_bottom = y_rib_top - rib_len;     // 립 아랫면 (y_inner_bottom + rib_gap 와 같아야 함)
    y_inner_bottom = -face_size / 2 + housing_t; // 안쪽 아래쪽 테두리

    rib_center_x = (x_rib_l + x_rib_r) / 2;
    rib_center_y = (y_rib_top + y_rib_bottom) / 2;

    echo("[PlatformV2] x_inner_r check =", x_inner_r, " (should be", face_size / 2 - housing_t, ")");
    echo("[PlatformV2] rib_bottom check =", y_rib_bottom, " (should be", y_inner_bottom + rib_gap, ")");
    echo("[PlatformV2] rib center =", rib_center_x, rib_center_y);

    // 바닥판 (면 전체, 실제 3D, 두께 1.2mm)
    color("gray")
        linear_extrude(height = housing_t)
            square([face_size, face_size], center = true);

    // 세로 립 (실제 3D, 바닥판 위에 Z 깊이 1.2mm 추가)
    color("SteelBlue")
        translate([rib_center_x, rib_center_y, housing_t])
            linear_extrude(height = rib_z)
                square([rib_w, rib_len], center = true);

    // 사방 옆면 벽 (실제 3D, 바닥판 위에 Z방향으로 20.6mm 쌓아 올림)
    // 안쪽 네 모서리(원래 직각 코너)에 반지름 4mm 부채꼴 보강재를 덧붙임
    // (안쪽 면 기준 직선 구간 44.6mm = 52.6 - 2*4 만 남고, 모서리 쪽은 보강재로 채워짐)
    // 그 보강재 안에서, 벽면 두 곳으로부터 각각 1.2mm 여백을 두고 지름 2mm 나사 구멍을 뚫음
    wall_h    = 20.6;  // 벽 높이
    fillet_r  = 4;     // 모서리 보강재 반지름 (안쪽 모서리 기준, 44.6mm 직선구간과 일치)
    screw_d   = 2;     // 나사 구멍 지름
    hole_gap  = 1.2;   // 바깥쪽 모서리 - 구멍 중심까지의 대각선 각 축 성분 (구멍 중심 = 바깥 모서리에서 2.2, 2.2)
    hole_off  = face_size / 2 - hole_gap - screw_d / 2; // 바깥쪽 모서리 기준 중심까지 거리(=25.3mm)
    corner_off = inner_size / 2; // 안쪽 모서리(원래 직각 코너) 위치 (=26.3mm, 보강재 형상 기준)

    inner_straight = inner_size - 2 * fillet_r; // 보강재 사이 직선 구간 (44.6mm)

    echo("[PlatformV2] inner_straight check =", inner_straight, " (should be 44.6)");
    echo("[PlatformV2] hole_off =", hole_off);

    difference() {
        color("orange")
            translate([0, 0, housing_t])
                linear_extrude(height = wall_h)
                    union() {
                        difference() {
                            square([face_size, face_size], center = true);
                            square([inner_size, inner_size], center = true);
                        }
                        // 모서리 보강재 (안쪽 코너에서 반지름 4mm 부채꼴, 캐비티 쪽으로 채움)
                        for (sx = [-1, 1])
                            for (sy = [-1, 1])
                                intersection() {
                                    translate([sx * corner_off, sy * corner_off])
                                        circle(r = fillet_r, $fn = 60);
                                    square([inner_size, inner_size], center = true);
                                }
                    }

        for (sx = [-1, 1])
            for (sy = [-1, 1])
                translate([sx * hole_off, sy * hole_off, housing_t - 0.1])
                    cylinder(d = screw_d, h = wall_h + 0.2, $fn = 40);
    }
}

platform_v2_bottom();
