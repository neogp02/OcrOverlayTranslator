from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# groupElementsForBubbles의 out.add 부분을 멤버 좌표 포함 형태로 변경
old = '''            if (text.trim().length() > 0) {
                out.add(new OcrItem(r, text.trim()));
            }'''

new = '''            if (text.trim().length() > 0) {
                StringBuilder dbg = new StringBuilder();
                dbg.append(text.trim()).append("\\n");

                dbg.append("---- members ----\\n");
                for (OcrItem m : g) {
                    dbg.append("L=").append(m.rect.left)
                            .append(" T=").append(m.rect.top)
                            .append(" R=").append(m.rect.right)
                            .append(" B=").append(m.rect.bottom)
                            .append(" W=").append(m.rect.width())
                            .append(" H=").append(m.rect.height())
                            .append(" :: ")
                            .append(m.text)
                            .append("\\n");
                }

                out.add(new OcrItem(r, dbg.toString().trim()));
            }'''

if old not in s:
    print("교체 패턴 못 찾음")
else:
    s = s.replace(old, new, 1)

p.write_text(s)
print("group member debug patched")
