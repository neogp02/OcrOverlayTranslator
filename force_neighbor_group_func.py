from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private ArrayList<OcrItem> groupElementsForBubbles")
end = s.find("\nprivate ArrayList<OcrItem> groupLinesByXYStart", start)

new_func = r'''
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

                if (test.width() > 150 || test.height() > 330) continue;

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

                    // 인접 세로 컬럼만 같은 말풍선으로 결합
                    boolean neighborColumn = xDist <= 36;

                    // 시작점이 어느 정도 비슷해야 함
                    boolean yStartClose = yStartDist <= 70;

                    // 세로로 너무 떨어져 있으면 분리
                    boolean yConnected = yOverlap > -45 || yGap <= 80;

                    if (neighborColumn && yStartClose && yConnected) {
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
                StringBuilder dbg = new StringBuilder();
                dbg.append(text.trim()).append("\n");
                dbg.append("---- members ----\n");

                for (OcrItem m : g) {
                    dbg.append("L=").append(m.rect.left)
                            .append(" T=").append(m.rect.top)
                            .append(" R=").append(m.rect.right)
                            .append(" B=").append(m.rect.bottom)
                            .append(" W=").append(m.rect.width())
                            .append(" H=").append(m.rect.height())
                            .append(" :: ")
                            .append(m.text)
                            .append("\n");
                }

                out.add(new OcrItem(r, dbg.toString().trim()));
            }
        }

        return out;
    }

'''

if start == -1 or end == -1:
    print("교체 위치 못 찾음")
else:
    s = s[:start] + new_func + s[end:]
    p.write_text(s)
    print("force neighbor group function replaced")
