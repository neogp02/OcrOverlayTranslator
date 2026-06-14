from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# groupElementsForBubbles 내부 기준값 수정
s = s.replace(
'''                boolean xClose = xDist <= 92;
                boolean yStartClose = yStartDist <= 42;
                boolean yConnected = yOverlap > -35 || yGap <= 65;
                boolean sizeOk = test.width() <= 165 && test.height() <= 320;

                if (xClose && yStartClose && yConnected && sizeOk) {''',
'''                // 핵심: X 중심 차이가 크면 다른 말풍선으로 분리
                boolean xClose = xDist <= 52;

                // Y 시작점은 보조 기준으로만 사용
                boolean yStartClose = yStartDist <= 60;

                // 세로로 너무 멀면 분리
                boolean yConnected = yOverlap > -35 || yGap <= 65;

                // 말풍선 하나로 보기엔 너무 큰 영역 방지
                boolean sizeOk = test.width() <= 130 && test.height() <= 320;

                if (xClose && yStartClose && yConnected && sizeOk) {'''
)

p.write_text(s)
print("center-x split rule patched")
