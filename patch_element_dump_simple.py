from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_code = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        StringBuilder sb = new StringBuilder();
        sb.append("[ELEMENT DUMP]\n\n");

        int blockIndex = 1;

        for (Text.TextBlock block : result.getTextBlocks()) {
            sb.append("B").append(blockIndex++).append(": ");
            sb.append(block.getText()).append("\n");

            int lineIndex = 1;

            for (Text.Line line : block.getLines()) {
                Rect lr = line.getBoundingBox();

                sb.append("  L").append(lineIndex++).append(" ");
                if (lr != null) {
                    sb.append("box=");
                    sb.append(lr.left).append(",");
                    sb.append(lr.top).append(",");
                    sb.append(lr.right).append(",");
                    sb.append(lr.bottom).append(" ");
                }
                sb.append("text=[").append(line.getText()).append("]\n");

                int elementIndex = 1;

                for (Text.Element element : line.getElements()) {
                    Rect er = element.getBoundingBox();

                    sb.append("    E").append(elementIndex++).append(" ");
                    if (er != null) {
                        sb.append("box=");
                        sb.append(er.left).append(",");
                        sb.append(er.top).append(",");
                        sb.append(er.right).append(",");
                        sb.append(er.bottom).append(" ");
                    }
                    sb.append("text=[").append(element.getText()).append("]\n");
                }
            }

            sb.append("\n");
        }

        overlay.removeAllViews();
        placedBoxes.clear();

        TextView tv = new TextView(this);
        tv.setText(sb.toString());
        tv.setTextSize(7);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(8, 8, 8, 8);
        tv.setMaxLines(160);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        FrameLayout.LayoutParams lp =
                new FrameLayout.LayoutParams(
                        dm.widthPixels - 20,
                        FrameLayout.LayoutParams.WRAP_CONTENT
                );

        lp.leftMargin = 10;
        lp.topMargin = 40;

        overlay.addView(tv, lp);
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("element dump simple patch complete")
