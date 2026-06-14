from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_code = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> blocks = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect r = block.getBoundingBox();
            String t = cleanSource(block.getText());

            if (r == null) continue;
            if (t.length() < 2) continue;
            if (!containsJpOrZh(t)) continue;

            blocks.add(new OcrItem(new Rect(r), t));
        }

        ArrayList<OcrItem> groups = mergeVerticalBlocks(blocks);

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;

        for (OcrItem g : groups) {
            addTextBox(g.rect, "[GROUP]\n" + g.text);
            count++;
            if (count >= 12) break;
        }
    }

    private ArrayList<OcrItem> mergeVerticalBlocks(ArrayList<OcrItem> blocks) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        // 오른쪽에서 왼쪽 순서로 정렬
        blocks.sort((a, b) -> Integer.compare(b.rect.centerX(), a.rect.centerX()));

        for (OcrItem b : blocks) {
            boolean added = false;

            for (ArrayList<OcrItem> g : groups) {
                Rect gr = rectOfItems(g);

                int gapX = Math.abs(gr.centerX() - b.rect.centerX());
                int overlapY = Math.min(gr.bottom, b.rect.bottom) - Math.max(gr.top, b.rect.top);

                boolean nearX = gapX < 85;
                boolean sameHeight = overlapY > -80;

                if (nearX && sameHeight) {
                    g.add(b);
                    added = true;
                    break;
                }
            }

            if (!added) {
                ArrayList<OcrItem> ng = new ArrayList<>();
                ng.add(b);
                groups.add(ng);
            }
        }

        ArrayList<OcrItem> result = new ArrayList<>();

        for (ArrayList<OcrItem> g : groups) {
            // 같은 말풍선 안에서는 오른쪽 열 -> 왼쪽 열 순서
            g.sort((a, b) -> Integer.compare(b.rect.centerX(), a.rect.centerX()));

            StringBuilder sb = new StringBuilder();
            Rect area = rectOfItems(g);

            for (OcrItem item : g) {
                if (sb.length() > 0) sb.append("\n");
                sb.append(item.text);
            }

            String text = sb.toString().trim();
            if (text.length() == 0) continue;

            result.add(new OcrItem(area, text));
        }

        // 화면상 위쪽부터, 같은 높이면 오른쪽부터
        result.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 120) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        return result;
    }

    private Rect rectOfItems(ArrayList<OcrItem> items) {
        Rect r = new Rect(items.get(0).rect);
        for (OcrItem i : items) {
            r.union(i.rect);
        }
        return r;
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("block grouping debug patch complete")
