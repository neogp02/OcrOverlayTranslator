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
            for (Text.Line line : block.getLines()) {
                Rect r = line.getBoundingBox();
                String text = cleanSource(line.getText());

                if (r == null) continue;
                if (text.length() < 2) continue;
                if (!containsJpOrZh(text)) continue;

                // OCR 이미지를 2배 확대해서 넣었으므로 좌표 /2 보정
                Rect rr = new Rect(
                        r.left / 2,
                        r.top / 2,
                        r.right / 2,
                        r.bottom / 2
                );

                addTextBox(rr, text);

                count++;
                if (count >= 35) break;
            }

            if (count >= 35) break;
        }
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

# LINE 표시용 addTextBox
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
        tv.setPadding(3, 2, 3, 2);
        tv.setMaxLines(8);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int w = Math.max(42, r.width() + 18);
        int h = Math.max(36, r.height() + 18);

        if (w > 120) w = 120;
        if (h > 180) h = 180;

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
print("use lines directly patch complete")
