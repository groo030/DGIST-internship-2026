// ============================================================
// 클로저 하우징 - 평면도(XY, 정면에서 본 모습)
// 뚫린 면(-X쪽)에 들어갈 평판. 하단 돌출 탭이 ERM 면과 맞물림.
// ============================================================

module closure_housing() {
    lid_w = 22.6;  // 평판 가로
    lid_h = 23.8;  // 평판 세로
    lid_t = 1.8;   // 평판 두께 (1.2 -> 1.8, 0.6mm 증가)
    plate_grow = lid_t - 1.2; // 두께 증가분 (0.6mm) - 바깥쪽(outer, z 음의 방향)으로 확장

    hole_d          = 2;   // 구멍 지름
    hole_y_from_top = 1.2; // 윗변 - 구멍 중심 거리 (가장 가까운 면의 모서리와 1.2mm 차이)

    hole_x = 0;                       // 가운데 정렬
    hole_y = lid_h / 2 - hole_y_from_top;

    tab_w    = 5;   // 하단 돌출부 가로
    tab_len  = 1.2; // 하단 돌출부가 평판 아래로 튀어나온 길이
    tab_z    = 1.0; // 돌출부의 Z방향 두께 (평판 바깥쪽 면과 밑면이 딱 맞음, 안쪽으로 0.8mm 단차)

    echo("[Closure] hole_x =", hole_x, " hole_y =", hole_y);

    // 메인 평판 (구멍 1개, 가운데). 안쪽면(z=1.2)은 고정, 바깥쪽면이 0.6mm 더 나감(z=-0.6)
    color("gray")
        translate([0, 0, -plate_grow])
            linear_extrude(height = lid_t)
                difference() {
                    square([lid_w, lid_h], center = true);
                    translate([hole_x, hole_y]) circle(d = hole_d, $fn = 50);
                }

    // 하단 돌출 탭 (평판 아래쪽 가장자리에서 1.2mm 튀어나옴).
    // Z방향으로는 평판 바깥쪽 면(z=-plate_grow)과 밑면이 딱 맞고, 두께는 1mm만
    // (평판 두께 1.8mm 중 안쪽으로 0.8mm는 단차로 비움)
    color("SlateGray")
        translate([0, -lid_h / 2 - tab_len / 2, -plate_grow])
            linear_extrude(height = tab_z)
                square([tab_w, tab_len], center = true);
}

closure_housing();
