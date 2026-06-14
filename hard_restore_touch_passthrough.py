from pathlib import Path
import re

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# createOverlay 함수 전체 교체
start = s.find("private void createOverlay()")
end = s.find("private void showStatus", start)

new_create = r'''
    private void createOverlay() {
        wm = (WindowManager)getSystemService(WINDOW_SERVICE);

        overlay = new FrameLayout(this);
        overlay.setBackgroundColor(Color.TRANSPARENT);
        overlay.setClickable(false);
        overlay.setFocusable(false);
        overlay.setEnabled(false);

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                        | WindowManager.LayoutParams.FLAG_NOT_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
        );

        wm.addView(overlay, lp);
    }

'''

if start == -1 or end == -1:
    print("createOverlay 위치 못 찾음")
else:
    s = s[:start] + new_create + s[end:]

# ScrollView 제거: addBottomPanel을 터치 안 받는 TextView로 고정
start = s.find("private void addBottomPanel(String text)")
end = s.find("\n    private void", start + 1)

new_panel = r'''
    private void addBottomPanel(String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0x66000000);
        tv.setPadding(12, 10, 12, 10);
        tv.setMaxLines(8);
        tv.setSingleLine(false);
        tv.setClickable(false);
        tv.setFocusable(false);
        tv.setEnabled(false);

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

# ScrollView 잔여물 제거/무력화는 하지 않고 함수 교체로 차단
p.write_text(s)
print("hard touch passthrough restored")
