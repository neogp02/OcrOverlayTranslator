from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(Text result, String lang)")
end = s.find("\n    private ArrayList<OcrItem> groupPanelItemsLoose", start)

new_handle = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> lines = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            for (Text.Line line : block.getLines()) {
                Rect r = line.getBoundingBox();
                String text = cleanSourceKeepLines(line.getText());

                if (r == null) continue;
                if (text.length() < 2) continue;
                if (!containsJpOrZh(text)) continue;

                Rect rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
                lines.add(new OcrItem(rr, text));
            }
        }

        ArrayList<OcrItem> groups = groupLinesByXYStart(lines);

        groups.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 90) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        overlay.removeAllViews();
        placedBoxes.clear();

        StringBuilder panel = new StringBuilder();

        int max = Math.min(groups.size(), 50);

        for (int i = 0; i < max; i++) {
            panel.append("[")
                    .append(i + 1)
                    .append("]\n")
                    .append(groups.get(i).text)
                    .append("\n\n");
        }

        addBottomPanel(panel.toString());
    }

    private ArrayList<OcrItem> groupLinesByXYStart(ArrayList<OcrItem> lines) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(lines);

        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 90) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : sorted) {
            boolean added = false;

            for (ArrayList<OcrItem> g : groups) {
                Rect gr = rectOfLineGroup(g);
                Rect test = new Rect(gr);
                test.union(cur.rect);

                int xDist = Math.abs(cur.rect.centerX() - gr.centerX());
                int yStartDist = Math.abs(cur.rect.top - gr.top);

                int yOverlap = Math.min(cur.rect.bottom, gr.bottom) - Math.max(cur.rect.top, gr.top);
                int yGap = Math.max(0, Math.max(cur.rect.top - gr.bottom, gr.top - cur.rect.bottom));

                boolean xClose = xDist < 95;
                boolean yStartClose = yStartDist < 90;
                boolean yConnected = yOverlap > -40 || yGap < 70;

                // 말풍선 하나로 보기엔 너무 큰 그룹 방지
                boolean sizeOk = test.width() < 170 && test.height() < 360;

                if (xClose && yStartClose && yConnected && sizeOk) {
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
            Rect r = rectOfLineGroup(g);
            String text = orderLineGroupText(g);

            if (text.trim().length() > 0) {
                out.add(new OcrItem(r, text.trim()));
            }
        }

        return out;
    }

    private Rect rectOfLineGroup(ArrayList<OcrItem> group) {
        Rect r = new Rect(group.get(0).rect);
        for (OcrItem item : group) {
            r.union(item.rect);
        }
        return r;
    }

    private String orderLineGroupText(ArrayList<OcrItem> group) {
        ArrayList<OcrItem> sorted = new ArrayList<>(group);

        sorted.sort((a, b) -> {
            // 세로쓰기: 오른쪽 컬럼 먼저
            if (Math.abs(a.rect.centerX() - b.rect.centerX()) > 30) {
                return Integer.compare(b.rect.centerX(), a.rect.centerX());
            }

            // 같은 컬럼 안에서는 위에서 아래
            return Integer.compare(a.rect.top, b.rect.top);
        });

        StringBuilder sb = new StringBuilder();

        for (OcrItem item : sorted) {
            if (sb.length() > 0) sb.append("\n");
            sb.append(item.text);
        }

        return sb.toString();
    }

'''

if start == -1 or end == -1:
    print("handleText 교체 위치 못 찾음")
else:
    s = s[:start] + new_handle + s[end:]

p.write_text(s)
print("line group xy-start patch complete")
