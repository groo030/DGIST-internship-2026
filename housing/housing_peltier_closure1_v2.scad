// ============================================================
// 하우징 Peltier v2 - housing_peltier_closure1_v2 (별도 부품)
// housing_erm_closure1_v2를 그대로 가져옴
// ============================================================

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

housing_peltier_closure1_v2();
