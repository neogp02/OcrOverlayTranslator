from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

if "private Rect rectOfItems(ArrayList<OcrItem> items)" not in s:
    marker = "private String cleanSource"
    helper = r'''
    private Rect rectOfItems(ArrayList<OcrItem> items) {
        Rect r = new Rect(items.get(0).rect);
        for (OcrItem item : items) {
            r.union(item.rect);
        }
        return r;
    }

'''
    s = s.replace(marker, helper + marker)

p.write_text(s)
print("rectOfItems restored")
