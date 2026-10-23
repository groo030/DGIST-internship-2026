// ============================================================
// test.scad
// 70mm x 70mm 정사각형 기준 "ㄷ"자 브라켓. 높이 20mm, 두께 1.2mm.
// X축 양수방향 벽이 열려있는 형태 (hat.scad와 동일한 관례 적용 - 확인 필요).
// ============================================================

module test() {
    outer = 70;   // 바깥 정사각형 한 변
    t     = 1.2;  // 두께
    z     = 20;   // 높이
    inner = outer - 2 * t;

    color("SteelBlue")
        linear_extrude(height = z)
            difference() {
                difference() {
                    square([outer, outer], center = true);
                    square([inner, inner], center = true);
                }
                // X축 양수방향 벽 제거
                translate([inner / 2, -outer / 2 - 0.1])
                    square([outer / 2 - inner / 2 + 0.2, outer + 0.2]);
            }
}

test();
