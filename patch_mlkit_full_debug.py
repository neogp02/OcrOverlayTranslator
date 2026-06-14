from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# Log import 추가
if "import android.util.Log;" not in s:
    s = s.replace("import android.util.DisplayMetrics;", "import android.util.DisplayMetrics;\nimport android.util.Log;")

# handleText 시작 부분에 전체 OCR 로그 추가
target = '''private void handleText(Text result, String lang) {
        if (result == null) return;'''

replace = '''private void handleText(Text result, String lang) {
        if (result == null) return;

        Log.d("MLKIT_RAW", "================ RAW OCR START ================");
        Log.d("MLKIT_RAW", result.getText());
        Log.d("MLKIT_RAW", "================ RAW OCR END ==================");

        for (Text.TextBlock block : result.getTextBlocks()) {
            Log.d("MLKIT_BLOCK", "BLOCK=[" + block.getText() + "]");
            for (Text.Line line : block.getLines()) {
                Log.d("MLKIT_LINE", "LINE=[" + line.getText() + "]");
                for (Text.Element element : line.getElements()) {
                    Log.d("MLKIT_ELEMENT", "ELEMENT=[" + element.getText() + "] BOX=" + element.getBoundingBox());
                }
            }
        }'''

if target not in s:
    print("handleText 시작 부분을 못 찾음")
else:
    s = s.replace(target, replace)

p.write_text(s)
print("ML Kit full debug patch complete")
