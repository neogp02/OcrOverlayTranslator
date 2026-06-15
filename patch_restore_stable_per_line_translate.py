from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# lastSourceKey 필드 추가
if "private String lastSourceKey" not in s:
    s = s.replace(
        'private String lastPanelText = "";',
        'private String lastPanelText = "";\n    private String lastSourceKey = "";'
    )

start = s.find("    private void handleText(Text result, String lang)")
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

        int max = Math.min(groups.size(), 60);
        if (max <= 0) return;

        String[] srcs = new String[max];
        String[] trans = new String[max];

        StringBuilder keyBuilder = new StringBuilder();

        for (int i = 0; i < max; i++) {
            String clean = groups.get(i).text;
            int cut = clean.indexOf("---- members ----");
            if (cut >= 0) clean = clean.substring(0, cut).trim();

            srcs[i] = clean;
            trans[i] = "";

            keyBuilder.append(i).append(":").append(clean).append("\n");
        }

        String sourceKey = keyBuilder.toString();

        // 같은 페이지/같은 OCR 결과면 재번역하지 않음
        if (sourceKey.equals(lastSourceKey)) {
            return;
        }

        lastSourceKey = sourceKey;
        lastPanelText = "";

        overlay.removeAllViews();
        placedBoxes.clear();

        final java.util.concurrent.atomic.AtomicInteger doneCount =
                new java.util.concurrent.atomic.AtomicInteger(0);

        for (int i = 0; i < max; i++) {
            final int idx = i;

            translateForPanel(srcs[i], lang, translated -> {
                trans[idx] = translated;

                if (doneCount.incrementAndGet() >= max) {
                    String panelText = buildPanelText(srcs, trans);

                    if (!panelText.equals(lastPanelText)) {
                        lastPanelText = panelText;
                        addBottomPanel(panelText);
                    }
                }
            });
        }
    }

'''

if start == -1 or end == -1:
    print("handleText 위치 못 찾음")
else:
    s = s[:start] + new_handle + s[end:]
    p.write_text(s)
    print("stable per-line translate restored")
