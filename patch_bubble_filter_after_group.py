from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 1. Element 단계에서 말풍선 필터 제거
s = s.replace(
'''// 하얀 말풍선 내부가 아니면 제외
Rect bubbleCheck = findWhiteBubbleRect(rr);
if (bubbleCheck == null) continue;

items.add(new OcrItem(rr, src));''',
'''items.add(new OcrItem(rr, src));'''
)

# 2. 그룹 단계에서 말풍선 검사하되, 못 찾으면 OCR rect 그대로 사용
s = s.replace(
'''Rect bubbleRect = findWhiteBubbleRect(g.rect);
            if (bubbleRect == null) continue;

            translateAndAdd(bubbleRect, g.text, lang);''',
'''Rect bubbleRect = findWhiteBubbleRect(g.rect);
            if (bubbleRect == null) {
                bubbleRect = g.rect;
            }

            translateAndAdd(bubbleRect, g.text, lang);'''
)

# 3. 흰색 판정 완화
s = s.replace(
'''return max > 215 && min > 190 && (max - min) < 45;''',
'''return max > 200 && min > 170 && (max - min) < 65;'''
)

# 4. 너무 큰 흰색 영역 제한 완화/수정
s = s.replace(
'''if (r.width() > bw * 0.55f || r.height() > bh * 0.45f) continue;
            if (area > bw * bh * 0.20f) continue;''',
'''if (r.width() > bw * 0.70f || r.height() > bh * 0.55f) continue;
            if (area > bw * bh * 0.30f) continue;'''
)

# 5. 말풍선 못 찾은 경우에도 박스가 과도하게 커지지 않게 addTextBox에서 높이 제한
s = s.replace(
'''int w = Math.max(55, r.width());
        int h = Math.max(45, r.height());''',
'''int w = Math.max(55, r.width());
        int h = Math.max(45, r.height());

        if (w > 180) w = 180;
        if (h > 180) h = 180;'''
)

p.write_text(s)
print("bubble filter after grouping patch complete")
