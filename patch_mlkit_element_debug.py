from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_code = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        StringBuilder sb = new StringBuilder();
        sb.append("[ML KIT ELEMENT TEST]\n\n");

        int bIndex = 1;

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect br = block.getBoundingBox();

            sb.append("===== BLOCK ");
            sb.append(bIndex++);
            sb.append(" =====\n");

            if (br != null) {
                sb.append("BBOX L=").append(br.left)
                        .append(" T=").append(br.top)
                        .append(" R=").append(br.right)
                        .append(" B=").append(br.bottom)
                        .append(" W=").append(br.width())
                        .append(" H=").append(br.height())
                        .append("\n");
            }

            int lIndex = 1;

            for (Text.Line line : block.getLines()) {
                Rect lr = line.getBoundingBox();

                sb.append("  -- LINE ");
                sb.append(lIndex++);
                sb.append(" -- ");

                if (lr != null) {
                    sb.append("L=").append(lr.left)
                            .append(" T=").append(lr.top)
                            .append(" R=").append(lr.right)
                            .append(" B=").append(lr.bottom)
                            .append(" W=").append(lr.width())
                            .append(" H=").append(lr.height())
                            .append(" : ");
                }

                sb.append(line.getText()).append("\n");

                int eIndex = 1;

                for (Text.Element element : line.getElements()) {
                    Rect er = element.getBoundingBox();

                    sb.append("      E");
                    sb.append(eIndex++);
                    sb.append(" ");

                    if (er != null) {
                        sb.append("L=").append(er.left)
                                .append(" T=").append(er.top)
                                .append(" R=").append(er.right)
                                .append(" B=").append(er.bottom)
                                .append(" W=").append(er.width())
                                .append(" H=").append(er.height())
                                .append(" : ");
                    }

                    sb.append(element.getText()).append("\n");
                }
            }

            sb.append("\n");
        }

        overlay.removeAllViews();
        placedBoxes.clear();

        TextView tv = new TextView(this);
        tv.setText(sb.toString());
        tv.setTextSize(8);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(8, 8, 8, 8);
        tv.setMaxLines(120);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        FrameLayout.LayoutParams lp =
                new FrameLayout.LayoutParams(
                        dm.widthPixels - 20,
                        FrameLayout.LayoutParams.WRAP_CONTENT
                );

        lp.leftMargin = 10;
        lp.topMargin = 45;

        overlay.addView(tv, lp);
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("ML Kit element debug patch complete")
