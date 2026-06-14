from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 1) 필드 추가: 별도 패널 뷰
if "private android.widget.ScrollView bottomPanel;" not in s:
    s = s.replace(
        "private FrameLayout overlay;",
        "private FrameLayout overlay;\n    private android.widget.ScrollView bottomPanel;"
    )

# 2) addBottomPanel 전체 교체
start = s.find("private void addBottomPanel(String text)")
end = s.find("\n    private void", start + 1)

new_panel = r'''
    private void addBottomPanel(String text) {
        text = text.replace("\\n", "\n");

        if (wm == null) {
            wm = (WindowManager)getSystemService(WINDOW_SERVICE);
        }

        if (bottomPanel != null) {
            try {
                wm.removeView(bottomPanel);
            } catch (Throwable ignored) {}
            bottomPanel = null;
        }

        bottomPanel = new android.widget.ScrollView(this);
        bottomPanel.setBackgroundColor(0xCC000000);
        bottomPanel.setFillViewport(false);
        bottomPanel.setVerticalScrollBarEnabled(true);
        bottomPanel.setClickable(true);
        bottomPanel.setFocusable(false);

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setPadding(12, 10, 12, 40);
        tv.setSingleLine(false);

        bottomPanel.addView(
                tv,
                new android.widget.ScrollView.LayoutParams(
                        android.widget.ScrollView.LayoutParams.MATCH_PARENT,
                        android.widget.ScrollView.LayoutParams.WRAP_CONTENT
                )
        );

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int panelHeight = Math.min(360, dm.heightPixels / 3);
        int bottomOffset = 160;

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                dm.widthPixels,
                panelHeight,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
        );

        lp.gravity = Gravity.TOP | Gravity.LEFT;
        lp.x = 0;
        lp.y = dm.heightPixels - panelHeight - bottomOffset;

        wm.addView(bottomPanel, lp);
    }

'''

if start == -1 or end == -1:
    print("addBottomPanel 위치 못 찾음")
else:
    s = s[:start] + new_panel + s[end:]

# 3) onDestroy에서 bottomPanel 제거 추가
if "if (bottomPanel != null && wm != null) wm.removeView(bottomPanel);" not in s:
    s = s.replace(
        "if (overlay != null && wm != null) wm.removeView(overlay);",
        """if (overlay != null && wm != null) wm.removeView(overlay);
            if (bottomPanel != null && wm != null) wm.removeView(bottomPanel);"""
    )

p.write_text(s)
print("separate scrollable bottom panel patched")
