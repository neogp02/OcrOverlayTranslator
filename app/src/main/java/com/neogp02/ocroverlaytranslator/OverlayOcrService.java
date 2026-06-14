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

            Rect rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
            items.add(new OcrItem(rr, text));
        }

        items.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 100) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        overlay.removeAllViews();
        placedBoxes.clear();

        StringBuilder panel = new StringBuilder();
        int index = 1;

        for (OcrItem item : items) {
            addNumberMarker(item.rect, index);
            panel.append(index)
                    .append(". ")
                    .append(item.text.replace("\n", " "))
                    .append("\n");

            index++;
            if (index > 25) break;
        }

        addBottomPanel(panel.toString());
    }

    private void addNumberMarker(Rect r, int number) {
        TextView tv = new TextView(this);
        tv.setText(String.valueOf(number));
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setGravity(Gravity.CENTER);
        tv.setBackgroundColor(0xDD000000);
        tv.setPadding(2, 1, 2, 1);

        int size = 24;
        int x = Math.max(0, r.left - 6);
        int y = Math.max(0, r.top - 6);

        DisplayMetrics dm = getResources().getDisplayMetrics();

        if (x + size > dm.widthPixels) x = dm.widthPixels - size;
        if (y + size > dm.heightPixels) y = dm.heightPixels - size;

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(size, size);
        fp.leftMargin = x;
        fp.topMargin = y;

        overlay.addView(tv, fp);
    }

    
    private void addBottomPanel(String text) {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(0xCC000000);
        scroll.setFillViewport(false);

        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setPadding(12, 10, 12, 10);
        tv.setSingleLine(false);

        scroll.addView(
                tv,
                new ScrollView.LayoutParams(
                        ScrollView.LayoutParams.MATCH_PARENT,
                        ScrollView.LayoutParams.WRAP_CONTENT
                )
        );

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int panelHeight = Math.min(260, dm.heightPixels / 4);
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

        overlay.addView(scroll, fp);
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
