// ============================================================
// 하우징 Peltier v2 조립
// Peltier 면(바닥): 25x25mm, 사각 링(프레임)이 바닥판 위로 3.8mm 돌출, 안쪽은 관통 구멍
// -X쪽 면: Peltier 면의 -X쪽 가장자리에 수직으로 세움 (평면 기준 90도 회전 후 부착), 리브 5mm 돌출
// +Y쪽 면 / +Z쪽 면(윗면): 패턴 없는 평판, 크기/두께는 나머지 두 면과 동일
// ============================================================

// ---------------- Peltier 면 (바닥) ----------------
module peltier_v2_face() {
    face_size = 25;   // 면의 가로/세로 (정사각형)
    housing_t = 1.2;  // 하우징 두께 (사방 테두리)

    frame_w = 1.28;   // 사각 링(프레임) 벽 두께
    sq_size = 20.04;  // 프레임 안쪽 정사각형 (Peltier 안착 공간, 관통 구멍)
    ring_z  = 3.8;    // 사각 링 Z방향 돌출 높이

    inner_size = face_size - 2 * housing_t; // 22.6mm (하우징 안쪽 치수)
    ring_outer = sq_size + 2 * frame_w;     // 22.6mm (하우징 안쪽 치수와 동일해야 함)

    echo("[Peltier_v2] ring_outer check =", ring_outer, " (should be", inner_size, ")");

    // 바닥판 (실제 3D, 두께 1.2mm). 사각 링 안쪽(20.04x20.04)은 관통 구멍.
    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([0, 0, -0.1])
                linear_extrude(height = housing_t + 0.2)
                    square([sq_size, sq_size], center = true);
        }

    // 사각 링(프레임): 하우징 안쪽 경계에 정확히 맞닿아 있고, 중앙에 20.04x20.04 정사각형
    // 안착 공간이 생김. 바닥판 위로 ring_z만큼 돌출 (높이 미확정, 참고용).
    color("SteelBlue")
        translate([0, 0, housing_t])
            linear_extrude(height = ring_z)
                difference() {
                    square([ring_outer, ring_outer], center = true);
                    square([sq_size, sq_size], center = true);
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

    left_margin  = 5.56;  // 안쪽 왼쪽 모서리 - 리브 왼쪽 면 거리
    right_margin = 16.04; // 리브 오른쪽 면 - 안쪽 오른쪽 모서리 거리

    // Y축: 리브 위쪽 끝이 안쪽 위쪽 모서리(위쪽 테두리 안쪽)에 닿음
    y_inner_top    = face_size / 2 - housing_t;  // 안쪽 위쪽 테두리 (11.3)
    y_inner_bottom = -face_size / 2 + housing_t; // 안쪽 아래쪽 테두리 (-11.3)
    rib_bottom     = y_inner_top - rib_len;      // 리브 아래쪽 끝
    gap_bottom_check = rib_bottom - y_inner_bottom; // 4.1mm 이어야 함

    rib_center_y = (y_inner_top + rib_bottom) / 2;
    rib_center_x = -face_size / 2 + housing_t + left_margin + rib_w / 2;
    x_total_check = left_margin + rib_w + right_margin; // 22.6mm 이어야 함

    echo("[PeltierLeft_v2] gap_bottom check =", gap_bottom_check, " (should be 4.1)");
    echo("[PeltierLeft_v2] x_total check =", x_total_check, " (should be", face_size - 2 * housing_t, ")");

    // 바닥판 (실제 3D, 두께 1.2mm). -Y쪽 모서리에서 1.2mm 떨어진 5x1.2mm 관통 구멍.
    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([-hole_w / 2, -face_size / 2 + hole_gap, -0.1])
                cube([hole_w, hole_h, housing_t + 0.2]);
        }

    // 리브 (실제 3D, 바닥판 위에 Z 깊이 rib_z 추가, 높이 미확정)
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

// ---------------- housing_peltier_closure1_v2 (별도 부품) ----------------
module housing_peltier_closure1_v2() {
    plate_w = 22.56; // 가로
    plate_h = 21.36; // 세로
    plate_t = 1.2;   // 판재 두께

    // 돌출 직육면체: 가로 4.96mm, 높이(Z) 1.16mm.
    // 세로(Y)는 +Y쪽 가장자리 기준으로 면 위에 1.2mm + 바깥으로 1.2mm = 총 2.4mm
    tab_w        = 4.96; // 가로
    tab_protrude = 1.2;  // 3D 기준 +Y 방향으로 면 바깥으로 튀어나오는 길이
    tab_overlap  = 1.2;  // 면 위에 걸쳐있는 길이 (+Y쪽 가장자리에서 안쪽으로)
    tab_len      = tab_protrude + tab_overlap; // 세로 전체 길이 (2.4mm)
    tab_z        = 1;    // 돌출부가 판재 위로 추가로 튀어나오는 두께(높이)

