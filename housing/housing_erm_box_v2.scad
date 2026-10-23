// ============================================================
// 하우징 ERM v2 - box 조립 (ERM 면 + 왼쪽/오른쪽/+Y쪽 면)
// ERM 면(2번째 사진, 링): 바닥 (XY 평면, world Z=0)
// 왼쪽 면(1번째 사진): ERM 면의 -X쪽 가장자리에 수직으로 세움
// 오른쪽 면(3번째 사진): ERM 면의 +X쪽 가장자리에 수직으로 세움
//
// 클로져1/클로져2는 housing_erm_closure1_v2.scad / housing_erm_closure2_v2.scad로 분리됨.
// ============================================================

// ---------------- ERM 면 (2번째 사진, 바닥) ----------------
module erm_v2_face() {
    face_size  = 25;   // 면의 가로/세로 (정사각형)
    housing_t  = 1.2;  // 하우징 두께 (사방 테두리)

    ring_margin = 5.05; // 안쪽 테두리(22.6mm 사각형) 기준, 링 위/좌/우 여백
    ring_wall   = 1.23; // 링 벽 두께
    ring_id     = 10.04; // 링 안지름
    ring_r_in   = ring_id / 2;
    ring_r_out  = ring_r_in + ring_wall;

    ring_z      = 2.6;  // 링의 Z방향 깊이 (미확인, 기존 ERM 링과 동일 값으로 가정)

    // 직사각형 구멍 (돌출이 아니라 관통 구멍). 안쪽 모서리(테두리 안쪽 경계선)에 닿은 상태로
    // 거기서부터 안쪽(캐비티 방향)으로 1.2mm 파고드는 형태 - 테두리를 관통하는 게 아님.
    // 링의 뚫린 부분(-Y 방향)에 맞춰 -Y쪽 안쪽 모서리 기준으로 배치
    rect_w = 5;   // X방향 (링 중심과 동일선상)
    rect_h = 1.2; // Y방향 (안쪽 모서리에서 캐비티 쪽으로)

    // ERM 링에서 잘라낼 구간: 3D에서 Y축 음수 방향(270도) 기준 45도
    // (housing_erm.scad 참고)
    erm_gap_center_deg = 270;
    erm_gap_width_deg  = 45;
    erm_gap_r           = ring_r_out + 1; // 확실히 잘리도록 여유

    inner_size = face_size - 2 * housing_t; // 22.6mm

    echo("[ERM_v2] ring_r_out check =", ring_r_out,
         " (inner_size/2 - ring_margin =", inner_size / 2 - ring_margin, ")");

