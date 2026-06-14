from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_code = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect r = block.getBoundingBox();
            String text = cleanSource(block.getText());

            if (r == null) continue;
            if (text.length() < 2) continue;
            if (!containsJpOrZh(text)) continue;

            addTextBox(r, "[BLOCK]\n" + text);

            count++;
            if (count >= 20) break;
        }
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

# addTextBox를 Block용으로 조정
start = s.find("private void addTextBox(Rect r, String text)")
end = s.find("@Override\n    public void onDestroy", start)

new_add = r'''
    private void addTextBox(Rect r, String text) {
        if (text == null) return;

        text = text.trim();
        if (text.length() == 0) return;

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(9);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC000000);
        tv.setPadding(5, 3, 5, 3);
        tv.setMaxLines(12);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int w = Math.max(65, r.width() + 25);
        int h = Math.max(50, r.height() + 20);

        if (w > 145) w = 145;
        if (h > 145) h = 145;

        int x = Math.max(0, r.left - 3);
        int y = Math.max(0, r.top - 3);

        if (x + w > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - w - 3);
        }

        if (y + h > dm.heightPixels) {
            y = Math.max(0, dm.heightPixels - h - 3);
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
print("use blocks directly patch complete")
