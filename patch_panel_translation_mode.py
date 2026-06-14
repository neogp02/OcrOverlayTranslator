from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(")
end = s.find("private void addNumberMarker", start)

new_code = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> items = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect r = block.getBoundingBox();
            String text = cleanSource(orderedBlockText(block));

            if (r == null) continue;
            if (text.length() < 2) continue;
            if (!containsJpOrZh(text)) continue;

            Rect rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
            items.add(new OcrItem(rr, text));
        }

        ArrayList<OcrItem> groups = groupPanelItemsLoose(items);

        groups.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 90) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        overlay.removeAllViews();
        placedBoxes.clear();

        int max = Math.min(groups.size(), 25);

        String[] srcs = new String[max];
        String[] trans = new String[max];

        for (int i = 0; i < max; i++) {
            srcs[i] = groups.get(i).text;
            trans[i] = "번역 중...";
        }

        addBottomPanel(buildPanelText(srcs, trans));

        for (int i = 0; i < max; i++) {
            final int idx = i;
            translateForPanel(srcs[i], lang, translated -> {
                trans[idx] = translated;
                addBottomPanel(buildPanelText(srcs, trans));
            });
        }
    }

    private ArrayList<OcrItem> groupPanelItemsLoose(ArrayList<OcrItem> items) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(items);

        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 100) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : sorted) {
            boolean added = false;

            for (ArrayList<OcrItem> g : groups) {
                Rect gr = rectOfPanelItems(g);
                Rect test = new Rect(gr);
                test.union(cur.rect);

                int dx = Math.abs(cur.rect.centerX() - gr.centerX());
                int overlapY = Math.min(cur.rect.bottom, gr.bottom) - Math.max(cur.rect.top, gr.top);
                int gapY = Math.max(0, Math.max(cur.rect.top - gr.bottom, gr.top - cur.rect.bottom));

                boolean closeEnoughX = dx < 150;
                boolean relatedY = overlapY > -80 || gapY < 120;
                boolean sizeOk = test.width() < 230 && test.height() < 430;

                if (closeEnoughX && relatedY && sizeOk) {
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
            Rect area = rectOfPanelItems(g);
            String text = orderPanelGroupText(g);

            if (text.trim().length() > 0) {
                out.add(new OcrItem(area, text.trim()));
            }
        }

        return out;
    }

    private String orderPanelGroupText(ArrayList<OcrItem> group) {
        ArrayList<OcrItem> sorted = new ArrayList<>(group);

        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.centerX() - b.rect.centerX()) > 35) {
                return Integer.compare(b.rect.centerX(), a.rect.centerX());
            }
            return Integer.compare(a.rect.top, b.rect.top);
        });

        StringBuilder sb = new StringBuilder();

        for (OcrItem item : sorted) {
            if (sb.length() > 0) sb.append("\n");
            sb.append(item.text);
        }

        return sb.toString();
    }

    private Rect rectOfPanelItems(ArrayList<OcrItem> items) {
        Rect r = new Rect(items.get(0).rect);

        for (OcrItem item : items) {
            r.union(item.rect);
        }

        return r;
    }

    private String buildPanelText(String[] srcs, String[] trans) {
        StringBuilder sb = new StringBuilder();

        for (int i = 0; i < srcs.length; i++) {
            int n = i + 1;

            sb.append("[")
                    .append(n)
                    .append("] 원문\n")
                    .append(srcs[i])
                    .append("\n\n");

            sb.append("[")
                    .append(n)
                    .append("] 번역\n")
                    .append(trans[i])
                    .append("\n\n");
        }

        return sb.toString();
    }

    private interface PanelTranslateCallback {
        void onDone(String text);
    }

    private void translateForPanel(String src, String lang, PanelTranslateCallback cb) {
        if (src == null || src.trim().length() == 0) {
            cb.onDone("");
            return;
        }

        try {
            if ("zh".equals(lang) && zhTranslator != null) {
                zhTranslator.translate(src)
                        .addOnSuccessListener(cb::onDone)
                        .addOnFailureListener(e -> cb.onDone(src));
            } else if (jpTranslator != null) {
                jpTranslator.translate(src)
                        .addOnSuccessListener(cb::onDone)
                        .addOnFailureListener(e -> cb.onDone(src));
            } else {
                cb.onDone(src);
            }
        } catch (Throwable t) {
            cb.onDone(src);
        }
    }

'''

if start == -1 or end == -1:
    print("handleText 교체 위치 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("panel translation mode patched")
