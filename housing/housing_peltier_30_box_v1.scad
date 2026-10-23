// ============================================================
// 하우징 Peltier 30x30 - box 조립 (Peltier 면 + 립이 있는 면 + +Y쪽 면 + +Z쪽 면)
// Peltier 면(바닥): housing_peltier_box_v2에서 가져옴. 전체 크기 25x25 -> 30x30으로 변경,
// 사각 링 안쪽 20.04x20.04는 그대로 유지 (ring_outer는 그대로라 이제 하우징 안쪽 경계와
// 떨어져 있음).
// 립이 있는 면(peltier_30_v1_face): Peltier 면의 -X쪽 가장자리에 부착, 평면 기준 90도 회전.
// 이 회전으로 로컬 X -> world Z(높이), 로컬 Y -> world Y(깊이, 부호 반전),
// 로컬 Z(립 돌출) -> world +X 로 대응됨. 립 Z방향 돌출 높이 8mm.
//
// closure1/closure2는 housing_peltier_30_closure1_v1.scad / housing_peltier_30_closure2_v1.scad로 분리됨.
// ============================================================

// ---------------- Peltier 면 (바닥, 30x30) ----------------
module peltier_v2_face() {
    face_size = 30;   // 면의 가로/세로 (정사각형, 25 -> 30으로 변경)
    housing_t = 1.2;  // 하우징 두께 (사방 테두리)

    frame_w = 1.28;   // 사각 링(프레임) 벽 두께 (변경 없음)
    sq_size = 20.08;  // 프레임 안쪽 정사각형 (Peltier 안착 공간, 관통 구멍) - 20.04에서 0.04mm 증가
    ring_z  = 3.8;    // 사각 링 Z방향 돌출 높이

    inner_size = face_size - 2 * housing_t; // 27.6mm (하우징 안쪽 치수)
    ring_outer = sq_size + 2 * frame_w;     // 22.64mm (sq_size와 함께 0.04mm 증가, frame_w는 그대로)

    echo("[Peltier_v2] ring_outer =", ring_outer, " sq_size =", sq_size);

    // 바닥판 (실제 3D, 두께 1.2mm). 사각 링 안쪽(20.08x20.08)은 관통 구멍.
    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([0, 0, -0.1])
                linear_extrude(height = housing_t + 0.2)
                    square([sq_size, sq_size], center = true);
        }

    // 사각 링(프레임): 중앙에 20.08x20.08 정사각형 안착 공간이 생김.
    // 바닥판 위로 ring_z만큼 돌출. X축 양수방향 벽은 제거되어 열려있음.
    color("SteelBlue")
        translate([0, 0, housing_t])
            linear_extrude(height = ring_z)
                difference() {
                    difference() {
                        square([ring_outer, ring_outer], center = true);
                        square([sq_size, sq_size], center = true);
                    }
                    // X축 양수방향 벽 제거
                    translate([sq_size / 2, -ring_outer / 2 - 0.1])
                        square([ring_outer / 2 - sq_size / 2 + 0.2, ring_outer + 0.2]);
                }
}

// ---------------- 립이 있는 면 (-X쪽 면) ----------------
module peltier_30_v1_face() {
    face_size = 30;   // 면의 가로/세로 (정사각형)
    housing_t = 1.2;  // 하우징 두께 (위/오른쪽 테두리)

    rib_w   = 1;      // 립 두께 (X방향)
    rib_len = 25.2;   // 립 길이 (Y방향)
    rib_z   = 8;      // 립 Z방향 돌출 높이

    left_margin  = 4.86;  // 안쪽 왼쪽 모서리 - 립 왼쪽 면 거리
    right_margin = 21.74; // 립 오른쪽 면 - 안쪽 오른쪽 모서리 거리

    // world Y축 음수방향 모서리에서 1.2mm 떨어진 5x1.2mm 관통 구멍 (housing_peltier_box_v2의
    // peltier_left_v2_face와 동일한 스펙)
    hole_w = 5;   // X방향
    hole_h = 1.2; // Y방향
    hole_gap = 1.2; // world -Y쪽 모서리 - 구멍 사이 거리

    // Y축: 립 위쪽 끝이 안쪽 위쪽 모서리(위쪽 테두리 안쪽)에 닿음
    y_inner_top    = face_size / 2 - housing_t;  // 안쪽 위쪽 테두리 (13.8)
    y_inner_bottom = -face_size / 2 + housing_t; // 안쪽 아래쪽 테두리 (-13.8)
    rib_bottom     = y_inner_top - rib_len;      // 립 아래쪽 끝
    gap_bottom_check = rib_bottom - y_inner_bottom; // 2.4mm 이어야 함

