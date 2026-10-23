// ============================================================
// hat.scad
// 80mm x 80mm 정사각형 판재, 두께 1.2mm.
// 판재 정중앙에 55.04mm x 55.04mm 정사각형 관통 구멍.
// 구멍 가장자리에 벽(사각 링)을 Z축 방향 위로 2mm 높이, 1.2mm 두께로 세움.
// ============================================================

module hat() {
    plate_size = 80;   // 바깥 정사각형 한 변 (70 -> 80)
    plate_t    = 1.2;  // 판재 두께

    hole_size  = 55.04; // 중앙 정사각형 구멍 한 변

    wall_t = 1.2; // 구멍 가장자리 벽 두께
    wall_z = 2;   // 구멍 가장자리 벽 높이
    wall_outer = hole_size + 2 * wall_t; // 벽 바깥쪽 치수

    color("gray")
        difference() {
            linear_extrude(height = plate_t)
                square([plate_size, plate_size], center = true);
            translate([0, 0, -0.1])
                linear_extrude(height = plate_t + 0.2)
                    square([hole_size, hole_size], center = true);
        }

    // 구멍 가장자리 벽 (사각 링): 안쪽 면이 구멍 경계에 맞닿고, 판재 위로 wall_z만큼 돌출
    color("SteelBlue")
        translate([0, 0, plate_t])
            linear_extrude(height = wall_z)
                difference() {
                    square([wall_outer, wall_outer], center = true);
                    square([hole_size, hole_size], center = true);
                }

    // Z축 음수방향 ㄷ자 브라켓: 정사각형 정중앙 기준 70x72mm (X x Y, 60x60에서 변경),
    // 두께 1.2mm, 높이 20mm.
    // X축 양수방향 벽이 열려있는 "ㄷ"자 형태 (다른 사각 링들과 동일하게 +X쪽을 열어둠 - 확인 필요).
    bracket_outer_x = 70;
    bracket_outer_y = 72;
    bracket_t       = 1.2;
    bracket_z       = 20;
    bracket_inner_x = bracket_outer_x - 2 * bracket_t;
    bracket_inner_y = bracket_outer_y - 2 * bracket_t;

    color("SteelBlue")
        translate([0, 0, -bracket_z])
            linear_extrude(height = bracket_z)
                difference() {
                    difference() {
                        square([bracket_outer_x, bracket_outer_y], center = true);
                        square([bracket_inner_x, bracket_inner_y], center = true);
                    }
                    // X축 양수방향 벽 제거
                    translate([bracket_inner_x / 2, -bracket_outer_y / 2 - 0.1])
                        square([bracket_outer_x / 2 - bracket_inner_x / 2 + 0.2, bracket_outer_y + 0.2]);
                }
}

hat();
