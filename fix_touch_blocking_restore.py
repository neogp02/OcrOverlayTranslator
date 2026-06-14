from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 전체 오버레이가 화면 터치를 먹지 않도록 NOT_TOUCHABLE 복구
# flags 위치를 넓게 찾아서 보정
s = s.replace(
    "WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,",
    "WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,"
)

s = s.replace(
    "WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,",
    "WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,"
)

# 스크롤 패널은 일단 안전하게 TextView 고정형으로 되돌림
start = s.find("private void addBottomPanel(String text)")
end = s.find("\n    private void", start + 1)

new_panel = r'''
    private void addBottomPanel(String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC000000);
        tv.setPadding(12, 10, 12, 10);
        tv.setMaxLines(8);
        tv.setSingleLine(false);

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

        overlay.addView(tv, fp);
    }

'''

if start != -1 and end != -1:
    s = s[:start] + new_panel + s[end:]
else:
    print("addBottomPanel 위치 못 찾음")

p.write_text(s)
print("touch blocking restored; scroll panel disabled safely")