    rib_center_y = (y_inner_top + rib_bottom) / 2;
    rib_center_x = -face_size / 2 + housing_t + left_margin + rib_w / 2;
    x_total_check = left_margin + rib_w + right_margin; // 27.6mm 이어야 함

    echo("[Peltier30_v1] gap_bottom check =", gap_bottom_check, " (should be 2.4)");
    echo("[Peltier30_v1] x_total check =", x_total_check, " (should be", face_size - 2 * housing_t, ")");

    // 바닥판 (실제 3D, 두께 1.2mm). world Y축 음수방향 모서리에서 1.2mm 떨어진
    // 5x1.2mm 관통 구멍. 이 면은 world_y = -local_y로 매핑되므로(평면 기준 90도 회전),
    // world -Y 모서리는 로컬 +Y 모서리에 해당함.
    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([-hole_w / 2, face_size / 2 - hole_gap - hole_h, -0.1])
                cube([hole_w, hole_h, housing_t + 0.2]);
        }

    // 립 (실제 3D, 바닥판 위에 Z 깊이 rib_z 추가)
    color("SteelBlue")
        translate([0, 0, housing_t])
            linear_extrude(height = rib_z)
                translate([rib_center_x, rib_center_y])
                    square([rib_w, rib_len], center = true);
}

// ---------------- +Y쪽 면 (X축 양수방향 모서리에 구멍) ----------------
// 크기와 두께는 Peltier 면 / 립이 있는 면과 동일 (30x30mm, 1.2mm 두께).
module peltier30_y_pos_face() {
    face_size = 30;
    housing_t = 1.2;

    // X축 양수방향 모서리에서 X축 음수 방향으로 1.2mm 떨어진 5x1.2mm 관통 구멍
    hole_w = 1.2; // X방향
    hole_h = 5;   // Y방향
    hole_gap = 1.2; // +X쪽 모서리 - 구멍 사이 거리

    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([face_size / 2 - hole_gap - hole_w, -hole_h / 2, -0.1])
                cube([hole_w, hole_h, housing_t + 0.2]);
        }

    // 원기둥: 지름 1.5mm, 길이 10mm. -X쪽 면(립 있는 면)의 안쪽 면 기준 2.5mm 떨어진 위치.
    // world -Y 방향(캐비티 쪽)으로 돌출, 높이는 벽 중앙.
    pin_d = 1.5;
    pin_len = 10;
    pin_x = -face_size / 2 + housing_t + 2.5; // -11.3

    echo("[Peltier30YPos_v1] pin_x =", pin_x);

    color("SteelBlue")
        translate([pin_x, 0, housing_t])
            cylinder(d = pin_d, h = pin_len, $fn = 40);
}

// ---------------- +Z쪽 면 (윗면, 정가운데 10x10 정사각형 구멍) ----------------
// 크기와 두께는 Peltier 면 / 립이 있는 면과 동일 (30x30mm, 1.2mm 두께).
module peltier30_top_face() {
    face_size = 30;
    housing_t = 1.2;
    sq_size   = 10; // 정가운데 정사각형 구멍 한 변

    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([0, 0, -0.1])
                linear_extrude(height = housing_t + 0.2)
                    square([sq_size, sq_size], center = true);
        }
}

// ---------------- 조립 ----------------
peltier_v2_face();

// 립이 있는 면을 Peltier 면의 -X쪽 가장자리(x=-15)에 수직으로 세움.
// 평면 기준 90도 회전하여 로컬 X -> world Z(높이), 로컬 Y -> world Y(깊이, 부호 반전),
// 로컬 Z(립 돌출) -> world +X 로 대응됨.
translate([-15, 0, 15])
    rotate([0, 0, 90])
        rotate([90, 0, 0])
            rotate([0, 0, 90])
                peltier_30_v1_face();

// +Y쪽 면을 Peltier 면의 +Y쪽 가장자리(y=15)에 수직으로 세움.
translate([0, 15, 15])
    rotate([90, 0, 0])
        peltier30_y_pos_face();

// +Z쪽 면(윗면)을 Peltier 면 위(z=28.8~30)에 평행하게 덮음.
translate([0, 0, 28.8])
    peltier30_top_face();
