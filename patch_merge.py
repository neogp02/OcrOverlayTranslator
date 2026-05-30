from pathlib import Path
p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

# ArrayList import 없으면 추가
if "import java.util.ArrayList;" not in s:
    s = s.replace(
        "import java.util.Map;",
        "import java.util.Map;\nimport java.util.ArrayList;\nimport java.util.List;"
    )

# OCR 블록 병합 클래스 추가
insert_point = s.find("public class OverlayOcrService")
brace = s.find("{", insert_point)

helper = '''

    static class OcrItem {
        Rect rect;
        String text;

        OcrItem(Rect r,String t){
            rect=r;
            text=t;
        }
    }

'''

s = s[:brace+1] + helper + s[brace+1:]

# handleText 함수 찾기
start = s.find("private void handleText(")
end = s.find("private String cleanSource", start)

new_handle = r'''
    private void handleText(Text result, String lang) {
        if(result==null) return;

        overlay.removeAllViews();
        placedBoxes.clear();

        ArrayList<OcrItem> items = new ArrayList<>();

        for(Text.TextBlock block : result.getTextBlocks()){

            Rect r = block.getBoundingBox();
            if(r==null) continue;

            String src = cleanSource(block.getText());

            if(src.length()<2) continue;

            if(src.matches("[0-9!?！？♡☆★・…\\s]+"))
                continue;

            if(!containsJpOrZh(src))
                continue;

            if(r.width()<25 || r.height()<18)
                continue;

            items.add(new OcrItem(r,src));
        }

        ArrayList<OcrItem> merged = new ArrayList<>();

        boolean[] used = new boolean[items.size()];

        for(int i=0;i<items.size();i++){

            if(used[i]) continue;

            Rect base = new Rect(items.get(i).rect);
            StringBuilder sb = new StringBuilder(items.get(i).text);

            used[i]=true;

            for(int j=i+1;j<items.size();j++){

                if(used[j]) continue;

                Rect r2 = items.get(j).rect;

                int dx = Math.abs(base.centerX()-r2.centerX());
                int dy = Math.abs(base.centerY()-r2.centerY());

                if(dx<120 && dy<180){

                    sb.append("\n");
                    sb.append(items.get(j).text);

                    base.union(r2);

                    used[j]=true;
                }
            }

            merged.add(new OcrItem(base,sb.toString()));
        }

        merged.sort((a,b)->{
            return Integer.compare(
                    a.rect.top,
                    b.rect.top
            );
        });

        int count=0;

        for(OcrItem item : merged){

            translateAndAdd(
                    item.rect,
                    item.text,
                    lang
            );

            count++;

            if(count>=4)
                break;
        }
    }

'''

s = s[:start] + new_handle + s[end:]

p.write_text(s)
print("patched")
