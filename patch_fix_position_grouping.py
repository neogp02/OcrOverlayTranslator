from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 1. 세로열 병합 범위 더 축소
s = s.replace(
    "if (gapX < 35 && overlapY > 10)",
    "if (gapX < 20 && overlapY > 40)"
)

# 혹시 이전 조건이 남아있을 경우도 처리
s = s.replace(
    "if (gapX < 80 && overlapY > -40)",
    "if (gapX < 20 && overlapY > 40)"
)

# 2. addTextBox 함수 교체: 겹침 회피 제거, OCR 위치 그대로 덮기
start = s.find("private void addTextBox(Rect r, String text)")
end = s.find("@Override\n    public void onDestroy", start)

new_func = r'''
    private void addTextBox(Rect r, String text) {
        if (text == null) return;

        text = text.trim();
        if (text.length() == 0) return;

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(12);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(8, 5, 8, 5);
        tv.setMaxLines(8);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int boxW = Math.max(120, r.width() + 55);
        int boxH = FrameLayout.LayoutParams.WRAP_CONTENT;

        // 세로 말풍선은 조금 좁고 길게
        if (r.height() > r.width() * 1.3f) {
            boxW = Math.max(95, r.width() + 45);
            tv.setTextSize(11);
            tv.setMaxLines(12);
        }

        int x = Math.max(0, r.left - 6);
        int y = Math.max(0, r.top - 6);

        if (x + boxW > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - boxW - 4);
        }

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(boxW, boxH);
        fp.leftMargin = x;
        fp.topMargin = y;

        overlay.addView(tv, fp);
    }

'''

if start == -1 or end == -1:
    print("addTextBox 함수 위치를 못 찾음")
else:
    s = s[:start] + new_func + s[end:]

p.write_text(s)
print("position/grouping patch complete")
