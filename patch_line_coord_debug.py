from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

old = '''panel.append("[")
                    .append(i + 1)
                    .append("]\\n")
                    .append(groups.get(i).text)
                    .append("\\n\\n");'''

new = '''OcrItem it = groups.get(i);
            panel.append("[")
                    .append(i + 1)
                    .append("] ")
                    .append("L=").append(it.rect.left)
                    .append(" T=").append(it.rect.top)
                    .append(" R=").append(it.rect.right)
                    .append(" B=").append(it.rect.bottom)
                    .append(" W=").append(it.rect.width())
                    .append(" H=").append(it.rect.height())
                    .append("\\n")
                    .append(it.text)
                    .append("\\n\\n");'''

if old not in s:
    print("기존 panel append 패턴 못 찾음")
else:
    s = s.replace(old, new)

p.write_text(s)
print("line coord debug patched")