    // 바닥판 (면 전체, 실제 3D, 두께 1.2mm). -Y쪽 안쪽 모서리에 닿고 캐비티 쪽으로
    // 1.2mm 파고드는 5mm x 1.2mm 관통 구멍 (테두리 자체는 관통하지 않음).
    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([-rect_w / 2, -face_size / 2 + housing_t, -0.1])
                cube([rect_w, rect_h, housing_t + 0.2]);
        }

    // ERM 고정 링 (실제 3D, 바닥판 위에 Z 깊이 ring_z 추가), 중앙 정렬, 9시 방향 45도 절개
    color("SteelBlue")
        translate([0, 0, housing_t])
            linear_extrude(height = ring_z)
                difference() {
                    difference() {
                        circle(r = ring_r_out, $fn = 100);
                        circle(r = ring_r_in, $fn = 100);
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

// ---------------- 왼쪽 면 (1번째 사진) ----------------
module left_v2_face() {
    face_size  = 25;    // 면의 가로/세로 (정사각형)
    housing_t  = 1.2;   // 하우징 두께 (위/아래 테두리)

    bracket_t  = 1;      // 브라켓 두께 (X방향)
    bracket_len = 22;    // 브라켓 길이 (Y방향)
    bracket_z  = 4;      // 브라켓 높이 (Z방향 돌출)

    open_w     = 17.04;  // 브라켓 사이 뚫린 공간 가로 폭
    edge_margin = 2.98;  // 브라켓 - 바깥쪽 모서리 거리

    // Y축: 브라켓 위쪽 끝이 안쪽 모서리(위쪽 테두리 안쪽)에 닿음
    y_inner_top = face_size / 2 - housing_t;      // 안쪽 위쪽 테두리 (11.3)
    y_bracket_bottom = y_inner_top - bracket_len; // 브라켓 아래쪽 끝
    y_inner_bottom = -face_size / 2 + housing_t;  // 안쪽 아래쪽 테두리 (-11.3)
    gap_bottom_check = y_bracket_bottom - y_inner_bottom; // 0.6mm 이어야 함

    bracket_center_y = (y_inner_top + y_bracket_bottom) / 2;

    // X축: 브라켓 2개 (부착 후 world Z축 방향으로 대응 - 로컬 X가 world Z에 매핑됨).
    // right_bracket(로컬 X 양수 -> world Z 음수 방향)을 world Z 음수 방향으로 추가 이동하여
    // 두 브라켓 사이 간격(world Z 방향)을 원래 17.04mm에서 18mm로 늘림 (0.96mm 이동).
    // world_z = hs - local_x 매핑이므로, world -Z로 이동 = local_x 증가.
    z_neg_bracket_shift = 0.96;

    left_bracket_center_x  = -face_size / 2 + edge_margin + bracket_t / 2;
    right_bracket_center_x =  face_size / 2 - edge_margin - bracket_t / 2 + z_neg_bracket_shift;
    x_total_check = edge_margin * 2 + bracket_t * 2 + open_w;
    gap_z_check = open_w + z_neg_bracket_shift; // 브라켓 사이 world Z 간격, 18이어야 함

    echo("[Left_v2] gap_bottom check =", gap_bottom_check, " (should be 0.6)");
    echo("[Left_v2] x_total check =", x_total_check, " (should be", face_size, ")");
    echo("[Left_v2] right_bracket_center_x =", right_bracket_center_x);
    echo("[Left_v2] gap_z_check =", gap_z_check, " (should be 18)");

    // 바닥판 (면 전체, 실제 3D, 두께 1.2mm)
    color("gray")
        linear_extrude(height = housing_t)
            square([face_size, face_size], center = true);

    // 브라켓 2개 (실제 3D, 바닥판 위에 Z 깊이 bracket_z 추가)
    color("SteelBlue")
        translate([0, 0, housing_t])
            linear_extrude(height = bracket_z) {
                translate([left_bracket_center_x, bracket_center_y])
                    square([bracket_t, bracket_len], center = true);
                translate([right_bracket_center_x, bracket_center_y])
                    square([bracket_t, bracket_len], center = true);
            }
}

// ---------------- 오른쪽 면 (3번째 사진) ----------------
module right_v2_face() {
    face_size  = 25;    // 면의 가로/세로 (정사각형)
    housing_t  = 1.2;   // 하우징 두께 (위/아래 테두리)

    bracket_t  = 1;      // 브라켓 두께 (X방향)
    bracket_len = 18.5;  // 브라켓 길이 (Y방향)
    bracket_z  = 3;      // 브라켓 높이 (Z방향 돌출)

    open_w     = 16.04;  // 브라켓 사이 뚫린 공간 가로 폭
    edge_margin = 3.48;  // 브라켓 - 바깥쪽 모서리 거리

    // Y축: 브라켓 위쪽 끝이 안쪽 모서리(위쪽 테두리 안쪽)에 닿음
    y_inner_top = face_size / 2 - housing_t;      // 안쪽 위쪽 테두리 (11.3)
    y_bracket_bottom = y_inner_top - bracket_len; // 브라켓 아래쪽 끝
    y_inner_bottom = -face_size / 2 + housing_t;  // 안쪽 아래쪽 테두리 (-11.3)
    gap_bottom_check = y_bracket_bottom - y_inner_bottom; // 4.1mm 이어야 함

    bracket_center_y = (y_inner_top + y_bracket_bottom) / 2;

    // X축: 브라켓 2개
    left_bracket_center_x  = -face_size / 2 + edge_margin + bracket_t / 2;
    right_bracket_center_x =  face_size / 2 - edge_margin - bracket_t / 2;
    x_total_check = edge_margin * 2 + bracket_t * 2 + open_w;

    echo("[Right_v2] gap_bottom check =", gap_bottom_check, " (should be 4.1)");
    echo("[Right_v2] x_total check =", x_total_check, " (should be", face_size, ")");

    // 바닥판 (면 전체, 실제 3D, 두께 1.2mm)
    color("gray")
        linear_extrude(height = housing_t)
            square([face_size, face_size], center = true);

    // 브라켓 2개 (실제 3D, 바닥판 위에 Z 깊이 bracket_z 추가)
    color("SteelBlue")
        translate([0, 0, housing_t])
            linear_extrude(height = bracket_z) {
                translate([left_bracket_center_x, bracket_center_y])
                    square([bracket_t, bracket_len], center = true);
                translate([right_bracket_center_x, bracket_center_y])
                    square([bracket_t, bracket_len], center = true);
            }
}

// ---------------- +Y쪽 면 ----------------
// 1.2mm 두께 벽. 높이는 왼쪽/오른쪽 면과 동일(25mm).
// world Z축 양수 방향 모서리(local y=+12.5)에서 1.2mm 아래에 5mm x 1.2mm 관통 구멍.
module y_pos_v2_face() {
    face_size = 25;   // 면의 가로/세로 (정사각형, 왼쪽/오른쪽 면과 동일)
    housing_t = 1.2;  // 하우징 두께 (벽 두께)

    rect_w = 5;   // X방향 (가운데 정렬)
    rect_h = 1.2; // Y방향 (world Z 양수 모서리에서 1.2mm 아래로 내려간 위치)

    color("gray")
        difference() {
            linear_extrude(height = housing_t)
                square([face_size, face_size], center = true);
            translate([-rect_w / 2, face_size / 2 - rect_h - 1.2, -0.1])
                cube([rect_w, rect_h, housing_t + 0.2]);
        }

    // 원기둥 2개: 지름 1.5mm, 길이 10mm. 벽 안쪽 면에서 world Y축 음수 방향(캐비티 쪽)으로
    // 돌출. 로컬 Z가 world Y(깊이)에 대응하므로 housing_t 위치에서 시작해 10mm 돌출시키면
    // world -Y 방향으로 뻗어나감. 높이는 벽 중앙(world Z=12.5, 로컬 y=0).
    // pin1: 간격이 더 넓은 브라켓 면(-X쪽, left_v2_face) 기준 4.5mm 위치에서
    //       X축 양수 방향으로 1.25mm 추가 이동 (-8 -> -6.75, 서로 가까워지는 방향)
    // pin2: 간격이 더 좁은 브라켓 면(+X쪽, right_v2_face) 기준 3.5mm 위치에서
    //       X축 음수 방향으로 1.25mm 추가 이동 (9 -> 7.75) - pin1과 반대 방향
    pin_d = 1.5;
    pin_len = 10;
    pin1_x = -face_size / 2 + 4.5 + 1.25; // -6.75
    pin2_x =  face_size / 2 - 3.5 - 1.25; //  7.75

    echo("[YPos_v2] pin1_x =", pin1_x, " pin2_x =", pin2_x);

    color("SteelBlue") {
        translate([pin1_x, 0, housing_t])
            cylinder(d = pin_d, h = pin_len, $fn = 40);
        translate([pin2_x, 0, housing_t])
            cylinder(d = pin_d, h = pin_len, $fn = 40);
    }
}

// ---------------- 조립 ----------------
erm_v2_face();

// 왼쪽 면을 ERM 면의 -X쪽 가장자리(x=-12.5)에 수직으로 세움.
// 로컬 Y -> world Z, 로컬 Z(브라켓 돌출) -> world +X
// 면 안의 패턴(브라켓)은 제자리에서 90도 회전 (반대 방향: 브라켓이 닿는 쪽이 world +Y를 향하도록).
translate([-12.5, 0, 12.5])
    rotate([0, 0, 90])
        rotate([90, 0, 0])
            rotate([0, 0, -90])
                left_v2_face();

// 오른쪽 면을 ERM 면의 +X쪽 가장자리(x=12.5)에 수직으로 세움.
// 로컬 Y -> world Z, 로컬 Z(브라켓 돌출) -> world -X
// 면 안의 패턴(브라켓)은 제자리에서 90도 회전.
translate([12.5, 0, 12.5])
    rotate([0, 0, -90])
        rotate([90, 0, 0])
            rotate([0, 0, 90])
                right_v2_face();

// +Y쪽 면을 ERM 면의 +Y쪽 가장자리(y=12.5)에 수직으로 세움. 높이는 왼쪽/오른쪽 면과 동일(25mm).
translate([0, 12.5, 12.5])
    rotate([90, 0, 0])
        y_pos_v2_face();
