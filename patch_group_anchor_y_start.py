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
            if (Math.abs(a.rect.top - b.rect.top) > 70) {
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

                // 그룹 기준점: 첫 줄의 Y 시작점
                int anchorTop = g.get(0).rect.top;
                int anchorCenterX = g.get(0).rect.centerX();

                int xDist = Math.abs(cur.rect.centerX() - anchorCenterX);
                int yStartDist = Math.abs(cur.rect.top - anchorTop);

                boolean xClose = xDist < 65;

                // 핵심: Y 길이/겹침보다 시작점 우선
                boolean yStartClose = yStartDist < 28;

                // 너무 큰 말풍선 방지
                boolean sizeOk =
                        test.width() < 135 &&
                        test.height() < 260;

                if (xClose && yStartClose && sizeOk) {
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
print("anchor y-start grouping patched")
