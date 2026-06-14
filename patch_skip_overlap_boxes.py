from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# placedBoxes 필드가 없으면 추가
if "private final List<Rect> placedBoxes" not in s:
    s = s.replace(
        'private String lastKey = "";',
        'private String lastKey = "";\n    private final List<Rect> placedBoxes = new ArrayList<>();'
    )

# addTextBox 교체: 겹치면 표시하지 않음
start = s.find("private void addTextBox(Rect r, String text)")
end = s.find("@Override\n    public void onDestroy", start)

new_func = r'''
    private void addTextBox(Rect r, String text) {
        if (text == null) return;

        text = text.trim();
        if (text.length() == 0) return;

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(11);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(7, 4, 7, 4);
        tv.setMaxLines(8);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int boxW = Math.max(95, r.width() + 45);
        int boxH = Math.max(60, r.height() + 45);

        if (r.height() > r.width() * 1.3f) {
            boxW = Math.max(85, r.width() + 35);
            boxH = Math.max(70, r.height() + 35);
            tv.setTextSize(10);
            tv.setMaxLines(10);
        }

        int x = Math.max(0, r.left - 4);
        int y = Math.max(0, r.top - 4);

        if (x + boxW > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - boxW - 4);
        }

        if (y + boxH > dm.heightPixels) {
            y = Math.max(0, dm.heightPixels - boxH - 4);
        }

        Rect newBox = new Rect(x, y, x + boxW, y + boxH);

        // 이미 표시된 박스와 겹치면 이번 박스는 버림
        for (Rect old : placedBoxes) {
            Rect padded = new Rect(old.left - 6, old.top - 6, old.right + 6, old.bottom + 6);
            if (Rect.intersects(newBox, padded)) {
                return;
            }
        }

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(boxW, boxH);
        fp.leftMargin = x;
        fp.topMargin = y;

        overlay.addView(tv, fp);
        placedBoxes.add(newBox);
    }

'''

if start == -1 or end == -1:
    print("addTextBox 함수 위치를 못 찾음")
else:
    s = s[:start] + new_func + s[end:]

p.write_text(s)
print("skip overlap boxes patch complete")
