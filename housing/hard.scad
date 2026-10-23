// ============================================================
// hard.scad
// "ㅁ"자 사각 프레임 (4면 모두 닫힌 링).
// 바깥 기준 72mm(X) x 74.2mm(Y). 74.2mm 길이 면(좌/우, Y방향 벽) 중 -X쪽 벽만
// 높이 10mm, 나머지 3면(+X쪽 74.2mm 벽, 위/아래 72mm 벽)은 높이 55mm.
// * 벽 두께는 지정하신 값이 없어 이 프로젝트 전반에서 쓰인 기본값 1.2mm로 가정했습니다.
// * 74.2mm인 두 면(좌/우) 중 어느 쪽을 줄일지 지정이 없어 -X쪽으로 가정했습니다.
//   +X쪽이어야 하면 알려주세요.
// ============================================================

module hard() {
    outer_w = 72;  // 바깥 가로(X)
    outer_d = 74.2; // 바깥 세로(Y) (74 -> 74.2)
    wall_t  = 1.2; // 벽 두께 (가정값)

    z_tall  = 55;  // 나머지 3면 높이 (25 -> 55)
    z_short = 10;  // -X쪽 74.2mm 벽 높이 (25 -> 10로 축소)

    inner_w = outer_w - 2 * wall_t;

    // -X쪽 벽 (74.2mm 길이, Y방향), 높이 10mm
    color("SteelBlue")
        translate([-outer_w / 2, -outer_d / 2, 0])
            linear_extrude(height = z_short)
                square([wall_t, outer_d]);

    // +X쪽 벽 (74.2mm 길이, Y방향), 높이 55mm
    color("SteelBlue")
        translate([outer_w / 2 - wall_t, -outer_d / 2, 0])
            linear_extrude(height = z_tall)
                square([wall_t, outer_d]);

    // -Y쪽 벽 (72mm 안쪽 폭, X방향), 높이 55mm
    color("SteelBlue")
        translate([-inner_w / 2, -outer_d / 2, 0])
            linear_extrude(height = z_tall)
                square([inner_w, wall_t]);

    // +Y쪽 벽 (72mm 안쪽 폭, X방향), 높이 55mm
    color("SteelBlue")
        translate([-inner_w / 2, outer_d / 2 - wall_t, 0])
            linear_extrude(height = z_tall)
                square([inner_w, wall_t]);
}

hard();
