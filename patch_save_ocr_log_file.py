from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

if "import java.io.FileOutputStream;" not in s:
    s = s.replace(
        "import java.util.ArrayList;",
        "import java.io.FileOutputStream;\nimport java.util.ArrayList;"
    )

target = '''Log.d("MLKIT_RAW", result.getText());'''

replace = '''Log.d("MLKIT_RAW", result.getText());

        try {
            FileOutputStream fos = openFileOutput("mlkit_ocr_log.txt", MODE_APPEND);
            String dump = "\\n===== RAW OCR =====\\n" + result.getText() + "\\n";
            fos.write(dump.getBytes());
            fos.close();
        } catch (Exception e) {
            Log.e("MLKIT_RAW", "file write failed", e);
        }'''

if target not in s:
    print("RAW 로그 위치를 못 찾음")
else:
    s = s.replace(target, replace)

p.write_text(s)
print("save OCR log file patch complete")
