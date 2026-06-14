from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_code = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        StringBuilder sb = new StringBuilder();
        sb.append("[ML KIT BLOCK TEST]\n\n");

        int index = 1;

        for (Text.TextBlock block : result.getTextBlocks()) {
            sb.append("===== BLOCK ");
            sb.append(index++);
            sb.append(" =====\n");
            sb.append(block.getText());
            sb.append("\n\n");
        }

        overlay.removeAllViews();
        placedBoxes.clear();

        TextView tv = new TextView(this);
        tv.setText(sb.toString());
        tv.setTextSize(12);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(12, 12, 12, 12);
        tv.setMaxLines(60);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        FrameLayout.LayoutParams lp =
                new FrameLayout.LayoutParams(
                        dm.widthPixels - 20,
                        FrameLayout.LayoutParams.WRAP_CONTENT
                );

        lp.leftMargin = 10;
        lp.topMargin = 80;

        overlay.addView(tv, lp);
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("ML Kit block debug patch complete")
