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

        String dump = debugGroupDump(items);

        overlay.removeAllViews();
        placedBoxes.clear();

        TextView tv = new TextView(this);
        tv.setText(dump);
        tv.setTextSize(7);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(8, 8, 8, 8);
        tv.setMaxLines(180);

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

    private String debugGroupDump(ArrayList<OcrItem> items) {
        ArrayList<ArrayList<OcrItem>> groups = makeDebugGroups(items);

        StringBuilder sb = new StringBuilder();
        sb.append("[GROUP DEBUG DUMP]\n\n");
        sb.append("items=").append(items.size()).append("\n");
        sb.append("groups=").append(groups.size()).append("\n\n");

        int gi = 1;

        for (ArrayList<OcrItem> g : groups) {
            ArrayList<ArrayList<OcrItem>> cols = splitDebugColumns(g);

            Rect gr = rectOfItems(g);

            sb.append("===== GROUP ").append(gi++).append(" =====\n");
            sb.append("box=");
            sb.append(gr.left).append(",");
            sb.append(gr.top).append(",");
            sb.append(gr.right).append(",");
            sb.append(gr.bottom);
            sb.append(" w=").append(gr.width());
            sb.append(" h=").append(gr.height()).append("\n");
            sb.append("items=").append(g.size());
            sb.append(" columns=").append(cols.size()).append("\n");

            int ci = 1;

            for (ArrayList<OcrItem> col : cols) {
                Rect cr = rectOfItems(col);
                sb.append("  -- COL ").append(ci++).append(" ");
                sb.append("cx=").append(cr.centerX());
                sb.append(" box=");
                sb.append(cr.left).append(",");
                sb.append(cr.top).append(",");
                sb.append(cr.right).append(",");
                sb.append(cr.bottom).append("\n");

                col.sort((a, b) -> Integer.compare(a.rect.top, b.rect.top));

                for (OcrItem item : col) {
                    sb.append("     item cx=").append(item.rect.centerX());
                    sb.append(" cy=").append(item.rect.centerY());
                    sb.append(" box=");
                    sb.append(item.rect.left).append(",");
                    sb.append(item.rect.top).append(",");
                    sb.append(item.rect.right).append(",");
                    sb.append(item.rect.bottom);
                    sb.append(" text=[").append(item.text).append("]\n");
                }
            }

            sb.append("\n");
        }

        return sb.toString();
    }

    private ArrayList<ArrayList<OcrItem>> makeDebugGroups(ArrayList<OcrItem> items) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(items);

        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 120) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : sorted) {
            boolean added = false;

            for (ArrayList<OcrItem> group : groups) {
                Rect gr = rectOfItems(group);

                int dx = Math.abs(cur.rect.centerX() - gr.centerX());
                int dy = Math.abs(cur.rect.centerY() - gr.centerY());

                int overlapY = Math.min(cur.rect.bottom, gr.bottom) - Math.max(cur.rect.top, gr.top);
                int gapY = Math.max(0, Math.max(cur.rect.top - gr.bottom, gr.top - cur.rect.bottom));

                boolean closeX = dx < 95;
                boolean closeY = dy < 260 || gapY < 120;
                boolean yRelated = overlapY > -120;
                boolean notTooLarge = gr.width() < 190 && gr.height() < 430;

                if (closeX && closeY && yRelated && notTooLarge) {
                    group.add(cur);
                    added = true;
                    break;
                }
            }

            if (!added) {
                ArrayList<OcrItem> ng = new ArrayList<>();
                ng.add(cur);
                groups.add(ng);
            }
        }

        return groups;
    }

    private ArrayList<ArrayList<OcrItem>> splitDebugColumns(ArrayList<OcrItem> group) {
        ArrayList<ArrayList<OcrItem>> columns = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(group);
        sorted.sort((a, b) -> Integer.compare(b.rect.centerX(), a.rect.centerX()));

        for (OcrItem item : sorted) {
            boolean added = false;

            for (ArrayList<OcrItem> col : columns) {
                Rect cr = rectOfItems(col);
                int dx = Math.abs(item.rect.centerX() - cr.centerX());

                if (dx < 38) {
                    col.add(item);
                    added = true;
                    break;
                }
            }

            if (!added) {
                ArrayList<OcrItem> nc = new ArrayList<>();
                nc.add(item);
                columns.add(nc);
            }
        }

        columns.sort((a, b) -> {
            Rect ar = rectOfItems(a);
            Rect br = rectOfItems(b);
            return Integer.compare(br.centerX(), ar.centerX());
        });

        return columns;
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("group debug dump patch complete")
