from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

start = s.find("    private void translateForPanel(String src, String lang, PanelTranslateCallback cb)")
end = s.find("\n    private void addBottomPanel", start)

new_func = r'''
    private void translateForPanel(String src, String lang, PanelTranslateCallback cb) {
        if (src == null || src.trim().length() == 0) {
            cb.onDone("");
            return;
        }

        final String text = src.trim();

        new Thread(() -> {
            String result = text;

            try {
                String sl = "jp".equals(lang) ? "ja" : "zh-CN";
                String q = java.net.URLEncoder.encode(text, "UTF-8");

                String urlStr =
                        "https://translate.googleapis.com/translate_a/single"
                                + "?client=gtx"
                                + "&sl=" + sl
                                + "&tl=ko"
                                + "&dt=t"
                                + "&q=" + q;

                java.net.URL url = new java.net.URL(urlStr);
                java.net.HttpURLConnection conn =
                        (java.net.HttpURLConnection) url.openConnection();

                conn.setRequestMethod("GET");
                conn.setConnectTimeout(5000);
                conn.setReadTimeout(5000);
                conn.setRequestProperty("User-Agent", "Mozilla/5.0");

                java.io.BufferedReader br =
                        new java.io.BufferedReader(
                                new java.io.InputStreamReader(conn.getInputStream(), "UTF-8")
                        );

                StringBuilder sb = new StringBuilder();
                String line;

                while ((line = br.readLine()) != null) {
                    sb.append(line);
                }

                br.close();
                conn.disconnect();

                org.json.JSONArray arr = new org.json.JSONArray(sb.toString());
                org.json.JSONArray parts = arr.getJSONArray(0);

                StringBuilder out = new StringBuilder();

                for (int i = 0; i < parts.length(); i++) {
                    org.json.JSONArray part = parts.getJSONArray(i);
                    if (!part.isNull(0)) {
                        out.append(part.getString(0));
                    }
                }

                result = out.toString().trim();

            } catch (Throwable e) {
                result = text;
            }

            final String finalResult = result;

            if (handler != null) {
                handler.post(() -> cb.onDone(finalResult));
            } else {
                cb.onDone(finalResult);
            }
        }).start();
    }

'''

if start == -1 or end == -1:
    print("translateForPanel 위치 못 찾음")
else:
    s = s[:start] + new_func + s[end:]
    p.write_text(s)
    print("Google web translate patched")
