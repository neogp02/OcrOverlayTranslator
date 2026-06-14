from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 진한 오버레이 배경을 낮은 투명도로 변경
s = s.replace("0xE6000000", "0x66000000")
s = s.replace("0xDD000000", "0x66000000")
s = s.replace("0xCC000000", "0x66000000")

# 루트 오버레이 자체도 클릭 불가 명시
if "overlay.setClickable(false);" not in s:
    s = s.replace(
        "overlay = new FrameLayout(this);",
        "overlay = new FrameLayout(this);\n        overlay.setClickable(false);\n        overlay.setFocusable(false);\n        overlay.setEnabled(false);"
    )

# flags 강제 확인
s = s.replace(
    "WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE",
    "WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE"
)

# 중복 정리
while "FLAG_NOT_TOUCHABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE" in s:
    s = s.replace(
        "FLAG_NOT_TOUCHABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE",
        "FLAG_NOT_TOUCHABLE"
    )

p.write_text(s)
print("overlay opacity lowered and touch passthrough reinforced")
