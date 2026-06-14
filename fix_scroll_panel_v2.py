from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 잘못 추가됐을 수 있는 import 제거
s = s.replace("import android.widget.ScrollView;\n", "")

start = s.find("private void addBottomPanel(String text)")
end = s.find("\n    private void", start + 1)

new_code = r'''
    private void addBottomPanel(String text) {
        android.widget.ScrollView scroll = new android.widget.ScrollView(this);
        scroll.setBackgroundColor(0xCC000000);
        scroll.setFillViewport(false);
        scroll.setOverScrollMode(android.view.View.OVER_SCROLL_IF_CONTENT_SCROLLS);

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setPadding(12, 10, 12, 10);
        tv.setSingleLine(false);

        android.view.ViewGroup.LayoutParams childLp =
                new android.view.ViewGroup.LayoutParams(
                        android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                        android.view.ViewGroup.LayoutParams.WRAP_CONTENT
                );

        scroll.addView(tv, childLp);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int panelHeight = Math.min(260, dm.heightPixels / 4);
        int bottomOffset = 200;

        FrameLayout.LayoutParams fp =
                new FrameLayout.LayoutParams(
                        dm.widthPixels,
                        panelHeight
                );

        fp.leftMargin = 0;
        fp.topMargin = dm.heightPixels - panelHeight - bottomOffset;

        overlay.addView(scroll, fp);
    }

'''

if start == -1 or end == -1:
    print("addBottomPanel 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("scroll panel v2 patched")
