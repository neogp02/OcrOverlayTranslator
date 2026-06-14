from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_code = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> items = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect r = block.getBoundingBox();
            String text = cleanSource(block.getText());

            if (r == null) continue;
            if (text.length() < 2) continue;
            if (!containsJpOrZh(text)) continue;

            Rect rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
            items.add(new OcrItem(rr, text));
        }

        items.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 100) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        overlay.removeAllViews();
        placedBoxes.clear();

        StringBuilder panel = new StringBuilder();
        int index = 1;

        for (OcrItem item : items) {
            addNumberMarker(item.rect, index);
            panel.append(index)
                    .append(". ")
                    .append(item.text.replace("\n", " "))
                    .append("\n");

            index++;
            if (index > 25) break;
        }

        addBottomPanel(panel.toString());
    }

    private void addNumberMarker(Rect r, int number) {
        TextView tv = new TextView(this);
        tv.setText(String.valueOf(number));
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setGravity(Gravity.CENTER);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(2, 1, 2, 1);

        int size = 24;
        int x = Math.max(0, r.left - 6);
        int y = Math.max(0, r.top - 6);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        if (x + size > dm.widthPixels) x = dm.widthPixels - size;
        if (y + size > dm.heightPixels) y = dm.heightPixels - size;

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(size, size);
        fp.leftMargin = x;
        fp.topMargin = y;

        overlay.addView(tv, fp);
    }

    private void addBottomPanel(String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xE6000000);
        tv.setPadding(12, 10, 12, 10);
        tv.setMaxLines(12);
        tv.setSingleLine(false);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int panelHeight = Math.min(360, dm.heightPixels / 3);

        FrameLayout.LayoutParams fp =
                new FrameLayout.LayoutParams(
                        dm.widthPixels,
                        panelHeight
                );

        fp.leftMargin = 0;
        fp.topMargin = dm.heightPixels - panelHeight;

        overlay.addView(tv, fp);
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("numbered panel mode patch complete")
