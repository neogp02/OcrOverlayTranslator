from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(Text result, String lang)")
end = s.find("\n    private ArrayList<OcrItem> groupElementsForBubbles", start)

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

        int max = Math.min(groups.size(), 60);

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

'''

if start == -1 or end == -1:
    print("handleText 위치 못 찾음")
else:
    s = s[:start] + new_handle + s[end:]

p.write_text(s)
print("translation panel enabled")
