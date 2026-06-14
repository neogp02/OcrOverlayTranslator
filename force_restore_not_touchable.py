from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# ScrollView 관련 터치 속성 제거
s = s.replace("scroll.setClickable(true);", "scroll.setClickable(false);")
s = s.replace("scroll.setFocusable(true);", "scroll.setFocusable(false);")

# 모든 WindowManager.LayoutParams 플래그에 FLAG_NOT_TOUCHABLE 강제 추가
s = re.sub(
    r'(WindowManager\.LayoutParams\.FLAG_NOT_FOCUSABLE)(?!\s*\|)',
    r'\1 | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE',
    s
)

# 중복 정리
s = s.replace(
    "WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE",
    "WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE"
)

p.write_text(s)
print("forced FLAG_NOT_TOUCHABLE restored")
