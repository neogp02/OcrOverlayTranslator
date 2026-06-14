from pathlib import Path

f = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")

txt = f.read_text()

if "private String cleanSource(" not in txt:

    insert = '''

    private String cleanSource(String s) {
        if (s == null) return "";

        return s
                .replace(" ", "")
                .replace("\\n", "")
                .trim();
    }

    private boolean containsJpOrZh(String s) {
        if (s == null) return false;

        for (char c : s.toCharArray()) {

            if ((c >= 0x3040 && c <= 0x30FF) ||
                (c >= 0x4E00 && c <= 0x9FFF)) {

                return true;
            }
        }

        return false;
    }

'''

    pos = txt.rfind("}")
    txt = txt[:pos] + insert + "\n}"

    f.write_text(txt)

    print("Methods restored.")

else:
    print("Methods already exist.")
