from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

s = s.replace(
    '"\\\\n"',
    '"\\n"'
)

s = s.replace(
    '"\\\\n\\\\n"',
    '"\\n\\n"'
)

p.write_text(s)

print("newline fixed")
