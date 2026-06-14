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

        ArrayList<OcrItem> groups = groupBubbleCandidatesV2(items);

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;
        for (OcrItem g : groups) {
            addTextBox(g.rect, g.text);
            count++;
            if (count >= 25) break;
        }
    }

    private ArrayList<OcrItem> groupBubbleCandidatesV2(ArrayList<OcrItem> items) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        items.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 100) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : items) {
            boolean added = false;

            for (ArrayList<OcrItem> g : groups) {
                Rect gr = rectOfItemsV2(g);

                int dx = Math.abs(cur.rect.centerX() - gr.centerX());
                int dy = Math.abs(cur.rect.centerY() - gr.centerY());

                int overlapY = Math.min(cur.rect.bottom, gr.bottom) - Math.max(cur.rect.top, gr.top);
                int gapY = Math.max(0, Math.max(cur.rect.top - gr.bottom, gr.top - cur.rect.bottom));

                Rect test = new Rect(gr);
                test.union(cur.rect);

                boolean closeColumn = dx < 70;
                boolean yClose = overlapY > -45 || gapY < 70;
                boolean centerClose = dy < 210;

                // 말풍선 하나가 비정상적으로 커지는 것 방지
                boolean sizeOk = test.width() < 145 && test.height() < 340;

                if (closeColumn && yClose && centerClose && sizeOk) {
                    g.add(cur);
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

        ArrayList<OcrItem> out = new ArrayList<>();

        for (ArrayList<OcrItem> g : groups) {
            Rect area = rectOfItemsV2(g);
            String text = orderVerticalTextV2(g);

            if (text.trim().length() == 0) continue;
            out.add(new OcrItem(area, text.trim()));
        }

        out.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 90) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        return out;
    }

    private String orderVerticalTextV2(ArrayList<OcrItem> group) {
        ArrayList<ArrayList<OcrItem>> columns = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(group);
        sorted.sort((a, b) -> Integer.compare(b.rect.centerX(), a.rect.centerX()));

        for (OcrItem item : sorted) {
            boolean added = false;

            for (ArrayList<OcrItem> col : columns) {
                Rect cr = rectOfItemsV2(col);
                int dx = Math.abs(item.rect.centerX() - cr.centerX());

                if (dx < 32) {
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
            Rect ar = rectOfItemsV2(a);
            Rect br = rectOfItemsV2(b);
            return Integer.compare(br.centerX(), ar.centerX());
        });

        StringBuilder sb = new StringBuilder();

        for (ArrayList<OcrItem> col : columns) {
            col.sort((a, b) -> Integer.compare(a.rect.top, b.rect.top));

            for (OcrItem item : col) {
                if (sb.length() > 0) sb.append("\n");
                sb.append(item.text);
            }
        }

        return sb.toString();
    }

    private Rect rectOfItemsV2(ArrayList<OcrItem> items) {
        Rect r = new Rect(items.get(0).rect);
        for (OcrItem item : items) {
            r.union(item.rect);
        }
        return r;
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("bubble group v2 strict patch complete")
