from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# translateForPanel 내부에서 번역 입력값 보정
s = s.replace(
'''        try {
            if ("zh".equals(lang) && zhTranslator != null) {''',
'''        String fixedSrc = normalizeForTranslate(src);

        try {
            if ("zh".equals(lang) && zhTranslator != null) {'''
)

s = s.replace("zhTranslator.translate(src)", "zhTranslator.translate(fixedSrc)")
s = s.replace("jpTranslator.translate(src)", "jpTranslator.translate(fixedSrc)")

# 함수 추가
if "private String normalizeForTranslate(String s)" not in s:
    pos = s.find("    private interface PanelTranslateCallback")
    helper = r'''
    private String normalizeForTranslate(String s) {
        if (s == null) return "";

        String t = s;

        // ML Kit OCR 자주 나는 오인식 보정
        t = t.replace("時距", "時間");
        t = t.replace("時臣", "時間");
        t = t.replace("時距が", "時間が");

        // 만화/구어체 보정
        t = t.replace("アガリ時間", "上がり時間");
        t = t.replace("あがり時間", "上がり時間");
        t = t.replace("出待ち?", "出待ち？");

        // 줄바꿈은 번역기에 문장 경계로 전달
        t = t.replace("\n", "。");

        return t.trim();
    }

'''
    s = s[:pos] + helper + s[pos:]

p.write_text(s)
print("translate normalize patch complete")
