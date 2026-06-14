from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(Text result, String lang)")
end = s.find("\n    private ArrayList<OcrItem> groupLinesByXYStart", start)

new_handle = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> elems = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            for (Text.Line line : block.getLines()) {
                for (Text.Element el : line.getElements()) {
                    Rect r = el.getBoundingBox();
                    String text = cleanSourceKeepLines(el.getText());

                    if (r == null) continue;
                    if (text.length() < 1) continue;
                    if (!containsJpOrZh(text)) continue;

                    Rect rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
                    elems.add(new OcrItem(rr, text));
                }
            }
        }

        ArrayList<OcrItem> groups = groupElementsForBubbles(elems);

        groups.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 70) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        overlay.removeAllViews();
        placedBoxes.clear();

        StringBuilder panel = new StringBuilder();

        int max = Math.min(groups.size(), 60);

        for (int i = 0; i < max; i++) {
            OcrItem it = groups.get(i);

            panel.append("[")
                    .append(i + 1)
                    .append("] ")
                    .append("L=").append(it.rect.left)
                    .append(" T=").append(it.rect.top)
                    .append(" R=").append(it.rect.right)
                    .append(" B=").append(it.rect.bottom)
                    .append(" W=").append(it.rect.width())
                    .append(" H=").append(it.rect.height())
                    .append("\n")
                    .append(it.text)
                    .append("\n\n");
        }

        addBottomPanel(panel.toString());
    }

'''

if start == -1 or end == -1:
    print("handleText 교체 위치 못 찾음")
else:
    s = s[:start] + new_handle + s[end:]

# 기존 groupLinesByXYStart 함수 앞에 새 함수 추가
insert_pos = s.find("private ArrayList<OcrItem> groupLinesByXYStart")

helper = r'''
    private ArrayList<OcrItem> groupElementsForBubbles(ArrayList<OcrItem> elems) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(elems);

        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 55) {
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

                OcrItem anchor = g.get(0);

                int anchorX = anchor.rect.centerX();
                int anchorTop = anchor.rect.top;

                int xDist = Math.abs(cur.rect.centerX() - anchorX);
                int yStartDist = Math.abs(cur.rect.top - anchorTop);

                int yOverlap =
                        Math.min(cur.rect.bottom, gr.bottom)
                        - Math.max(cur.rect.top, gr.top);

                int yGap =
                        Math.max(0,
                                Math.max(cur.rect.top - gr.bottom,
                                         gr.top - cur.rect.bottom));

                // 같은 말풍선 내부 세로열 조건
                boolean xClose = xDist <= 92;

                // 시작점이 너무 다르면 다른 말풍선으로 분리
                boolean yStartClose = yStartDist <= 42;

                // 너무 멀리 떨어진 요소는 분리
                boolean yConnected = yOverlap > -35 || yGap <= 65;

                // 말풍선 하나로 보기엔 너무 큰 영역 방지
                boolean sizeOk = test.width() <= 165 && test.height() <= 320;

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

'''

if insert_pos != -1 and "groupElementsForBubbles" not in s:
    s = s[:insert_pos] + helper + s[insert_pos:]

p.write_text(s)
print("element based grouping patched")
