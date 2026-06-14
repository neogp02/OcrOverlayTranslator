from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 1. handleText에서 block 좌표를 화면 기준으로 /2 보정하고 [BLOCK] 제거
s = s.replace(
'''addTextBox(r, "[BLOCK]\\n" + text);''',
'''Rect rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
            addTextBox(rr, text);'''
)

# 2. addTextBox 표시 방식 개선
start = s.find("private void addTextBox(Rect r, String text)")
end = s.find("@Override\n    public void onDestroy", start)

new_add = r'''
    private void addTextBox(Rect r, String text) {
        if (text == null) return;

        text = text.trim();
        if (text.length() == 0) return;

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(8);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC000000);
        tv.setPadding(4, 3, 4, 3);
        tv.setMaxLines(20);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int w = Math.max(55, r.width() + 20);
        int h = Math.max(45, r.height() + 25);

        // 너무 작게 잘리는 문제 완화
        if (w > 170) w = 170;
        if (h > 260) h = 260;

        int x = Math.max(0, r.left - 2);
        int y = Math.max(0, r.top - 2);

        if (x + w > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - w - 2);
        }

        if (y + h > dm.heightPixels) {
            y = Math.max(0, dm.heightPixels - h - 2);
        }

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(w, h);
        fp.leftMargin = x;
        fp.topMargin = y;

        overlay.addView(tv, fp);
    }

'''

if start == -1 or end == -1:
    print("addTextBox 위치를 못 찾음")
else:
    s = s[:start] + new_add + s[end:]

p.write_text(s)
print("block position/display patch complete")
