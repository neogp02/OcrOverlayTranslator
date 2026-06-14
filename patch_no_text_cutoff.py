from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void addTextBox(Rect r, String text)")
end = s.find("@Override\n    public void onDestroy", start)

new_add = r'''
    private void addTextBox(Rect r, String text) {
        if (text == null) return;

        text = text.trim();
        if (text.length() == 0) return;

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(6);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC000000);
        tv.setPadding(3, 2, 3, 2);
        tv.setSingleLine(false);
        tv.setMaxLines(20);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int w = Math.max(48, r.width() + 26);
        int h = Math.max(60, r.height() + 80);

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
print("no text cutoff patch complete")
