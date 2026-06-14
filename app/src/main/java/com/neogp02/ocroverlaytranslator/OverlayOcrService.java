package com.neogp02.ocroverlaytranslator;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.hardware.display.DisplayManager;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.*;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.*;
import android.widget.*;

import com.google.mlkit.nl.translate.*;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions;
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions;

import java.nio.ByteBuffer;
import java.util.HashMap;
import java.util.Map;
import java.util.ArrayDeque;
import java.io.FileOutputStream;
import java.util.ArrayList;
import java.util.List;

public class OverlayOcrService extends Service {

    static class OcrItem {
        Rect rect;
        String text;

        OcrItem(Rect r,String t){
            rect=r;
            text=t;
        }
    }


    public static int resultCode;
    public static Intent resultData;

    private WindowManager wm;
    private FrameLayout overlay;
    private MediaProjection projection;
    private ImageReader reader;
    private Handler handler;

    private TextRecognizer jpRecognizer;
    private TextRecognizer zhRecognizer;
    private Translator jpTranslator;
    private Translator zhTranslator;

    private final Map<String, String> cache = new HashMap<>();
    private String lastKey = "";
    private Bitmap lastScreenBitmap;
    private final List<Rect> placedBoxes = new ArrayList<>();

    @Override
    public void onCreate() {
        super.onCreate();

        try {
            handler = new Handler(Looper.getMainLooper());

            jpRecognizer = TextRecognition.getClient(
                    new JapaneseTextRecognizerOptions.Builder().build()
            );

            zhRecognizer = TextRecognition.getClient(
                    new ChineseTextRecognizerOptions.Builder().build()
            );

            jpTranslator = Translation.getClient(
                    new TranslatorOptions.Builder()
                            .setSourceLanguage(TranslateLanguage.JAPANESE)
                            .setTargetLanguage(TranslateLanguage.KOREAN)
                            .build()
            );

            zhTranslator = Translation.getClient(
                    new TranslatorOptions.Builder()
                            .setSourceLanguage(TranslateLanguage.CHINESE)
                            .setTargetLanguage(TranslateLanguage.KOREAN)
                            .build()
            );

            startForeground(1, makeNotification());
            createOverlay();

            showStatus("번역 모델 다운로드 중...");

            jpTranslator.downloadModelIfNeeded()
                    .addOnSuccessListener(a ->
                            zhTranslator.downloadModelIfNeeded()
                                    .addOnSuccessListener(b -> {
                                        showStatus("번역 모델 준비 완료");
                                        startCapture();
                                    })
                                    .addOnFailureListener(e -> showStatus("중국어 모델 실패: " + e.getMessage()))
                    )
                    .addOnFailureListener(e -> showStatus("일본어 모델 실패: " + e.getMessage()));

        } catch (Throwable e) {
            e.printStackTrace();
            stopSelf();
        }
    }

    private Notification makeNotification() {
        NotificationChannel ch = new NotificationChannel(
                "ocr",
                "OCR Overlay",
                NotificationManager.IMPORTANCE_LOW
        );
        getSystemService(NotificationManager.class).createNotificationChannel(ch);

        return new Notification.Builder(this, "ocr")
                .setContentTitle("OCR Overlay Translator 실행 중")
                .setContentText("일본어/중국어 번역 오버레이")
                .setSmallIcon(android.R.drawable.ic_menu_view)
                .build();
    }

    private void createOverlay() {
        wm = (WindowManager)getSystemService(WINDOW_SERVICE);

        overlay = new FrameLayout(this);
        overlay.setBackgroundColor(Color.TRANSPARENT);

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                        WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE |
                        WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
        );

