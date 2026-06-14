from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# addView(overlay, params) 직전에 params.flags를 강제로 덮어쓰기
pattern = r'(\w+)\.addView\(overlay,\s*(\w+)\);'

def repl(m):
    wm = m.group(1)
    lp = m.group(2)
    return f'''
        {lp}.flags =
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                | WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS;

        {wm}.addView(overlay, {lp});'''

s = re.sub(pattern, repl, s)

p.write_text(s)
print("overlay flags forced before addView")
