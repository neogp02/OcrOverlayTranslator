from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private ArrayList<OcrItem> groupLinesByXYStart")
end = s.find("\n    private Rect rectOfLineGroup", start)

new_code = r'''
    private ArrayList<OcrItem> groupLinesByXYStart(ArrayList<OcrItem> lines) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(lines);

        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 80) {
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

                boolean sizeOk =
                        test.width() < 150 &&
                        test.height() < 300;

                if (!sizeOk) continue;

                boolean pairMatch = false;

                for (OcrItem old : g) {
                    int xDist = Math.abs(cur.rect.centerX() - old.rect.centerX());
                    int yStartDist = Math.abs(cur.rect.top - old.rect.top);

                    int yOverlap =
                            Math.min(cur.rect.bottom, old.rect.bottom)
                            - Math.max(cur.rect.top, old.rect.top);

                    int yGap =
                            Math.max(0,
                                    Math.max(cur.rect.top - old.rect.bottom,
                                             old.rect.top - cur.rect.bottom));

                    boolean xClose = xDist < 75;

                    // 핵심: 말풍선 안 같은 세로열/인접열은 Y 시작점이 비슷해야 함
                    boolean yStartClose = yStartDist < 45;

                    // 너무 멀리 떨어진 줄은 같은 말풍선으로 보지 않음
                    boolean yConnected = yOverlap > -30 || yGap < 55;

                    if (xClose && yStartClose && yConnected) {
                        pairMatch = true;
                        break;
                    }
                }

                if (pairMatch) {
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
print("stricter pair-based line grouping patched")