        wm.addView(overlay, lp);
        showStatus("번역 모델 준비 중...");
    }

    private void showStatus(String msg) {
        overlay.removeAllViews();

        TextView tv = new TextView(this);
        tv.setText(msg);
        tv.setTextSize(16);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC000000);
        tv.setPadding(16, 8, 16, 8);

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
        );
        fp.leftMargin = 20;
        fp.topMargin = 100;
        overlay.addView(tv, fp);
    }

    private void startCapture() {
        if (resultData == null) {
            showStatus("MediaProjection data 없음");
            return;
        }

        MediaProjectionManager mpm =
                (MediaProjectionManager)getSystemService(MEDIA_PROJECTION_SERVICE);

        projection = mpm.getMediaProjection(resultCode, resultData);

        if (projection == null) {
            showStatus("화면캡처 권한 실패");
            return;
        }

        projection.registerCallback(new MediaProjection.Callback() {
            @Override
            public void onStop() {
                try {
                    showStatus("화면캡처 중지됨");
                } catch (Throwable ignored) {}
            }
        }, handler);

        DisplayMetrics dm = getResources().getDisplayMetrics();
        int w = dm.widthPixels;
        int h = dm.heightPixels;

        reader = ImageReader.newInstance(w, h, PixelFormat.RGBA_8888, 2);

        projection.createVirtualDisplay(
                "ocr_capture",
                w,
                h,
                dm.densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                reader.getSurface(),
                null,
                null
        );

        showStatus("OCR 번역 시작");
        handler.postDelayed(loop, 1200);
    }

    private final Runnable loop = new Runnable() {
        @Override
        public void run() {
            captureAndOcr();
            handler.postDelayed(this, 1200);
        }
    };

    private void captureAndOcr() {
        if (reader == null) return;

        Image image = reader.acquireLatestImage();
        if (image == null) return;

        try {
            Image.Plane plane = image.getPlanes()[0];
            ByteBuffer buffer = plane.getBuffer();

            int width = image.getWidth();
            int height = image.getHeight();
            int pixelStride = plane.getPixelStride();
            int rowStride = plane.getRowStride();
            int rowPadding = rowStride - pixelStride * width;

            Bitmap bitmap = Bitmap.createBitmap(
                    width + rowPadding / pixelStride,
                    height,
                    Bitmap.Config.ARGB_8888
            );

            bitmap.copyPixelsFromBuffer(buffer);

            if (rowPadding != 0) {
                bitmap = Bitmap.createBitmap(bitmap, 0, 0, width, height);
            }

            lastScreenBitmap = bitmap;

            Bitmap ocrBitmap = Bitmap.createScaledBitmap(
                    bitmap,
                    bitmap.getWidth() * 2,
                    bitmap.getHeight() * 2,
                    true
            );

            InputImage input = InputImage.fromBitmap(ocrBitmap, 0);

            jpRecognizer.process(input)
                    .addOnSuccessListener(jp -> {
                        if (hasUsefulBlocks(jp)) {
                            handleText(jp, "jp");
                        } else {
                            zhRecognizer.process(input)
                                    .addOnSuccessListener(zh -> handleText(zh, "zh"))
                                    .addOnFailureListener(e -> {});
                        }
                    })
                    .addOnFailureListener(e -> {
                        zhRecognizer.process(input)
                                .addOnSuccessListener(zh -> handleText(zh, "zh"))
                                .addOnFailureListener(e2 -> {});
                    });

        } catch (Throwable e) {
            showStatus("OCR 예외: " + e.getClass().getSimpleName());
        } finally {
            image.close();
        }
    }

    private boolean hasUsefulBlocks(Text text) {
        if (text == null || text.getTextBlocks() == null) return false;

        int count = 0;
        for (Text.TextBlock b : text.getTextBlocks()) {
            String s = cleanSource(b.getText());
            Rect r = b.getBoundingBox();

            if (r == null || s.length() < 2) continue;
            if (!containsJpOrZh(s)) continue;
            if (r.width() < 30 || r.height() < 20) continue;

            count++;
            if (count >= 1) return true;
        }
        return false;
    }

    
    
    
    
    
    
    
    
    
    
    
    
    
    private void handleText(Text result, String lang) {
        if (result == null) return;

        ArrayList<OcrItem> items = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect r = block.getBoundingBox();
            String text = cleanSource(block.getText());

            if (r == null) continue;
            if (text.length() < 2) continue;
            if (!containsJpOrZh(text)) continue;

            Rect rr = new Rect(
                    r.left / 2,
                    r.top / 2,
                    r.right / 2,
                    r.bottom / 2
            );

            items.add(new OcrItem(rr, text));
        }

        ArrayList<OcrItem> groups = groupSpeechBubbles(items);

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;
        for (OcrItem g : groups) {
            addTextBox(g.rect, g.text);
            count++;
            if (count >= 25) break;
        }
    }

    private ArrayList<OcrItem> groupSpeechBubbles(ArrayList<OcrItem> items) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        items.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 120) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : items) {
            boolean added = false;

            for (ArrayList<OcrItem> group : groups) {
                Rect gr = rectOfItems(group);

                int dx = Math.abs(cur.rect.centerX() - gr.centerX());
                int dy = Math.abs(cur.rect.centerY() - gr.centerY());

                int overlapY = Math.min(cur.rect.bottom, gr.bottom) - Math.max(cur.rect.top, gr.top);
                int gapY = Math.max(0, Math.max(cur.rect.top - gr.bottom, gr.top - cur.rect.bottom));

                boolean closeX = dx < 95;
                boolean closeY = dy < 260 || gapY < 120;
                boolean yRelated = overlapY > -120;

                // 너무 멀리 있는 다른 컷/다른 말풍선끼리 합쳐지는 것 방지
                boolean notTooLarge = gr.width() < 190 && gr.height() < 430;

                if (closeX && closeY && yRelated && notTooLarge) {
                    group.add(cur);
                    added = true;
                    break;
                }
            }

            if (!added) {
                ArrayList<OcrItem> ng = new ArrayList<>();
                ng.add(cur);
                groups.add(ng);
            }
        }

        ArrayList<OcrItem> out = new ArrayList<>();

        for (ArrayList<OcrItem> group : groups) {
            String orderedText = orderVerticalGroupText(group);
            Rect area = rectOfItems(group);

            out.add(new OcrItem(area, orderedText.trim()));
        }

        out.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 100) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        return out;
    }


    private String orderVerticalGroupText(ArrayList<OcrItem> group) {
        ArrayList<ArrayList<OcrItem>> columns = new ArrayList<>();

        // X 좌표 기준으로 세로 컬럼 분리
        for (OcrItem item : group) {
            boolean added = false;

            for (ArrayList<OcrItem> col : columns) {
                Rect cr = rectOfItems(col);
                int dx = Math.abs(item.rect.centerX() - cr.centerX());

                if (dx < 38) {
                    col.add(item);
                    added = true;
                    break;
                }
            }

            if (!added) {
                ArrayList<OcrItem> nc = new ArrayList<>();
                nc.add(item);
                columns.add(nc);
            }
        }

        // 컬럼은 오른쪽 → 왼쪽
        columns.sort((a, b) -> {
            Rect ar = rectOfItems(a);
            Rect br = rectOfItems(b);
            return Integer.compare(br.centerX(), ar.centerX());
        });

        StringBuilder sb = new StringBuilder();

        for (ArrayList<OcrItem> col : columns) {
            // 같은 컬럼 내부는 위 → 아래
            col.sort((a, b) -> Integer.compare(a.rect.top, b.rect.top));

            for (OcrItem item : col) {
                if (sb.length() > 0) sb.append("\n");
                sb.append(item.text);
            }
        }

        return sb.toString();
    }

    private Rect rectOfItems(ArrayList<OcrItem> items) {
        Rect r = new Rect(items.get(0).rect);
        for (OcrItem item : items) {
            r.union(item.rect);
        }
        return r;
    }

