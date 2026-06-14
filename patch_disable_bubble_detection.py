from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 1. 그룹 후 말풍선 찾기 제거: OCR rect 그대로 사용
s = s.replace(
'''Rect bubbleRect = findWhiteBubbleRect(g.rect);
            if (bubbleRect == null) {
                bubbleRect = g.rect;
            }

            translateAndAdd(bubbleRect, g.text, lang);''',
'''translateAndAdd(g.rect, g.text, lang);'''
)

# 2. 혹시 남아있는 element 단계 말풍선 필터 제거
s = s.replace(
'''// 하얀 말풍선 내부가 아니면 제외
Rect bubbleCheck = findWhiteBubbleRect(rr);
if (bubbleCheck == null) continue;

items.add(new OcrItem(rr, src));''',
'''items.add(new OcrItem(rr, src));'''
)

# 3. addTextBox는 OCR rect 기준, 높이 제한 유지
start = s.find("private void addTextBox(Rect r, String text)")
end = s.find("@Override\n    public void onDestroy", start)

new_add = r'''
    private void addTextBox(Rect r, String text) {
        if (text == null) return;

        text = text.trim();
        if (text.length() == 0) return;

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(6, 4, 6, 4);
        tv.setMaxLines(10);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int w = Math.max(70, r.width() + 35);
        int h = Math.max(55, r.height() + 30);

        // 너무 큰 박스 방지
        if (w > 150) w = 150;
        if (h > 150) h = 150;

        int x = Math.max(0, r.left - 3);
        int y = Math.max(0, r.top - 3);

        if (x + w > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - w - 3);
        }

        if (y + h > dm.heightPixels) {
            y = Math.max(0, dm.heightPixels - h - 3);
        }

        Rect newBox = new Rect(x, y, x + w, y + h);

        // 겹침 제거는 유지하되 여유는 작게
        for (Rect old : placedBoxes) {
            Rect padded = new Rect(old.left - 2, old.top - 2, old.right + 2, old.bottom + 2);
            if (Rect.intersects(newBox, padded)) {
                return;
            }
        }

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(w, h);
        fp.leftMargin = x;
        fp.topMargin = y;

        overlay.addView(tv, fp);
        placedBoxes.add(newBox);
    }

'''

if start == -1 or end == -1:
    print("addTextBox 함수 위치 못 찾음")
else:
    s = s[:start] + new_add + s[end:]

p.write_text(s)
print("bubble detection disabled")
