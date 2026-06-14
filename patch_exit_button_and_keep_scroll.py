from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# 필드 추가
if "private TextView bottomPanelText;" not in s:
    s = s.replace(
        "private android.widget.ScrollView bottomPanel;",
        """private android.widget.ScrollView bottomPanel;
    private TextView bottomPanelText;
    private TextView closeButton;
    private String lastPanelText = ""; """
    )

# addBottomPanel 교체: 패널을 새로 만들지 않고 텍스트만 갱신
start = s.find("private void addBottomPanel(String text)")
end = s.find("\n    private void", start + 1)

new_panel = r'''
    private void addBottomPanel(String text) {
        text = text.replace("\\n", "\n");

        if (wm == null) {
            wm = (WindowManager)getSystemService(WINDOW_SERVICE);
        }

        // 같은 내용이면 갱신하지 않음: 스크롤 위치 유지
        if (text.equals(lastPanelText) && bottomPanel != null) {
            return;
        }

        lastPanelText = text;

        if (bottomPanel != null && bottomPanelText != null) {
            bottomPanelText.setText(text);
            return;
        }

        bottomPanel = new android.widget.ScrollView(this);
        bottomPanel.setBackgroundColor(0xCC000000);
        bottomPanel.setFillViewport(false);
        bottomPanel.setVerticalScrollBarEnabled(true);
        bottomPanel.setClickable(true);
        bottomPanel.setFocusable(false);

        bottomPanelText = new TextView(this);
        bottomPanelText.setText(text);
        bottomPanelText.setTextSize(10);
        bottomPanelText.setTextColor(Color.WHITE);
        bottomPanelText.setPadding(12, 10, 12, 40);
        bottomPanelText.setSingleLine(false);

        bottomPanel.addView(
                bottomPanelText,
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

        addCloseButton();
    }

'''

if start != -1 and end != -1:
    s = s[:start] + new_panel + s[end:]
else:
    print("addBottomPanel 위치 못 찾음")

# 종료 버튼 함수 추가
if "private void addCloseButton()" not in s:
    insert_pos = s.find("    private void translateAndAdd")
    close_func = r'''
    private void addCloseButton() {
        if (closeButton != null) return;

        if (wm == null) {
            wm = (WindowManager)getSystemService(WINDOW_SERVICE);
        }

        closeButton = new TextView(this);
        closeButton.setText("×");
        closeButton.setTextSize(22);
        closeButton.setTextColor(Color.WHITE);
        closeButton.setGravity(Gravity.CENTER);
        closeButton.setBackgroundColor(0xCCAA0000);
        closeButton.setClickable(true);
        closeButton.setFocusable(false);

        closeButton.setOnClickListener(v -> {
            try {
                stopSelf();
            } catch (Throwable ignored) {}
        });

        DisplayMetrics dm = getResources().getDisplayMetrics();

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                64,
                64,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
        );

        lp.gravity = Gravity.TOP | Gravity.LEFT;
        lp.x = dm.widthPixels - 80;
        lp.y = 90;

        wm.addView(closeButton, lp);
    }

'''
    if insert_pos != -1:
        s = s[:insert_pos] + close_func + s[insert_pos:]
    else:
        pos = s.rfind("}")
        s = s[:pos] + close_func + "\n}"

# onDestroy에서 제거 추가
if "if (closeButton != null && wm != null) wm.removeView(closeButton);" not in s:
    s = s.replace(
        "if (bottomPanel != null && wm != null) wm.removeView(bottomPanel);",
        """if (bottomPanel != null && wm != null) wm.removeView(bottomPanel);
            if (closeButton != null && wm != null) wm.removeView(closeButton);"""
    )

p.write_text(s)
print("exit button + keep scroll patch complete")
