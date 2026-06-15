from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 1) groupElementsForBubbles 안의 members 디버그 제거
pattern = r'''if \(text\.trim\(\)\.length\(\) > 0\) \{
\s*StringBuilder dbg = new StringBuilder\(\);
\s*dbg\.append\(text\.trim\(\)\)\.append\("\\n"\);
\s*dbg\.append\("---- members ----\\n"\);
\s*for \(OcrItem m : g\) \{
.*?
\s*out\.add\(new OcrItem\(r, dbg\.toString\(\)\.trim\(\)\)\);
\s*\}'''

replacement = '''if (text.trim().length() > 0) {
                out.add(new OcrItem(r, text.trim()));
            }'''

s = re.sub(pattern, replacement, s, flags=re.DOTALL)

# 2) 혹시 남아있는 members 문자열 안전 제거
s = s.replace('dbg.append("---- members ----\\n");', '')
s = s.replace('---- members ----', '')

# 3) handleText 안에서 src에 디버그가 섞였을 때 잘라내는 안전장치
s = s.replace(
'''            srcs[i] = groups.get(i).text;
            trans[i] = "번역 중...";''',
'''            String clean = groups.get(i).text;
            int cut = clean.indexOf("---- members ----");
            if (cut >= 0) clean = clean.substring(0, cut).trim();

            srcs[i] = clean;
            trans[i] = "번역 중...";'''
)

# 4) 번역 결과 갱신 시 깜빡임 완화: 매 번역마다 패널 갱신하지 않고 마지막 번역 때만 갱신
s = s.replace(
'''            translateForPanel(srcs[i], lang, translated -> {
                trans[idx] = translated;
                addBottomPanel(buildPanelText(srcs, trans));
            });''',
'''            translateForPanel(srcs[i], lang, translated -> {
                trans[idx] = translated;

                // 깜빡임 완화: 마지막 번역 완료 시에만 패널 갱신
                if (idx == max - 1) {
                    addBottomPanel(buildPanelText(srcs, trans));
                }
            });'''
)

p.write_text(s)
print("clean translate panel patched")
