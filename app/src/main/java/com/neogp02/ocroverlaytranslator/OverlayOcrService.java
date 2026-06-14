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
            for (Text.Line line : block.getLines()) {
                for (Text.Element element : line.getElements()) {
                    Rect r = element.getBoundingBox();
                    String src = cleanSource(element.getText());

                    if (r == null) continue;

                    String compact = src.replace("\n", "").replace(" ", "").replace("　", "").trim();
                    if (compact.length() < 1) continue;

                    if (!containsJpOrZh(src)) continue;

                    // 너무 작은 잡점 제거
                    if (r.width() < 6 || r.height() < 6) continue;

                    items.add(new OcrItem(new Rect(r), src));
                }
            }
        }

        if (items.size() == 0) {
            overlay.removeAllViews();
            placedBoxes.clear();
            return;
        }

        ArrayList<OcrItem> groups = groupVerticalItems(items);

        StringBuilder keyBuilder = new StringBuilder(lang);
        for (OcrItem g : groups) keyBuilder.append("|").append(g.text);
        String key = keyBuilder.toString();

        if (key.equals(lastKey)) return;
        lastKey = key;

        overlay.removeAllViews();
        placedBoxes.clear();

        int count = 0;

        for (OcrItem g : groups) {
            String compact = g.text.replace("\n", "").replace(" ", "").replace("　", "").trim();
            if (compact.length() < 3) continue;

            if (isMostlyLatin(g.text)) continue;

            String compactText = g.text.replace("\n", "").replace(" ", "").replace("　", "").trim();
            if (compactText.length() > 70) continue;

            translateAndAdd(g.rect, g.text, lang);

            count++;
            if (count >= 12) break;
        }
    }

    
    private ArrayList<OcrItem> groupVerticalItems(ArrayList<OcrItem> items) {
        ArrayList<ArrayList<OcrItem>> columns = new ArrayList<>();

        // x좌표가 가까운 글자만 같은 세로열로 묶음
        for (OcrItem item : items) {
            boolean added = false;

            for (ArrayList<OcrItem> col : columns) {
                int avgX = avgX(col);

                if (Math.abs(avgX - item.rect.centerX()) < 24) {
                    col.add(item);
                    added = true;
                    break;
                }
            }

            if (!added) {
                ArrayList<OcrItem> col = new ArrayList<>();
                col.add(item);
                columns.add(col);
            }
        }

        ArrayList<OcrItem> groups = new ArrayList<>();

        for (ArrayList<OcrItem> col : columns) {
            col.sort((a, b) -> Integer.compare(a.rect.top, b.rect.top));

            StringBuilder sb = new StringBuilder();
            Rect area = rectOfColumn(col);

            for (OcrItem item : col) {
                String t = cleanSource(item.text);
                if (t.length() == 0) continue;
                sb.append(t);
            }

            String text = sb.toString().trim();
            String compact = text.replace("\n", "").replace(" ", "").replace("　", "").trim();

            if (compact.length() < 3) continue;
            if (isMostlyLatin(compact)) continue;
            if (compact.length() > 40) continue;

            groups.add(new OcrItem(area, text));
        }

        // 위쪽부터, 같은 높이면 오른쪽부터
        groups.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 30) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.right, a.rect.right);
        });

        return groups;
    }

    private int avgX(ArrayList<OcrItem> col) {
        int x = 0;
        for (OcrItem i : col) x += i.rect.centerX();
        return x / Math.max(1, col.size());
    }

    private Rect rectOfColumn(ArrayList<OcrItem> col) {
        Rect r = new Rect(col.get(0).rect);
        for (OcrItem i : col) r.union(i.rect);
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
        tv.setTextSize(11);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(7, 4, 7, 4);
        tv.setMaxLines(8);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int boxW = Math.max(95, r.width() + 45);
        int boxH = Math.max(60, r.height() + 45);

        if (r.height() > r.width() * 1.3f) {
            boxW = Math.max(85, r.width() + 35);
            boxH = Math.max(70, r.height() + 35);
            tv.setTextSize(10);
            tv.setMaxLines(10);
        }

        int x = Math.max(0, r.left - 4);
        int y = Math.max(0, r.top - 4);

        if (x + boxW > dm.widthPixels) {
            x = Math.max(0, dm.widthPixels - boxW - 4);
        }

        if (y + boxH > dm.heightPixels) {
            y = Math.max(0, dm.heightPixels - boxH - 4);
        }

        Rect newBox = new Rect(x, y, x + boxW, y + boxH);

        // 이미 표시된 박스와 겹치면 이번 박스는 버림
        for (Rect old : placedBoxes) {
            Rect padded = new Rect(old.left - 6, old.top - 6, old.right + 6, old.bottom + 6);
            if (Rect.intersects(newBox, padded)) {
                return;
            }
        }

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(boxW, boxH);
        fp.leftMargin = x;
        fp.topMargin = y;

        overlay.addView(tv, fp);
        placedBoxes.add(newBox);
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
