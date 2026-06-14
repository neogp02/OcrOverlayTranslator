from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 1) 화면 번호 마커 호출 제거
s = re.sub(r'\n\s*addNumberMarker\(item\.rect,\s*index\);\s*', '\n', s)

# 2) 패널 append 형식 교체
old = '''panel.append(index)
                    .append(". ")
                    .append(item.text.replace("\\n", " "))
                    .append("\\n");'''

new = '''panel.append("[")
                    .append(index)
                    .append("]\\\\n")
                    .append(item.text)
                    .append("\\\\n\\\\n");'''

if old in s:
    s = s.replace(old, new)
else:
    # 기존 형태가 조금 다를 경우 대비
    s = re.sub(
        r'panel\.append\(index\)\s*\.append\("\. "\)\s*\.append\(item\.text\.replace\("\\\\n", " "\)\)\s*\.append\("\\\\n"\);',
        'panel.append("[").append(index).append("]\\\\n").append(item.text).append("\\\\n\\\\n");',
        s
    )

# 3) addNumberMarker 함수는 남아있어도 상관없지만 호출은 안 됨

p.write_text(s)
print("panel-only clean mode patched")
