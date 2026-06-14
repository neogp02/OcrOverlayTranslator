from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_code = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        String raw = result.getText();

        overlay.removeAllViews();
        placedBoxes.clear();

        showRawOcrDebug(raw);
    }

    private void showRawOcrDebug(String raw) {
        if (raw == null) raw = "";

        TextView tv = new TextView(this);
        tv.setText("[ML KIT RAW OCR]\n" + raw);
        tv.setTextSize(12);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(12, 8, 12, 8);
        tv.setMaxLines(35);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        FrameLayout.LayoutParams fp =
                new FrameLayout.LayoutParams(
                        dm.widthPixels - 30,
                        FrameLayout.LayoutParams.WRAP_CONTENT
                );

        fp.leftMargin = 15;
        fp.topMargin = 80;

        overlay.addView(tv, fp);
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("RAW OCR screen debug patch complete")
