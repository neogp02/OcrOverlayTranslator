from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 1) 오버레이가 터치를 못 받게 하는 플래그 제거: 스크롤 가능하게
s = s.replace(" | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE", "")
s = s.replace("WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE | ", "")
s = s.replace("WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE", "0")

# 2) block.getText() 대신 세로쓰기 줄 순서 보정 함수 사용
s = s.replace(
    "String text = cleanSource(block.getText());",
    "String text = cleanSource(orderedBlockText(block));"
)

# 3) addBottomPanel을 ScrollView 버전으로 교체
start = s.find("private void addBottomPanel(String text)")
end = s.find("\n    private void", start + 1)

new_panel = r'''
    private void addBottomPanel(String text) {
        android.widget.ScrollView scroll = new android.widget.ScrollView(this);
        scroll.setBackgroundColor(0xCC000000);
        scroll.setFillViewport(false);
        scroll.setVerticalScrollBarEnabled(true);
        scroll.setClickable(true);
        scroll.setFocusable(true);

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setPadding(12, 10, 12, 40);
        tv.setSingleLine(false);

        scroll.addView(
                tv,
                new android.widget.ScrollView.LayoutParams(
                        android.widget.ScrollView.LayoutParams.MATCH_PARENT,
                        android.widget.ScrollView.LayoutParams.WRAP_CONTENT
                )
        );

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int panelHeight = Math.min(280, dm.heightPixels / 4);
        int bottomOffset = 170;

        FrameLayout.LayoutParams fp =
                new FrameLayout.LayoutParams(dm.widthPixels, panelHeight);

        fp.leftMargin = 0;
        fp.topMargin = dm.heightPixels - panelHeight - bottomOffset;

        overlay.addView(scroll, fp);
    }

'''

if start != -1 and end != -1:
    s = s[:start] + new_panel + s[end:]
else:
    print("addBottomPanel 위치 못 찾음")

# 4) orderedBlockText 함수 추가
if "private String orderedBlockText(Text.TextBlock block)" not in s:
    pos = s.find("private String cleanSource")
    helper = r'''
    private String orderedBlockText(Text.TextBlock block) {
        ArrayList<Text.Line> lines = new ArrayList<>(block.getLines());

        lines.sort((a, b) -> {
            Rect ar = a.getBoundingBox();
            Rect br = b.getBoundingBox();

            if (ar == null || br == null) return 0;

            // 세로쓰기: 오른쪽 줄 먼저
            if (Math.abs(ar.centerX() - br.centerX()) > 25) {
                return Integer.compare(br.centerX(), ar.centerX());
            }

            // 같은 줄이면 위에서 아래
            return Integer.compare(ar.top, br.top);
        });

        StringBuilder sb = new StringBuilder();

        for (Text.Line line : lines) {
            String t = line.getText();
            if (t == null) continue;

            if (sb.length() > 0) sb.append(" ");
            sb.append(t);
        }

        return sb.toString();
    }

'''
    if pos != -1:
        s = s[:pos] + helper + s[pos:]
    else:
        pos = s.rfind("}")
        s = s[:pos] + helper + "\n}"

p.write_text(s)
print("panel scroll + vertical order patch complete")
