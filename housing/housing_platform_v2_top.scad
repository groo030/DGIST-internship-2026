// ============================================================
// 플랫폼 v2 - 윗면(덮개) 평면도(XY, 위에서 본 모습)
// 55mm x 55mm 정사각형 평판, 두께 1.2mm.
// 네 모서리에 지름 2mm 구멍 (바깥쪽 모서리에서 대각선 각 축 방향 2.2mm, platform_v2 바닥의
// 모서리 나사 보스 구멍과 동일한 위치).
// 그리고 4개의 10x10mm 정사각형 구멍 (바깥쪽 모서리에서 각 축 방향 9.5mm 지점이
// 사각형의 모서리가 되도록 배치).
// ============================================================

module platform_v2_top() {
    face_size = 55;   // 면의 가로/세로 (정사각형)
    plate_t   = 1.2;  // 덮개 두께

    screw_d  = 2;      // 나사 구멍 지름
    hole_gap = 1.2;    // 바깥쪽 모서리 - 구멍 중심까지의 각 축 성분
    hole_off = face_size / 2 - hole_gap - screw_d / 2; // 중심까지 거리 (=25.3mm)

    sq_size    = 10;   // 정사각형 구멍 한 변
    sq_corner  = 9.5;  // 바깥쪽 모서리 - 사각형 모서리까지 각 축 거리
    sq_off     = face_size / 2 - sq_corner - sq_size / 2; // 중심까지 거리 (=13mm)

    echo("[PlatformV2Top] hole_off =", hole_off);
    echo("[PlatformV2Top] sq_off =", sq_off);

    color("gray")
        difference() {
            linear_extrude(height = plate_t)
                square([face_size, face_size], center = true);

            for (sx = [-1, 1])
                for (sy = [-1, 1])
                    translate([sx * hole_off, sy * hole_off, -0.1])
                        cylinder(d = screw_d, h = plate_t + 0.2, $fn = 40);

            for (sx = [-1, 1])
                for (sy = [-1, 1])
                    translate([sx * sq_off, sy * sq_off, -0.1])
                        linear_extrude(height = plate_t + 0.2)
                            square([sq_size, sq_size], center = true);
        }
}

platform_v2_top();
