// ============================================================
// 캡스톤 프로젝트 - 하우징 (완전히 새 디자인)
// 단위: 전부 cm
//
// 직육면체(몸통): 가로(X) 10cm x 세로(Y) 6cm x 높이(Z) 7cm, 벽 두께 1cm의 빈 상자.
//   바닥면(판재1이 붙는 면, world Z 아래쪽)에 8cm x 5cm 직사각형 구멍을 정중앙에 뚫음,
//   높이 7cm 전체를 관통해 윗면까지 이어짐.
// 판재1: 10cm x 6cm 직사각형, 두께 1cm. 직육면체 바로 아래, 같은 footprint로 맞닿음.
// 판재2, 3: 6cm x 6cm 정사각형 2개, 두께 1cm. 판재1 아래에 나란히(X축 방향) 배치.
//
// * 정사각형 2개 사이 간격은 아직 정확한 값을 받지 못해 0(맞닿음)으로 가정했습니다.
//   실제 원하시는 배치와 다를 수 있어 확인 후 조정하겠습니다.
// ============================================================

module capstone() {
    // 직육면체(몸통)
    body_w = 10;   // 가로(X)
    body_d = 6;    // 세로(Y)
    body_h = 7;    // 높이(Z)
    wall_t = 1;    // 벽 두께

    // 판재1
    plate1_w = 10;
    plate1_d = 6;
    plate1_t = 1;

    // 판재2, 3 (정사각형, 나란히)
    sq_size = 6;
    sq_t    = 1;
    sq_gap  = 0; // TODO: 두 정사각형 사이 간격 미확정 (일단 0, 맞닿음으로 가정)

    // 구멍 (직육면체 바닥면, 정중앙, 높이 전체 관통)
    hole_w = 8;
    hole_d = 5;

    // --- Z 스택 (아래 -> 위) ---
    sq_z0     = 0;
    sq_z1     = sq_z0 + sq_t;          // 1
    plate1_z0 = sq_z1;                 // 1
    plate1_z1 = plate1_z0 + plate1_t;  // 2
    body_z0   = plate1_z1;             // 2
    body_z1   = body_z0 + body_h;      // 9

    echo("[Capstone] total height =", body_z1, " (sq_t+plate1_t+body_h)");

    // 정사각형 2개 (나란히, X축 방향)
    sq_total_w = sq_size * 2 + sq_gap;
    color("SteelBlue") {
        translate([-sq_total_w / 2, -sq_size / 2, sq_z0])
            cube([sq_size, sq_size, sq_t]);
        translate([-sq_total_w / 2 + sq_size + sq_gap, -sq_size / 2, sq_z0])
            cube([sq_size, sq_size, sq_t]);
    }

    // 판재1
    color("SteelBlue")
        translate([-plate1_w / 2, -plate1_d / 2, plate1_z0])
            cube([plate1_w, plate1_d, plate1_t]);

    // 직육면체 몸통 (속이 빈 상자, 벽 두께 wall_t) + 8x5 구멍 (높이 전체 관통)
    inner_w = body_w - 2 * wall_t;
    inner_d = body_d - 2 * wall_t;
    inner_h = body_h - 2 * wall_t;

    difference() {
        color("gray")
            difference() {
                translate([-body_w / 2, -body_d / 2, body_z0])
                    cube([body_w, body_d, body_h]);
                translate([-inner_w / 2, -inner_d / 2, body_z0 + wall_t])
                    cube([inner_w, inner_d, inner_h]);
            }
        translate([-hole_w / 2, -hole_d / 2, body_z0 - 0.1])
            cube([hole_w, hole_d, body_h + 0.2]);
    }
}

capstone();
