from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# OcrItem 중복 추가 방지
if "static class OcrItem" not in s:
    pos = s.find("public class OverlayOcrService")
    brace = s.find("{", pos)
    helper = '''
    static class OcrItem {
        Rect rect;
        String text;
        OcrItem(Rect r, String t) {
            rect = r;
            text = t;
        }
    }

'''
    s = s[:brace+1] + helper + s[brace+1:]

# import 보강
if "import java.util.ArrayList;" not in s:
    s = s.replace("import java.util.HashMap;", "import java.util.ArrayList;\nimport java.util.HashMap;")
if "import java.util.List;" not in s:
    s = s.replace("import java.util.Map;", "import java.util.Map;\nimport java.util.List;")

# handleText 교체
start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_handle = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> items = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect r = block.getBoundingBox();
            String src = cleanSource(block.getText());

            if (r == null || src.length() < 2) continue;
            if (!containsJpOrZh(src)) continue;
            if (src.matches("[0-9!?！？♡☆★・…\\s]+")) continue;
            if (r.width() < 18 || r.height() < 18) continue;

            items.add(new OcrItem(new Rect(r), src));
        }

        if (items.size() == 0) {
            overlay.removeAllViews();
            placedBoxes.clear();
            return;
        }

        ArrayList<OcrItem> groups = groupOcrItems(items);

        StringBuilder keyBuilder = new StringBuilder(lang);
        for (OcrItem g : groups) keyBuilder.append("|").append(g.text);
        String key = keyBuilder.toString();

        if (key.equals(lastKey)) return;
        lastKey = key;

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;
        for (OcrItem g : groups) {
            if (g.text.length() < 2) continue;
            translateAndAdd(g.rect, g.text, lang);
            count++;
            if (count >= 4) break;
        }
    }

    private ArrayList<OcrItem> groupOcrItems(ArrayList<OcrItem> items) {
        ArrayList<OcrItem> result = new ArrayList<>();
        boolean[] used = new boolean[items.size()];

        for (int i = 0; i < items.size(); i++) {
            if (used[i]) continue;

            Rect base = new Rect(items.get(i).rect);
            ArrayList<OcrItem> group = new ArrayList<>();
            group.add(items.get(i));
            used[i] = true;

            boolean changed = true;
            while (changed) {
                changed = false;

                for (int j = 0; j < items.size(); j++) {
                    if (used[j]) continue;

                    Rect r = items.get(j).rect;

                    int gapX = Math.max(0, Math.max(base.left, r.left) - Math.min(base.right, r.right));
                    int gapY = Math.max(0, Math.max(base.top, r.top) - Math.min(base.bottom, r.bottom));

                    boolean nearVerticalColumn =
                            Math.abs(base.centerX() - r.centerX()) < 90 && gapY < 140;

                    boolean nearHorizontalLine =
                            Math.abs(base.centerY() - r.centerY()) < 70 && gapX < 160;

                    boolean insideNearby =
                            gapX < 80 && gapY < 120;

                    if (nearVerticalColumn || nearHorizontalLine || insideNearby) {
                        group.add(items.get(j));
                        base.union(r);
                        used[j] = true;
                        changed = true;
                    }
                }
            }

            String merged = mergeGroupText(group);
            if (merged.length() >= 2) {
                result.add(new OcrItem(base, merged));
            }
        }

        result.sort((a, b) -> {
            int dy = Integer.compare(a.rect.top, b.rect.top);
            if (dy != 0) return dy;
            return Integer.compare(a.rect.left, b.rect.left);
        });

        return result;
    }

    private String mergeGroupText(ArrayList<OcrItem> group) {
        if (group.size() == 0) return "";

        Rect area = new Rect(group.get(0).rect);
        for (OcrItem item : group) area.union(item.rect);

        boolean vertical = area.height() > area.width() * 1.15f;

        if (vertical) {
            group.sort((a, b) -> {
                int dx = Integer.compare(a.rect.left, b.rect.left);
                if (Math.abs(a.rect.left - b.rect.left) > 40) return dx;
                return Integer.compare(a.rect.top, b.rect.top);
            });
        } else {
            group.sort((a, b) -> {
                int dy = Integer.compare(a.rect.top, b.rect.top);
                if (Math.abs(a.rect.top - b.rect.top) > 35) return dy;
                return Integer.compare(a.rect.left, b.rect.left);
            });
        }

        StringBuilder sb = new StringBuilder();
        for (OcrItem item : group) {
            String t = cleanSource(item.text);
            if (t.length() == 0) continue;

            if (vertical) {
                sb.append(t.replace("\n", ""));
            } else {
                if (sb.length() > 0) sb.append("\n");
                sb.append(t);
            }
        }

        return sb.toString().trim();
    }

'''

s = s[:start] + new_handle + s[end:]

# cleanSource 강화
start2 = s.find("private String cleanSource")
end2 = s.find("private boolean containsJpOrZh", start2)

new_clean = r'''
    private String cleanSource(String s) {
        if (s == null) return "";
        return s
                .replace("|", "")
                .replace("｜", "")
                .replace("　", "")
                .replace(" ", "")
                .replace("...", "")
                .replace("…", "")
                .replace("\n\n", "\n")
                .trim();
    }

'''

s = s[:start2] + new_clean + s[end2:]

p.write_text(s)
print("patched group OCR")
