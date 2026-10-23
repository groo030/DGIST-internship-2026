// ============================================================
// 하우징 Peltier v2 - box 조립 (Peltier 면 + -X쪽 면 + +Y쪽 면 + +Z쪽 면)
// Peltier 면(바닥): 25x25mm, 사각 링(프레임)이 바닥판 위로 3.8mm 돌출, 안쪽은 관통 구멍
// -X쪽 면: Peltier 면의 -X쪽 가장자리에 수직으로 세움 (평면 기준 90도 회전 후 부착), 리브 5mm 돌출
// +Y쪽 면 / +Z쪽 면(윗면): 패턴 없는 평판, 크기/두께는 나머지 두 면과 동일
//
// closure1/closure2는 housing_peltier_closure1_v2.scad / housing_peltier_closure2_v2.scad로 분리됨.
// ============================================================

// ---------------- Peltier 면 (바닥) ----------------
module peltier_v2_face() {
    face_size = 25;   // 면의 가로/세로 (정사각형)
    housing_t = 1.2;  // 하우징 두께 (사방 테두리)

    frame_w = 1.28;   // 사각 링(프레임) 벽 두께 (변경 없음)
    sq_size = 20.08;  // 프레임 안쪽 정사각형 (Peltier 안착 공간, 관통 구멍) - 20.04에서 0.04mm 증가
    ring_z  = 3.8;    // 사각 링 Z방향 돌출 높이

    inner_size = face_size - 2 * housing_t; // 22.6mm (하우징 안쪽 치수)
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

// ---------------- -X쪽 면 (리브 있는 면) ----------------
module peltier_left_v2_face() {
    face_size = 25;   // 면의 가로/세로 (정사각형, Peltier 면과 동일)
    housing_t = 1.2;  // 하우징 두께 (위/아래/좌/우 테두리)

    rib_w   = 1;      // 리브 두께 (X방향)
    rib_len = 18.5;   // 리브 길이 (Y방향)
    rib_z   = 5;      // 리브 Z방향 돌출 높이

    // Y축 음수방향 모서리에서 Y축 양수 방향으로 1.2mm 떨어진 5x1.2mm 관통 구멍
    hole_w = 5;   // X방향
    hole_h = 1.2; // Y방향
    hole_gap = 1.2; // -Y쪽 모서리 - 구멍 사이 거리

    // 리브를 Peltier 면(바닥, world Z=0)에서 world Z축 양수방향으로 5.6mm 위치(중심)로 이동.
    // 리브 아래쪽 면(world Z = rib_world_z - rib_w/2)이 바닥에서 5.1mm 떨어지도록 함.
    // 이 벽의 부착 변환에서는 로컬 X가 world Z(높이)에 대응하므로,
    // rib_center_x = face_size/2 - rib_world_z 로 계산.
    rib_world_z = 5.6; // Peltier 면 기준 world Z 위치 (리브 중심)

    // Y축: 리브 위쪽 끝이 안쪽 위쪽 모서리(위쪽 테두리 안쪽)에 닿음
    y_inner_top    = face_size / 2 - housing_t;  // 안쪽 위쪽 테두리 (11.3)
    y_inner_bottom = -face_size / 2 + housing_t; // 안쪽 아래쪽 테두리 (-11.3)
    rib_bottom     = y_inner_top - rib_len;      // 리브 아래쪽 끝
    gap_bottom_check = rib_bottom - y_inner_bottom; // 4.1mm 이어야 함

    rib_center_y = (y_inner_top + rib_bottom) / 2;
    rib_center_x = face_size / 2 - rib_world_z;

    // 리브의 world Z 방향 위/아래 면과 각 끝(바닥 Z=0, 벽 꼭대기 Z=face_size)까지의 거리
    rib_z_bottom_face = rib_world_z - rib_w / 2; // 바닥까지 거리 (5.1이어야 함)
    rib_z_top_face    = rib_world_z + rib_w / 2; // 리브 위쪽 면 world Z 위치
    rib_z_top_gap     = face_size - rib_z_top_face; // 반대쪽(벽 꼭대기)까지 거리

    echo("[PeltierLeft_v2] gap_bottom check =", gap_bottom_check, " (should be 4.1)");
    echo("[PeltierLeft_v2] rib world Z =", face_size / 2 - rib_center_x, " (should be", rib_world_z, ")");
    echo("[PeltierLeft_v2] rib_z_bottom_face =", rib_z_bottom_face, " (should be 5.1)");
    echo("[PeltierLeft_v2] rib_z_top_gap (반대쪽 면 간격) =", rib_z_top_gap);

    // 바닥판 (실제 3D, 두께 1.2mm). -Y쪽 모서리에서 1.2mm 떨어진 5x1.2mm 관통 구멍.
    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([-hole_w / 2, -face_size / 2 + hole_gap, -0.1])
                cube([hole_w, hole_h, housing_t + 0.2]);
        }

    // 리브 (실제 3D, 바닥판 위에 Z 깊이 rib_z 추가)
    color("SteelBlue")
        translate([0, 0, housing_t])
            linear_extrude(height = rib_z)
                translate([rib_center_x, rib_center_y])
                    square([rib_w, rib_len], center = true);
}

// ---------------- +Y쪽 면 (X축 양수방향 모서리에 구멍) ----------------
// 크기와 두께는 Peltier 면 / -X쪽 면과 동일 (25x25mm, 1.2mm 두께).
module peltier_y_pos_v2_face() {
    face_size = 25;
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

    // 원기둥: 지름 1.5mm, 길이 10mm. -X쪽 면(립 있는 면)의 안쪽 면 기준 3.05mm 떨어진 위치.
    // world -Y 방향(캐비티 쪽)으로 돌출, 높이는 벽 중앙.
    pin_d = 1.5;
    pin_len = 10;
    pin_x = -face_size / 2 + housing_t + 3.05; // -8.25

    echo("[PeltierYPos_v2] pin_x =", pin_x);

    color("SteelBlue")
        translate([pin_x, 0, housing_t])
            cylinder(d = pin_d, h = pin_len, $fn = 40);
}

// ---------------- +Z쪽 면 (윗면, 정가운데 10x10 정사각형 구멍) ----------------
// 크기와 두께는 Peltier 면 / -X쪽 면과 동일 (25x25mm, 1.2mm 두께).
module peltier_top_v2_face() {
    face_size = 25;
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

// -X쪽 면을 Peltier 면의 -X쪽 가장자리(x=-12.5)에 수직으로 세움.
// 이 변환(rotate 90/90/-90 조합)에서는 로컬 X -> world Z(높이), 로컬 Y -> world Y(깊이),
// 로컬 Z(리브 돌출) -> world +X 로 대응됨.
// left_v2_face(housing_erm_v2)와 동일한 부착 방식: 평면 기준 90도 회전 후 부착.
translate([-12.5, 0, 12.5])
    rotate([0, 0, 90])
        rotate([90, 0, 0])
            rotate([0, 0, -90])
                peltier_left_v2_face();

// +Y쪽 면을 Peltier 면의 +Y쪽 가장자리(y=12.5)에 수직으로 세움.
translate([0, 12.5, 12.5])
    rotate([90, 0, 0])
        peltier_y_pos_v2_face();

// +Z쪽 면(윗면)을 Peltier 면 위(z=23.8~25)에 평행하게 덮음.
translate([0, 0, 23.8])
    peltier_top_v2_face();
