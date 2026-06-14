from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 번역 호출 부분을 OCR 원문 표시로 강제 변경
start = s.find("private void translateAndAdd")
end = s.find("private void addTextBox", start)

new_func = r'''
    private void translateAndAdd(Rect r, String src, String lang) {
        String out = "[OCR]\n" + src;
        addTextBox(r, out);
    }

'''

if start == -1 or end == -1:
    print("translateAndAdd 함수 위치를 못 찾음")
else:
    s = s[:start] + new_func + s[end:]

p.write_text(s)
print("OCR debug only patch complete")
