# .scad 파일 실행 방법

## 1. GUI 앱으로 열기 (가장 편함)

- Finder에서 `test.scad`를 더블클릭하거나, OpenSCAD 앱을 열고 File → Open으로 불러오기
- 앱 안에서 `F5` = Preview(빠른 미리보기), `F6` = Render(정식 렌더링, 시간 더 걸림)
- 좌측 코드 창에서 값 수정 → F5 누르면 3D 뷰가 바로 갱신됨

## 2. 터미널(CLI)로 실행

```bash
openscad -o test.png --imgsize=800,600 --autocenter --viewall test.scad
```

- `.scad` 코드를 이미지(PNG)나 3D 모델 파일(STL, OFF 등)로 변환
- GUI 없이도 결과를 이미지로 뽑아서 확인 가능 → 코드 수정 후 바로바로 렌더링 결과를 확인하며 반복 작업할 때 이 방식 사용
- STL로 뽑고 싶으면:

```bash
openscad -o test.stl test.scad
```
