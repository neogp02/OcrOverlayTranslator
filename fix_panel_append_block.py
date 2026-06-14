from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

pattern = r'''panel\.append\("\["\)
\s*\.append\(index\)
\s*\.append\("\]\s*"\)
\s*\.append\(item\.text\)
\s*\.append\("\\n\\n"\);'''

replacement = '''panel.append("[")
                    .append(index)
                    .append("]\\\\n")
                    .append(item.text)
                    .append("\\\\n\\\\n");'''

s = re.sub(pattern, replacement, s, flags=re.MULTILINE)

# 혹시 위 패턴이 안 잡혔을 경우: for문 내부를 통째로 안전 교체
if 'append("]\\n")' not in s:
    s = re.sub(
        r'''for \(OcrItem item : items\) \{.*?index\+\+;
\s*if \(index > 25\) break;
\s*\}''',
        '''for (OcrItem item : items) {
            panel.append("[")
                    .append(index)
                    .append("]\\\\n")
                    .append(item.text)
                    .append("\\\\n\\\\n");

            index++;
            if (index > 25) break;
        }''',
        s,
        flags=re.DOTALL
    )

p.write_text(s)
print("panel append block fixed")
