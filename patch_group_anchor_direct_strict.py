from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private ArrayList<OcrItem> groupLinesByXYStart")
end = s.find("\n    private Rect rectOfLineGroup", start)

new_code = r'''
    private ArrayList<OcrItem> groupLinesByXYStart(ArrayList<OcrItem> lines) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(lines);

        sorted.sort((a, b) -> {
            // 먼저 위쪽
            if (Math.abs(a.rect.top - b.rect.top) > 45) {
                return Integer.compare(a.rect.top, b.rect.top);
            }

            // 같은 높이면 오른쪽부터
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : sorted) {
            boolean added = false;

            for (ArrayList<OcrItem> g : groups) {
                OcrItem anchor = g.get(0);

                Rect gr = rectOfLineGroup(g);
                Rect test = new Rect(gr);
                test.union(cur.rect);

                int xDist = Math.abs(cur.rect.centerX() - anchor.rect.centerX());
                int yStartDist = Math.abs(cur.rect.top - anchor.rect.top);

                // 핵심: y 길이/겹침이 아니라 시작점 기준
                boolean xClose = xDist <= 80;
                boolean yStartClose = yStartDist <= 28;

                // 아래쪽으로 이어지는 세로 대사는 허용, 위로 역결합은 금지
                boolean notAboveAnchor = cur.rect.top >= anchor.rect.top - 12;

                // 너무 큰 말풍선 방지
                boolean sizeOk = test.width() <= 150 && test.height() <= 310;

                if (xClose && yStartClose && notAboveAnchor && sizeOk) {
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

if start == -1 or end == -1:
    print("groupLinesByXYStart 위치 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("anchor direct strict grouping patched")
