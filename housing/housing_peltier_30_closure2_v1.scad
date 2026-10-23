// ============================================================
// 하우징 Peltier 30x30 - housing_peltier_closure2_v2 (별도 부품)
// housing_peltier_closure2_v2에서 판재 크기를 가로/세로 각 5mm씩 키움 (탭 크기는 동일).
// 나사 구멍은 Y축 음수방향으로 2.5mm 추가 이동.
// ============================================================

module housing_peltier_closure2_v2() {
    plate_w = 27.56; // 가로 (22.56 -> 5mm 증가)
    plate_h = 28.8;  // 세로 (23.8 -> 5mm 증가)
    plate_t = 1.2;   // 판재 두께

    // 돌출 탭: housing_peltier_closure1_v2와 동일한 구조.
    // 가로 4.92mm. 세로(Y)는 +Y쪽 가장자리 기준 면 위에 1.2mm 걸치고(overlap)
    // 바깥으로 1.2mm 튀어나옴(protrude) = 총 2.4mm. 판재 위에 tab_z만큼 돌출.
    tab_w        = 4.92; // 가로
    tab_protrude = 1.2;  // 3D 기준 +Y 방향으로 면 바깥으로 튀어나오는 길이
    tab_overlap  = 1.2;  // 면 위에 걸쳐있는 길이 (+Y쪽 가장자리에서 안쪽으로)
    tab_len      = tab_protrude + tab_overlap; // 세로 전체 길이 (2.4mm)
    tab_z        = 1;    // 돌출부가 판재 위로 추가로 튀어나오는 두께(높이)

    // 나사 구멍: 판재 중심에서 Y축 음수 방향으로 10.3mm + 2.5mm = 12.8mm 떨어진 위치.
    // 보스 없이 Z방향(판재를 관통)으로 뚫림.
    screw_d = 2;
    screw_y = -12.8;

    echo("[PeltierClosure2] tab_w =", tab_w, " tab_len =", tab_len, " tab_z =", tab_z);
    echo("[PeltierClosure2] screw_y =", screw_y);

    difference() {
        union() {
            // 메인 평판
            color("gray")
                linear_extrude(height = plate_t)
                    square([plate_w, plate_h], center = true);

            // 윗변 돌출 탭 (실제 3D, 판재 위에 Z 깊이 tab_z 추가), 윗변 바깥쪽으로 튀어나옴.
            color("SteelBlue")
                translate([0, plate_h / 2 - tab_overlap + tab_len / 2, plate_t])
                    linear_extrude(height = tab_z)
                        square([tab_w, tab_len], center = true);
        }

        // 나사 구멍 (Z방향 관통)
        translate([0, screw_y, -0.1])
            cylinder(d = screw_d, h = plate_t + 0.2, $fn = 40);
    }
}

housing_peltier_closure2_v2();
