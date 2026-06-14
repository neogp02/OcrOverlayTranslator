from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void handleText(Text result, String lang)")
end = s.find("\n    private ArrayList<OcrItem> groupPanelItemsLoose", start)

new_handle = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> items = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect r = block.getBoundingBox();

            // 우선 ML Kit 원본 block text를 그대로 사용
            String text = cleanSourceKeepLines(block.getText());

            if (r == null) continue;
            if (text.length() < 2) continue;
            if (!containsJpOrZh(text)) continue;

            Rect rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
            items.add(new OcrItem(rr, text));
        }

        // 화면 읽기 순서: 위쪽 먼저, 같은 높이면 오른쪽 먼저
        items.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 90) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        overlay.removeAllViews();
        placedBoxes.clear();

        StringBuilder panel = new StringBuilder();

        int max = Math.min(items.size(), 40);

        for (int i = 0; i < max; i++) {
            panel.append("[")
                    .append(i + 1)
                    .append("]\n")
                    .append(items.get(i).text)
                    .append("\n\n");
        }

        addBottomPanel(panel.toString());
    }

'''

if start == -1 or end == -1:
    print("handleText 교체 위치 못 찾음")
else:
    s = s[:start] + new_handle + s[end:]

# cleanSourceKeepLines 추가
if "private String cleanSourceKeepLines(String s)" not in s:
    pos = s.find("private String cleanSource")
    helper = r'''
    private String cleanSourceKeepLines(String s) {
        if (s == null) return "";

        return s
                .replace("\r", "")
                .replace(" ", "")
                .trim();
    }

'''
    if pos != -1:
        s = s[:pos] + helper + s[pos:]
    else:
        pos = s.rfind("}")
        s = s[:pos] + helper + "\n}"

p.write_text(s)
print("raw block panel no translate patched")
