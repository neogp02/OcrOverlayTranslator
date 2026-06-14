from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# import 추가
if "import java.util.ArrayDeque;" not in s:
    s = s.replace("import java.util.ArrayList;", "import java.util.ArrayDeque;\nimport java.util.ArrayList;")

# lastScreenBitmap 필드 추가
if "private Bitmap lastScreenBitmap;" not in s:
    s = s.replace(
        'private String lastKey = "";',
        'private String lastKey = "";\n    private Bitmap lastScreenBitmap;'
    )

# 화면 캡처 bitmap 저장
if "lastScreenBitmap = bitmap;" not in s:
    s = s.replace(
        "Bitmap ocrBitmap = Bitmap.createScaledBitmap(",
        "lastScreenBitmap = bitmap;\n\n            Bitmap ocrBitmap = Bitmap.createScaledBitmap("
    )

# OCR element 추가 부분에 말풍선 필터 적용
s = s.replace(
'''items.add(new OcrItem(new Rect(r), src));''',
'''Rect rr = new Rect(r);

// OCR이 2배 확대 좌표로 반환된 경우 보정
if (lastScreenBitmap != null && rr.right > lastScreenBitmap.getWidth()) {
    rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
}

// 하얀 말풍선 내부가 아니면 제외
Rect bubbleCheck = findWhiteBubbleRect(rr);
if (bubbleCheck == null) continue;

items.add(new OcrItem(rr, src));'''
)

# translateAndAdd 호출 전에 말풍선 영역으로 교체
s = s.replace(
'''translateAndAdd(g.rect, g.text, lang);''',
'''Rect bubbleRect = findWhiteBubbleRect(g.rect);
            if (bubbleRect == null) continue;

            translateAndAdd(bubbleRect, g.text, lang);'''
)

# addTextBox 함수 교체: 말풍선 영역보다 크게 표시하지 않음
start = s.find("private void addTextBox(Rect r, String text)")
end = s.find("@Override\n    public void onDestroy", start)

new_add = r'''
    private void addTextBox(Rect r, String text) {
        if (text == null) return;

        text = text.trim();
        if (text.length() == 0) return;

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC000000);
        tv.setPadding(5, 3, 5, 3);
        tv.setMaxLines(8);

        int w = Math.max(55, r.width());
        int h = Math.max(45, r.height());

        if (w < 90 || h < 80) {
            tv.setTextSize(9);
        } else {
            tv.setTextSize(10);
        }

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int x = Math.max(0, r.left);
        int y = Math.max(0, r.top);

        if (x + w > dm.widthPixels) {
            w = dm.widthPixels - x - 2;
        }

        if (y + h > dm.heightPixels) {
            h = dm.heightPixels - y - 2;
        }

        Rect newBox = new Rect(x, y, x + w, y + h);

        for (Rect old : placedBoxes) {
            Rect padded = new Rect(old.left - 3, old.top - 3, old.right + 3, old.bottom + 3);
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

# 하얀 말풍선 검출 함수 추가
insert = s.find("    private void translateAndAdd")
helper = r'''
    private Rect findWhiteBubbleRect(Rect textRect) {
        if (lastScreenBitmap == null || textRect == null) return null;

        int bw = lastScreenBitmap.getWidth();
        int bh = lastScreenBitmap.getHeight();

        int cx = Math.max(0, Math.min(bw - 1, textRect.centerX()));
        int cy = Math.max(0, Math.min(bh - 1, textRect.centerY()));

        int[][] seeds = new int[][] {
                {cx, cy},
                {textRect.left - 4, cy},
                {textRect.right + 4, cy},
                {cx, textRect.top - 4},
                {cx, textRect.bottom + 4},
                {textRect.left - 8, textRect.top - 8},
                {textRect.right + 8, textRect.bottom + 8}
        };

        Rect best = null;

        for (int[] seed : seeds) {
            int sx = Math.max(0, Math.min(bw - 1, seed[0]));
            int sy = Math.max(0, Math.min(bh - 1, seed[1]));

            if (!isWhiteLike(sx, sy)) continue;

            Rect r = floodWhiteRegion(sx, sy);

            if (r == null) continue;

            int area = r.width() * r.height();

            // 너무 작은 영역 제외
            if (r.width() < 25 || r.height() < 25) continue;

            // 페이지 배경처럼 너무 큰 영역 제외
            if (r.width() > bw * 0.55f || r.height() > bh * 0.45f) continue;
            if (area > bw * bh * 0.20f) continue;

            // OCR 글자 영역을 포함하지 않으면 제외
            if (!Rect.intersects(r, textRect)) continue;

            if (best == null || area > best.width() * best.height()) {
                best = r;
            }
        }

        if (best == null) return null;

        // 말풍선 테두리 안쪽만 쓰도록 약간 축소
        best.left = Math.max(0, best.left + 2);
        best.top = Math.max(0, best.top + 2);
        best.right = Math.min(bw, best.right - 2);
        best.bottom = Math.min(bh, best.bottom - 2);

        return best;
    }

    private boolean isWhiteLike(int x, int y) {
        int c = lastScreenBitmap.getPixel(x, y);

        int r = Color.red(c);
        int g = Color.green(c);
        int b = Color.blue(c);

        int max = Math.max(r, Math.max(g, b));
        int min = Math.min(r, Math.min(g, b));

        return max > 215 && min > 190 && (max - min) < 45;
    }

    private Rect floodWhiteRegion(int sx, int sy) {
        int bw = lastScreenBitmap.getWidth();
        int bh = lastScreenBitmap.getHeight();

        boolean[] visited = new boolean[bw * bh];
        ArrayDeque<int[]> q = new ArrayDeque<>();

        q.add(new int[]{sx, sy});
        visited[sy * bw + sx] = true;

        int minX = sx, maxX = sx, minY = sy, maxY = sy;
        int count = 0;
        int limit = Math.max(8000, bw * bh / 8);

        while (!q.isEmpty()) {
            int[] p = q.poll();
            int x = p[0];
            int y = p[1];

            count++;
            if (count > limit) return null;

            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;

            int[][] dirs = new int[][] {
                    {1,0}, {-1,0}, {0,1}, {0,-1}
            };

            for (int[] d : dirs) {
                int nx = x + d[0];
                int ny = y + d[1];

                if (nx < 0 || ny < 0 || nx >= bw || ny >= bh) continue;

                int idx = ny * bw + nx;
                if (visited[idx]) continue;

                visited[idx] = true;

                if (isWhiteLike(nx, ny)) {
                    q.add(new int[]{nx, ny});
                }
            }
        }

        return new Rect(minX, minY, maxX + 1, maxY + 1);
    }

'''

if insert == -1:
    print("translateAndAdd 위치 못 찾음")
else:
    s = s[:insert] + helper + s[insert:]

p.write_text(s)
print("white bubble mode patch complete")
