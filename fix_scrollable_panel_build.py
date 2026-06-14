from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("private void addBottomPanel(String text)")
end = s.find("\n    private void", start + 1)

new_code = r'''
    private void addBottomPanel(String text) {
        android.widget.ScrollView scroll = new android.widget.ScrollView(this);
        scroll.setBackgroundColor(0xCC000000);
        scroll.setFillViewport(false);

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setPadding(12, 10, 12, 10);
        tv.setSingleLine(false);

        scroll.addView(
                tv,
                new android.widget.ScrollView.LayoutParams(
                        android.widget.ScrollView.LayoutParams.MATCH_PARENT,
                        android.widget.ScrollView.LayoutParams.WRAP_CONTENT
                )
        );

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int panelHeight = Math.min(260, dm.heightPixels / 4);
        int bottomOffset = 200;

        FrameLayout.LayoutParams fp =
                new FrameLayout.LayoutParams(
                        dm.widthPixels,
                        panelHeight
                );

        fp.leftMargin = 0;
        fp.topMargin =
                dm.heightPixels
                - panelHeight
                - bottomOffset;

        overlay.addView(scroll, fp);
    }

'''

if start == -1 or end == -1:
    print("addBottomPanel 위치를 못 찾음")
else:
    s = s[:start] + new_code + s[end:]

p.write_text(s)
print("scroll panel build fix complete")
