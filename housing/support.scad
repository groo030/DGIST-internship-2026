// ============================================================
// support.scad
// "ㅁ"자 사각 프레임 (4면 모두 닫힌 링).
// 안쪽 기준 55.04mm x 60.04mm, 벽 두께 1.2mm, 높이(Z) 10mm.
// ============================================================

module support() {
    inner_w = 55.04; // 안쪽 가로(X)
    inner_d = 60.04; // 안쪽 세로(Y)
    wall_t  = 1.2;   // 벽 두께 (안쪽 기준 바깥으로)
    z       = 10;    // 높이(Z)

    outer_w = inner_w + 2 * wall_t;
    outer_d = inner_d + 2 * wall_t;

    color("SteelBlue")
        linear_extrude(height = z)
            difference() {
                square([outer_w, outer_d], center = true);
                square([inner_w, inner_d], center = true);
            }
}

support();
