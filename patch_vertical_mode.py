from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# handleText 함수 교체
start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_handle = r'''
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> items = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            for (Text.Line line : block.getLines()) {
                for (Text.Element element : line.getElements()) {
                    Rect r = element.getBoundingBox();
                    String src = cleanSource(element.getText());

                    if (r == null) continue;

                    String compact = src.replace("\n", "").replace(" ", "").replace("　", "").trim();
                    if (compact.length() < 1) continue;

                    if (!containsJpOrZh(src)) continue;

                    // 너무 작은 잡점 제거
                    if (r.width() < 6 || r.height() < 6) continue;

                    items.add(new OcrItem(new Rect(r), src));
                }
            }
        }

        if (items.size() == 0) {
            overlay.removeAllViews();
            placedBoxes.clear();
            return;
        }

        ArrayList<OcrItem> groups = groupVerticalItems(items);

        StringBuilder keyBuilder = new StringBuilder(lang);
        for (OcrItem g : groups) keyBuilder.append("|").append(g.text);
        String key = keyBuilder.toString();

        if (key.equals(lastKey)) return;
        lastKey = key;

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;

        for (OcrItem g : groups) {
            String compact = g.text.replace("\n", "").replace(" ", "").replace("　", "").trim();
            if (compact.length() < 3) continue;

            translateAndAdd(g.rect, g.text, lang);

            count++;
            if (count >= 4) break;
        }
    }

    private ArrayList<OcrItem> groupVerticalItems(ArrayList<OcrItem> items) {
        ArrayList<ArrayList<OcrItem>> columns = new ArrayList<>();

        // 1. x좌표가 가까운 것끼리 같은 세로 열로 묶음
        for (OcrItem item : items) {
            boolean added = false;

            for (ArrayList<OcrItem> col : columns) {
                int avgX = 0;
                for (OcrItem c : col) avgX += c.rect.centerX();
                avgX /= col.size();

                if (Math.abs(avgX - item.rect.centerX()) < 28) {
                    col.add(item);
                    added = true;
                    break;
                }
            }

            if (!added) {
                ArrayList<OcrItem> col = new ArrayList<>();
                col.add(item);
                columns.add(col);
            }
        }

        // 2. 열 내부는 위 -> 아래
        for (ArrayList<OcrItem> col : columns) {
            col.sort((a, b) -> Integer.compare(a.rect.top, b.rect.top));
        }

        // 3. 열은 오른쪽 -> 왼쪽
        columns.sort((a, b) -> {
            int ax = 0;
            int bx = 0;
            for (OcrItem i : a) ax += i.rect.centerX();
            for (OcrItem i : b) bx += i.rect.centerX();
            ax /= a.size();
            bx /= b.size();
            return Integer.compare(bx, ax);
        });

        ArrayList<OcrItem> groups = new ArrayList<>();
        boolean[] usedCol = new boolean[columns.size()];

        // 4. 가까운 열끼리 하나의 말풍선 그룹으로 병합
        for (int i = 0; i < columns.size(); i++) {
            if (usedCol[i]) continue;

            ArrayList<ArrayList<OcrItem>> groupCols = new ArrayList<>();
            groupCols.add(columns.get(i));
            usedCol[i] = true;

            Rect base = rectOfColumn(columns.get(i));

            boolean changed = true;
            while (changed) {
                changed = false;

                for (int j = 0; j < columns.size(); j++) {
                    if (usedCol[j]) continue;

                    Rect r = rectOfColumn(columns.get(j));

                    int gapX = Math.max(0, Math.max(base.left, r.left) - Math.min(base.right, r.right));
                    int overlapY = Math.min(base.bottom, r.bottom) - Math.max(base.top, r.top);

                    // 같은 말풍선 안의 옆 열이라고 판단
                    if (gapX < 80 && overlapY > -40) {
                        groupCols.add(columns.get(j));
                        base.union(r);
                        usedCol[j] = true;
                        changed = true;
                    }
                }
            }

            // 그룹 내부 열도 다시 오른쪽 -> 왼쪽
            groupCols.sort((a, b) -> {
                int ax = avgX(a);
                int bx = avgX(b);
                return Integer.compare(bx, ax);
            });

            StringBuilder sb = new StringBuilder();
            Rect area = null;

            for (ArrayList<OcrItem> col : groupCols) {
                col.sort((a, b) -> Integer.compare(a.rect.top, b.rect.top));

                StringBuilder colText = new StringBuilder();
                for (OcrItem item : col) {
                    colText.append(cleanSource(item.text));
                }

                if (sb.length() > 0) sb.append("\n");
                sb.append(colText.toString());

                Rect cr = rectOfColumn(col);
                if (area == null) area = new Rect(cr);
                else area.union(cr);
            }

            String text = sb.toString().trim();

            if (area != null && text.length() > 0) {
                groups.add(new OcrItem(area, text));
            }
        }

        // 화면상 위쪽 그룹부터 표시
        groups.sort((a, b) -> {
            int dy = Integer.compare(a.rect.top, b.rect.top);
            if (dy != 0) return dy;
            return Integer.compare(b.rect.right, a.rect.right);
        });

        return groups;
    }

    private int avgX(ArrayList<OcrItem> col) {
        int x = 0;
        for (OcrItem i : col) x += i.rect.centerX();
        return x / Math.max(1, col.size());
    }

    private Rect rectOfColumn(ArrayList<OcrItem> col) {
        Rect r = new Rect(col.get(0).rect);
        for (OcrItem i : col) r.union(i.rect);
        return r;
    }

'''

s = s[:start] + new_handle + s[end:]

p.write_text(s)
print("vertical mode patched")
