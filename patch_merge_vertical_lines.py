from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_code = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> lines = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            for (Text.Line line : block.getLines()) {
                Rect r = line.getBoundingBox();
                String text = cleanSource(line.getText());

                if (r == null) continue;
                if (text.length() < 2) continue;
                if (!containsJpOrZh(text)) continue;

                Rect rr = new Rect(
                        r.left / 2,
                        r.top / 2,
                        r.right / 2,
                        r.bottom / 2
                );

                lines.add(new OcrItem(rr, text));
            }
        }

        ArrayList<OcrItem> merged = mergeVerticalLines(lines);

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;
        for (OcrItem item : merged) {
            addTextBox(item.rect, item.text);
            count++;
            if (count >= 35) break;
        }
    }

    private ArrayList<OcrItem> mergeVerticalLines(ArrayList<OcrItem> lines) {
        ArrayList<OcrItem> sorted = new ArrayList<>(lines);

        // 위쪽부터 처리. 같은 높이면 오른쪽부터.
        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 40) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        ArrayList<OcrItem> merged = new ArrayList<>();

        for (OcrItem cur : sorted) {
            boolean added = false;

            for (OcrItem m : merged) {
                int dx = Math.abs(cur.rect.centerX() - m.rect.centerX());
                int verticalGap = cur.rect.top - m.rect.bottom;

                boolean sameColumn = dx < 35;
                boolean below = verticalGap >= -15;
                boolean closeVertically = verticalGap < 130;

                if (sameColumn && below && closeVertically) {
                    m.text = m.text + "\n" + cur.text;
                    m.rect.union(cur.rect);
                    added = true;
                    break;
                }
            }

            if (!added) {
                merged.add(new OcrItem(new Rect(cur.rect), cur.text));
            }
        }

        merged.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 80) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        return merged;
    }

'''

if start == -1 or end == -1:
    print("handleText 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("vertical line merge patch complete")
