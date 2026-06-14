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

            Rect rr = new Rect(
                    r.left / 2,
                    r.top / 2,
                    r.right / 2,
                    r.bottom / 2
            );

            items.add(new OcrItem(rr, text));
        }

        ArrayList<OcrItem> groups = groupSpeechBubbles(items);

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;
        for (OcrItem g : groups) {
            addTextBox(g.rect, g.text);
            count++;
            if (count >= 25) break;
        }
    }

    private ArrayList<OcrItem> groupSpeechBubbles(ArrayList<OcrItem> items) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        items.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 120) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : items) {
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

                // 너무 멀리 있는 다른 컷/다른 말풍선끼리 합쳐지는 것 방지
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

        ArrayList<OcrItem> out = new ArrayList<>();

        for (ArrayList<OcrItem> group : groups) {
            group.sort((a, b) -> {
                // 세로쓰기: 오른쪽 열부터 왼쪽 열
                if (Math.abs(a.rect.centerX() - b.rect.centerX()) > 25) {
                    return Integer.compare(b.rect.centerX(), a.rect.centerX());
                }
                return Integer.compare(a.rect.top, b.rect.top);
            });

            StringBuilder sb = new StringBuilder();
            Rect area = rectOfItems(group);

            for (OcrItem item : group) {
                if (sb.length() > 0) sb.append("\n");
                sb.append(item.text);
            }

            out.add(new OcrItem(area, sb.toString().trim()));
        }

        out.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 100) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        return out;
    }

    private Rect rectOfItems(ArrayList<OcrItem> items) {
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
print("speech bubble grouping v1 patch complete")
