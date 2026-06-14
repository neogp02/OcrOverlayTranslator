from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

old = r'''
            group.sort((a, b) -> {
                // 세로쓰기: 오른쪽 열부터 왼쪽 열
                if (Math.abs(a.rect.centerX() - b.rect.centerX()) > 25) {
                    return Integer.compare(b.rect.centerX(), a.rect.centerX());
                }
                return Integer.compare(a.rect.top, b.rect.top);
            });

            StringBuilder sb = new StringBuilder();
            Rect area = rectOfItems(group);

            for (OcrItem item : group) {
                if (sb.length() > 0) sb.append("\n");
                sb.append(item.text);
            }

            out.add(new OcrItem(area, sb.toString().trim()));
'''

new = r'''
            String orderedText = orderVerticalGroupText(group);
            Rect area = rectOfItems(group);

            out.add(new OcrItem(area, orderedText.trim()));
'''

if old not in s:
    print("기존 group.sort 블록을 못 찾음")
else:
    s = s.replace(old, new)

insert_pos = s.find("    private Rect rectOfItems")
helper = r'''
    private String orderVerticalGroupText(ArrayList<OcrItem> group) {
        ArrayList<ArrayList<OcrItem>> columns = new ArrayList<>();

        // X 좌표 기준으로 세로 컬럼 분리
        for (OcrItem item : group) {
            boolean added = false;

            for (ArrayList<OcrItem> col : columns) {
                Rect cr = rectOfItems(col);
                int dx = Math.abs(item.rect.centerX() - cr.centerX());

                if (dx < 38) {
                    col.add(item);
                    added = true;
                    break;
                }
            }

            if (!added) {
                ArrayList<OcrItem> nc = new ArrayList<>();
                nc.add(item);
                columns.add(nc);
            }
        }

        // 컬럼은 오른쪽 → 왼쪽
        columns.sort((a, b) -> {
            Rect ar = rectOfItems(a);
            Rect br = rectOfItems(b);
            return Integer.compare(br.centerX(), ar.centerX());
        });

        StringBuilder sb = new StringBuilder();

        for (ArrayList<OcrItem> col : columns) {
            // 같은 컬럼 내부는 위 → 아래
            col.sort((a, b) -> Integer.compare(a.rect.top, b.rect.top));

            for (OcrItem item : col) {
                if (sb.length() > 0) sb.append("\n");
                sb.append(item.text);
            }
        }

        return sb.toString();
    }

'''

if insert_pos == -1:
    print("rectOfItems 위치를 못 찾음")
else:
    s = s[:insert_pos] + helper + s[insert_pos:]

p.write_text(s)
print("sort group columns patch complete")
