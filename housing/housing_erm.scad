// ============================================================
// ERM 쪽 바닥 면 - 평면도(XY, 하우징 내부에서 바닥을 내려다본 모습)
// ============================================================

face_size      = 25;   // 면의 가로/세로 (정사각형)
housing_t      = 1.2;  // 하우징 두께 (사방 테두리)
border_gap     = 0.1;  // 테두리 안쪽 빈 공간 (Peltier 쪽 면과 동일한 규칙 적용)
peltier_t      = 4;    // Peltier 고정 두께 (Z 깊이는 다른 면 설계 시 결정)
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

frame_inner_w = face_size - 2 * housing_t;           // 테두리 프레임 안쪽 폭 (22.6mm)
inner_w       = face_size - 2 * (housing_t + border_gap); // 밴드 폭: 테두리+갭 안쪽 (22.4mm)

echo("y_bottom check =", y_bottom, " (should be", -face_size / 2, ")");
echo("ERM ring center_y =", erm_center_y, " inner_r =", erm_inner_r, " outer_r =", erm_outer_r);

// --- 참고용 2D 레이아웃 (Z 깊이 미정 영역, 반투명 표시) ---
module face_reference_2d() {
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

    // Peltier 고정 영역 (Z는 다른 면 설계 시 결정, 바닥판 위에 참고 표시)
    color("orange", 0.3)
        translate([0, 0, housing_t])
            linear_extrude(height = guide_h)
                translate([0, y1 - peltier_t / 2])
                    square([inner_w, peltier_t], center = true);

    // 모터 드라이버 고정 영역 (Z는 다른 면 설계 시 결정, 바닥판 위에 참고 표시)
    color("cyan", 0.3)
        translate([0, 0, housing_t])
            linear_extrude(height = guide_h)
                translate([0, y7 - motor_driver_t / 2])
                    square([inner_w, motor_driver_t], center = true);
}

// ERM 링에서 잘라낼 구간: 9시 방향(180도) 기준 45도
erm_gap_center_deg = 180;
erm_gap_width_deg  = 45;
erm_gap_r          = erm_outer_r + 1; // 확실히 잘리도록 여유

// --- ERM 고정 링 (실제 3D, 바닥판 위에 Z 깊이 2.6mm 추가, 9시 방향 45도 절개) ---
module erm_ring() {
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

face_reference_2d();
erm_ring();