private String cleanSource(String s) {
        if (s == null) return "";
        return s
                .replace("|", "")
                .replace("｜", "")
                .replace("　", "")
                .replace(" ", "")
                .replace("...", "")
                .replace("…", "")
                .replace("\n\n", "\n")
                .trim();
    }

private boolean containsJpOrZh(String s) {
        if (s == null) return false;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);

            // Hiragana, Katakana, CJK Unified Ideographs
            if ((c >= 0x3040 && c <= 0x30FF) ||
                    (c >= 0x3400 && c <= 0x9FFF)) {
                return true;
            }
        }
        return false;
    }


    private boolean isMostlyLatin(String s) {
        if (s == null) return false;

        int latin = 0;
        int jpzh = 0;

        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);

            if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')) {
                latin++;
            }

            if ((c >= 0x3040 && c <= 0x30FF) ||
                    (c >= 0x3400 && c <= 0x9FFF)) {
                jpzh++;
            }
        }

        return latin >= 3 && latin > jpzh;
    }

    

    private Rect findWhiteBubbleRect(Rect textRect) {
        if (lastScreenBitmap == null || textRect == null) return null;

        int bw = lastScreenBitmap.getWidth();
        int bh = lastScreenBitmap.getHeight();

        int cx = Math.max(0, Math.min(bw - 1, textRect.centerX()));
        int cy = Math.max(0, Math.min(bh - 1, textRect.centerY()));

        int[][] seeds = new int[][] {
                {cx, cy},
                {textRect.left - 4, cy},
                {textRect.right + 4, cy},
                {cx, textRect.top - 4},
                {cx, textRect.bottom + 4},
                {textRect.left - 8, textRect.top - 8},
                {textRect.right + 8, textRect.bottom + 8}
        };

        Rect best = null;

        for (int[] seed : seeds) {
            int sx = Math.max(0, Math.min(bw - 1, seed[0]));
            int sy = Math.max(0, Math.min(bh - 1, seed[1]));

            if (!isWhiteLike(sx, sy)) continue;

            Rect r = floodWhiteRegion(sx, sy);

            if (r == null) continue;

            int area = r.width() * r.height();

            // 너무 작은 영역 제외
            if (r.width() < 25 || r.height() < 25) continue;

            // 페이지 배경처럼 너무 큰 영역 제외
            if (r.width() > bw * 0.70f || r.height() > bh * 0.55f) continue;
            if (area > bw * bh * 0.30f) continue;

            // OCR 글자 영역을 포함하지 않으면 제외
            if (!Rect.intersects(r, textRect)) continue;

            if (best == null || area > best.width() * best.height()) {
                best = r;
            }
        }

        if (best == null) return null;

        // 말풍선 테두리 안쪽만 쓰도록 약간 축소
        best.left = Math.max(0, best.left + 2);
        best.top = Math.max(0, best.top + 2);
        best.right = Math.min(bw, best.right - 2);
        best.bottom = Math.min(bh, best.bottom - 2);

        return best;
    }

    private boolean isWhiteLike(int x, int y) {
        int c = lastScreenBitmap.getPixel(x, y);

        int r = Color.red(c);
        int g = Color.green(c);
        int b = Color.blue(c);

        int max = Math.max(r, Math.max(g, b));
        int min = Math.min(r, Math.min(g, b));

        return max > 200 && min > 170 && (max - min) < 65;
    }

    private Rect floodWhiteRegion(int sx, int sy) {
        int bw = lastScreenBitmap.getWidth();
        int bh = lastScreenBitmap.getHeight();

        boolean[] visited = new boolean[bw * bh];
        ArrayDeque<int[]> q = new ArrayDeque<>();

        q.add(new int[]{sx, sy});
        visited[sy * bw + sx] = true;

        int minX = sx, maxX = sx, minY = sy, maxY = sy;
        int count = 0;
        int limit = Math.max(8000, bw * bh / 8);

        while (!q.isEmpty()) {
            int[] p = q.poll();
            int x = p[0];
            int y = p[1];

            count++;
            if (count > limit) return null;

            if (x < minX) minX = x;
            if (x > maxX) maxX = x;
            if (y < minY) minY = y;
            if (y > maxY) maxY = y;

            int[][] dirs = new int[][] {
                    {1,0}, {-1,0}, {0,1}, {0,-1}
            };

            for (int[] d : dirs) {
                int nx = x + d[0];
                int ny = y + d[1];

                if (nx < 0 || ny < 0 || nx >= bw || ny >= bh) continue;

                int idx = ny * bw + nx;
                if (visited[idx]) continue;

                visited[idx] = true;

                if (isWhiteLike(nx, ny)) {
                    q.add(new int[]{nx, ny});
                }
            }
        }

        return new Rect(minX, minY, maxX + 1, maxY + 1);
    }

    private void translateAndAdd(Rect r, String src, String lang) {
        String out = "[OCR]\n" + src;
        addTextBox(r, out);
    }


    
    
    
    
    
    
    
    private void addTextBox(Rect r, String text) {
        if (text == null) return;

        text = text.trim();
        if (text.length() == 0) return;

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(6);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC000000);
        tv.setPadding(3, 2, 3, 2);
        tv.setSingleLine(false);
        tv.setMaxLines(20);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int w = Math.max(48, r.width() + 26);
        int h = Math.max(60, r.height() + 80);

        int x = Math.max(0, r.left - 2);
        int y = Math.max(0, r.top - 2);

        if (x + w > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - w - 2);
        }

        if (y + h > dm.heightPixels) {
            y = Math.max(0, dm.heightPixels - h - 2);
        }

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(w, h);
        fp.leftMargin = x;
        fp.topMargin = y;

        overlay.addView(tv, fp);
    }

@Override
    public void onDestroy() {
        try {
            if (handler != null) handler.removeCallbacksAndMessages(null);
            if (overlay != null && wm != null) wm.removeView(overlay);
            if (projection != null) projection.stop();

            if (jpRecognizer != null) jpRecognizer.close();
            if (zhRecognizer != null) zhRecognizer.close();
            if (jpTranslator != null) jpTranslator.close();
            if (zhTranslator != null) zhTranslator.close();
        } catch (Throwable ignored) {}

        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
