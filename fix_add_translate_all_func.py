from pathlib import Path

p = Path("app/src/main/java/com/neogp02/ocroverlaytranslator/OverlayOcrService.java")
s = p.read_text()

insert = s.find("    private void translateForPanel(")

func = r'''
    private interface PanelBatchTranslateCallback {
        void onDone(String[] translated);
    }

    private void translateAllForPanel(String[] srcs, String lang, PanelBatchTranslateCallback cb) {
        new Thread(() -> {
            String[] out = new String[srcs.length];

            try {
                StringBuilder qText = new StringBuilder();

                for (int i = 0; i < srcs.length; i++) {
                    qText.append("[[").append(i + 1).append("]]\n");
                    qText.append(srcs[i]).append("\n\n");
                    out[i] = "";
                }

                String sl = "jp".equals(lang) ? "ja" : "zh-CN";
                String q = java.net.URLEncoder.encode(qText.toString(), "UTF-8");

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
                conn.setConnectTimeout(7000);
                conn.setReadTimeout(7000);
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

                StringBuilder translatedAll = new StringBuilder();

                for (int i = 0; i < parts.length(); i++) {
                    org.json.JSONArray part = parts.getJSONArray(i);
                    if (!part.isNull(0)) {
                        translatedAll.append(part.getString(0));
                    }
                }

                String all = translatedAll.toString();

                for (int i = 0; i < srcs.length; i++) {
                    String marker = "[[" + (i + 1) + "]]";
                    String nextMarker = "[[" + (i + 2) + "]]";

                    int a = all.indexOf(marker);
                    int b = all.indexOf(nextMarker);

                    if (a >= 0) {
                        a += marker.length();
                        String piece = (b > a) ? all.substring(a, b) : all.substring(a);
                        out[i] = piece.trim();
                    } else {
                        out[i] = "";
                    }
                }

            } catch (Throwable e) {
                for (int i = 0; i < srcs.length; i++) {
                    out[i] = "";
                }
            }

            if (handler != null) {
                handler.post(() -> cb.onDone(out));
            } else {
                cb.onDone(out);
            }
        }).start();
    }

'''

if insert == -1:
    print("translateForPanel 위치 못 찾음")
elif "private void translateAllForPanel" in s:
    print("already exists")
else:
    s = s[:insert] + func + s[insert:]
    p.write_text(s)
    print("translateAllForPanel added")
