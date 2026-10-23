difference() {
    cube([50, 50, 10], center=true);
    translate([0, 0, 2])
        cylinder(h=10, d=15, center=true);
}