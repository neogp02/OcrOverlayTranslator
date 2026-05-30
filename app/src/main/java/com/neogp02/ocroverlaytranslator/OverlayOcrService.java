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
            String src = cleanSource(block.getText());

            if (r == null || src.length() < 2) continue;
            if (!containsJpOrZh(src)) continue;
            if (src.matches("[0-9!?！？♡☆★・…\\s]+")) continue;
            if (r.width() < 18 || r.height() < 18) continue;

            Rect rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
            items.add(new OcrItem(rr, src));
        }

        if (items.size() == 0) {
            overlay.removeAllViews();
            placedBoxes.clear();
            return;
        }

        ArrayList<OcrItem> groups = groupOcrItems(items);

        StringBuilder keyBuilder = new StringBuilder(lang);
        for (OcrItem g : groups) keyBuilder.append("|").append(g.text);
        String key = keyBuilder.toString();

        if (key.equals(lastKey)) return;
        lastKey = key;

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;
        for (OcrItem g : groups) {
            if (g.text.length() < 2) continue;
            translateAndAdd(g.rect, g.text, lang);
            count++;
            if (count >= 4) break;
        }
    }

    private ArrayList<OcrItem> groupOcrItems(ArrayList<OcrItem> items) {
        ArrayList<OcrItem> result = new ArrayList<>();
        boolean[] used = new boolean[items.size()];

        for (int i = 0; i < items.size(); i++) {
            if (used[i]) continue;

            Rect base = new Rect(items.get(i).rect);
            ArrayList<OcrItem> group = new ArrayList<>();
            group.add(items.get(i));
            used[i] = true;

            boolean changed = true;
            while (changed) {
                changed = false;

                for (int j = 0; j < items.size(); j++) {
                    if (used[j]) continue;

                    Rect r = items.get(j).rect;

                    int gapX = Math.max(0, Math.max(base.left, r.left) - Math.min(base.right, r.right));
                    int gapY = Math.max(0, Math.max(base.top, r.top) - Math.min(base.bottom, r.bottom));

                    boolean nearVerticalColumn =
                            Math.abs(base.centerX() - r.centerX()) < 90 && gapY < 140;

                    boolean nearHorizontalLine =
                            Math.abs(base.centerY() - r.centerY()) < 70 && gapX < 160;

                    boolean insideNearby =
                            gapX < 80 && gapY < 120;

                    if (nearVerticalColumn || nearHorizontalLine || insideNearby) {
                        group.add(items.get(j));
                        base.union(r);
                        used[j] = true;
                        changed = true;
                    }
                }
            }

            String merged = mergeGroupText(group);
            if (merged.length() >= 2) {
                result.add(new OcrItem(base, merged));
            }
        }

        result.sort((a, b) -> {
            int dy = Integer.compare(a.rect.top, b.rect.top);
            if (dy != 0) return dy;
            return Integer.compare(a.rect.left, b.rect.left);
        });

        return result;
    }

    private String mergeGroupText(ArrayList<OcrItem> group) {
        if (group.size() == 0) return "";

        Rect area = new Rect(group.get(0).rect);
        for (OcrItem item : group) area.union(item.rect);

        boolean vertical = area.height() > area.width() * 1.15f;

        if (vertical) {
            group.sort((a, b) -> {
                int dx = Integer.compare(a.rect.left, b.rect.left);
                if (Math.abs(a.rect.left - b.rect.left) > 40) return dx;
                return Integer.compare(a.rect.top, b.rect.top);
            });
        } else {
            group.sort((a, b) -> {
                int dy = Integer.compare(a.rect.top, b.rect.top);
                if (Math.abs(a.rect.top - b.rect.top) > 35) return dy;
                return Integer.compare(a.rect.left, b.rect.left);
            });
        }

        StringBuilder sb = new StringBuilder();
        for (OcrItem item : group) {
            String t = cleanSource(item.text);
            if (t.length() == 0) continue;

            if (vertical) {
                sb.append(t.replace("\n", ""));
            } else {
                if (sb.length() > 0) sb.append("\n");
                sb.append(t);
            }
        }

        return sb.toString().trim();
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

    private void translateAndAdd(Rect r, String src, String lang) {
        String cacheKey = lang + ":" + src;

        if (cache.containsKey(cacheKey)) {
            addTextBox(r, cache.get(cacheKey));
            return;
        }

        Translator t = lang.equals("zh") ? zhTranslator : jpTranslator;

        t.translate(src)
                .addOnSuccessListener(ko -> {
                    String out = ko == null ? src : ko.trim();
                    if (out.length() == 0) out = src;

                    String debugOut = "[OCR]\n" + src + "\n[번역]\n" + out;

                    cache.put(cacheKey, debugOut);
                    addTextBox(r, debugOut);
                })
                .addOnFailureListener(e -> addTextBox(r, "[OCR]\\n" + src + "\\n[번역실패]\\n" + e.getMessage()));
    }

    private void addTextBox(Rect r, String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(11);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xEE000000);
        tv.setPadding(10, 6, 10, 6);
        tv.setMaxLines(5);

        int boxW = Math.max(150, r.width() + 60);
        int boxH = Math.max(46, r.height() + 24);

        // 세로글자/좁은 말풍선 보정
        if (r.height() > r.width() * 1.5f) {
            boxW = Math.max(130, r.width() + 90);
            boxH = Math.max(90, r.height() + 20);
            tv.setTextSize(11);
        }

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(boxW, boxH);

        int x = Math.max(0, r.left - 8);
        int y = Math.max(0, r.top - 8);

        // 기존 박스와 겹치면 아래로 밀기
        int maxTry = 8;
        for (int i = 0; i < maxTry; i++) {
            boolean overlap = false;

            for (int j = 0; j < overlay.getChildCount(); j++) {
                View child = overlay.getChildAt(j);
                FrameLayout.LayoutParams cp = (FrameLayout.LayoutParams) child.getLayoutParams();

                Rect a = new Rect(x, y, x + boxW, y + boxH);
                Rect b = new Rect(cp.leftMargin, cp.topMargin,
                        cp.leftMargin + child.getWidth() + 20,
                        cp.topMargin + child.getHeight() + 20);

                if (Rect.intersects(a, b)) {
                    overlap = true;
                    break;
                }
            }

            if (!overlap) break;
            y += boxH + 8;
        }

        DisplayMetrics dm = getResources().getDisplayMetrics();

        if (x + boxW > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - boxW - 8);
        }

        if (y + boxH > dm.heightPixels) {
            y = Math.max(0, r.top - boxH - 8);
        }

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