    // -Y쪽 나사 보스: 구멍은 Y축 방향으로 관통, X는 정중앙(0).
    // 안쪽 구멍 지름 2mm, 둘러싼 두께 2mm -> 바깥지름 6mm. 가장자리에서 안쪽으로 1.2mm.
    boss_screw_d = 2;
    boss_wall_t  = 2;
    boss_d       = boss_screw_d + 2 * boss_wall_t; // 6mm
    boss_len     = 1.2; // -Y 가장자리에서 안쪽(+Y)으로 들어간 길이
    boss_z       = plate_t + boss_d / 2 - 2; // 구멍 중심 기준 Z축 음수 방향으로 2mm 내림

    echo("[PeltierClosure1] tab_w =", tab_w, " tab_len =", tab_len, " tab_z =", tab_z);
    echo("[PeltierClosure1] boss_d =", boss_d, " boss_len =", boss_len);

    difference() {
        union() {
            // 메인 평판
            color("gray")
                linear_extrude(height = plate_t)
                    square([plate_w, plate_h], center = true);

            // 돌출 직육면체 (4.96mm x 2.4mm x 1.16mm). +Y쪽 가장자리를 기준으로
            // 안쪽(면 위)으로 1.2mm, 바깥쪽(3D +Y 방향)으로 1.2mm 걸쳐 있음.
            color("SteelBlue")
                translate([0, plate_h / 2 - tab_overlap + tab_len / 2, plate_t])
                    linear_extrude(height = tab_z)
                        square([tab_w, tab_len], center = true);

            // -Y쪽 나사 보스 (바깥지름 6mm), 가장자리에서 안쪽으로 1.2mm
            color("SteelBlue")
                translate([0, -plate_h / 2 + boss_len, boss_z])
                    rotate([90, 0, 0])
                        cylinder(d = boss_d, h = boss_len, $fn = 60);
        }

        // 나사 구멍 (Y방향 관통, 보스를 지나 여유 있게)
        translate([0, -plate_h / 2 + boss_len + 0.1, boss_z])
            rotate([90, 0, 0])
                cylinder(d = boss_screw_d, h = boss_len + 0.2, $fn = 40);

        // 보스가 판재 아래(z<0)로 튀어나온 부분 제거
        translate([-plate_w, -plate_h, -100])
            cube([plate_w * 2, plate_h * 2, 100]);
    }
}

// ---------------- housing_peltier_closure2_v2 (별도 부품) ----------------
module housing_peltier_closure2_v2() {
    plate_w = 22.56; // 가로
    plate_h = 23.8;  // 세로 (25 -> 1.2mm 감소)
    plate_t = 1.2;   // 판재 두께

    // 돌출 탭: housing_peltier_closure1_v2와 동일한 구조.
    // 가로 4.92mm. 세로(Y)는 +Y쪽 가장자리 기준 면 위에 1.2mm 걸치고(overlap)
    // 바깥으로 1.2mm 튀어나옴(protrude) = 총 2.4mm. 판재 위에 tab_z만큼 돌출.
    tab_w        = 4.92; // 가로 (4.96 -> 4.92)
    tab_protrude = 1.2;  // 3D 기준 +Y 방향으로 면 바깥으로 튀어나오는 길이
    tab_overlap  = 1.2;  // 면 위에 걸쳐있는 길이 (+Y쪽 가장자리에서 안쪽으로)
    tab_len      = tab_protrude + tab_overlap; // 세로 전체 길이 (2.4mm)
    tab_z        = 1;    // 돌출부가 판재 위로 추가로 튀어나오는 두께(높이)

    // 나사 구멍: 정사각형 중심(=판재 중심)에서 Y축 음수 방향으로 10.3mm 떨어진 위치.
    // 보스 없이 Z축 방향(판재를 관통)으로 뚫림.
    screw_d = 2;
    screw_y = -10.3;

    echo("[PeltierClosure2] tab_w =", tab_w, " tab_len =", tab_len, " tab_z =", tab_z);
    echo("[PeltierClosure2] screw_y =", screw_y);

    difference() {
        union() {
            // 메인 평판 (정사각형 구멍 없이 막힘)
            color("gray")
                linear_extrude(height = plate_t)
                    square([plate_w, plate_h], center = true);

            // 윗변 돌출 탭 (실제 3D, 판재 위에 Z 깊이 tab_z 추가), 윗변 바깥쪽으로 튀어나옴.
            color("SteelBlue")
                translate([0, plate_h / 2 - tab_overlap + tab_len / 2, plate_t])
                    linear_extrude(height = tab_z)
                        square([tab_w, tab_len], center = true);
        }

        // 나사 구멍 (Z방향 관통), 정사각형 중심에서 Y축 음수방향 10.3mm
        translate([0, screw_y, -0.1])
            cylinder(d = screw_d, h = plate_t + 0.2, $fn = 40);
    }
}

// ---------------- 조립 ----------------
peltier_v2_face();

// -X쪽 면을 Peltier 면의 -X쪽 가장자리(x=-12.5)에 수직으로 세움.
// 로컬 Y -> world Z, 로컬 Z(리브 돌출) -> world +X
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

// closure1/closure2는 조립체에 붙이지 않고 옆으로 떨어뜨려서 배치
translate([-50, 0, 0])
    housing_peltier_closure1_v2();

translate([-90, 0, 0])
    housing_peltier_closure2_v2();
