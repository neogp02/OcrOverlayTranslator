from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

old = '''
        int panelHeight = Math.min(360, dm.heightPixels / 3);

        FrameLayout.LayoutParams fp =
                new FrameLayout.LayoutParams(
                        dm.widthPixels,
                        panelHeight
                );

        fp.leftMargin = 0;
        fp.topMargin = dm.heightPixels - panelHeight;
'''

new = '''
        int panelHeight = Math.min(240, dm.heightPixels / 4);

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
'''

s = s.replace(old, new)

s = s.replace(
    'tv.setBackgroundColor(0xE6000000);',
    'tv.setBackgroundColor(0xCC000000);'
)

p.write_text(s)

print("Bottom panel moved up")
