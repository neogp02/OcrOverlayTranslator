from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

if "private ArrayList<OcrItem> groupElementsForBubbles(" not in s:
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

                int xDist = Math.abs(cur.rect.centerX() - anchor.rect.centerX());
                int yStartDist = Math.abs(cur.rect.top - anchor.rect.top);

                int yOverlap =
                        Math.min(cur.rect.bottom, gr.bottom)
                        - Math.max(cur.rect.top, gr.top);

                int yGap =
                        Math.max(0,
                                Math.max(cur.rect.top - gr.bottom,
                                         gr.top - cur.rect.bottom));

                boolean xClose = xDist <= 92;
                boolean yStartClose = yStartDist <= 42;
                boolean yConnected = yOverlap > -35 || yGap <= 65;
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

    if insert_pos == -1:
        print("insert 위치 못 찾음")
    else:
        s = s[:insert_pos] + helper + s[insert_pos:]
        p.write_text(s)
        print("groupElementsForBubbles added")
else:
    print("already exists")
