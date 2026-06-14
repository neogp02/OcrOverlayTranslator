from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 1. 표시 개수 제한 4 -> 12
s = s.replace("if (count >= 4) break;", "if (count >= 12) break;")

# 2. addTextBox 함수 안에서 y 위치 계산 수정
old = '''int x = Math.max(0, r.left - 6);
        int y = Math.max(0, r.top - 6);

        if (x + boxW > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - boxW - 4);
        }

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(boxW, boxH);
        fp.leftMargin = x;
        fp.topMargin = y;'''

new = '''int x = Math.max(0, r.left - 6);

        // 가능하면 원문 위쪽에 표시.
        // 위쪽 공간이 부족하면 원문 위치에 표시.
        int estimatedH = Math.max(70, r.height() + 50);
        int y;
        if (r.top - estimatedH - 6 > 0) {
            y = r.top - estimatedH - 6;
        } else {
            y = Math.max(0, r.top - 6);
        }

        if (x + boxW > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - boxW - 4);
        }

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(boxW, boxH);
        fp.leftMargin = x;
        fp.topMargin = y;'''

if old not in s:
    print("위치 계산 코드 못 찾음")
else:
    s = s.replace(old, new)

p.write_text(s)
print("more boxes + above positioning patch complete")
