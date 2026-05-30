package com.neogp02.ocroverlaytranslator;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.hardware.display.DisplayManager;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import android.util.DisplayMetrics;
import com.google.mlkit.nl.translate.*;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.*;
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions;
import java.nio.ByteBuffer;
import java.util.*;

public class OverlayOcrService extends Service {
    public static int resultCode;
    public static Intent resultData;

    private WindowManager wm;
    private FrameLayout overlay;
    private MediaProjection projection;
    private ImageReader reader;
    private Handler handler;
    private TextRecognizer recognizer;
    private Translator translator;
    private String lastText = "";

    @Override
    public void onCreate() {
        super.onCreate();
        handler = new Handler(Looper.getMainLooper());
        recognizer = TextRecognition.getClient(new JapaneseTextRecognizerOptions.Builder().build());

        TranslatorOptions opt = new TranslatorOptions.Builder()
                .setSourceLanguage(TranslateLanguage.JAPANESE)
                .setTargetLanguage(TranslateLanguage.KOREAN)
                .build();
        translator = Translation.getClient(opt);
        translator.downloadModelIfNeeded();

        startForeground(1, makeNotification());
        createOverlay();
        startCapture();
    }

    private Notification makeNotification() {
        NotificationChannel ch = new NotificationChannel("ocr", "OCR Overlay", NotificationManager.IMPORTANCE_LOW);
        getSystemService(NotificationManager.class).createNotificationChannel(ch);
        return new Notification.Builder(this, "ocr")
                .setContentTitle("OCR Overlay Translator 실행 중")
                .setSmallIcon(android.R.drawable.ic_menu_view)
                .build();
    }

    private void createOverlay() {
        wm = (WindowManager)getSystemService(WINDOW_SERVICE);
        overlay = new FrameLayout(this);
        overlay.setBackgroundColor(Color.TRANSPARENT);

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                -1, -1,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE |
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
        );
        wm.addView(overlay, lp);
    }

    private void startCapture() {
        MediaProjectionManager mpm = (MediaProjectionManager)getSystemService(MEDIA_PROJECTION_SERVICE);
        projection = mpm.getMediaProjection(resultCode, resultData);

        DisplayMetrics dm = getResources().getDisplayMetrics();
        int w = dm.widthPixels;
        int h = dm.heightPixels;

        reader = ImageReader.newInstance(w, h, PixelFormat.RGBA_8888, 2);
        projection.createVirtualDisplay("ocr",
                w, h, dm.densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                reader.getSurface(), null, null);

        handler.postDelayed(loop, 1000);
    }

    private final Runnable loop = new Runnable() {
        @Override public void run() {
            captureOnce();
            handler.postDelayed(this, 1000);
        }
    };

    private void captureOnce() {
        Image image = reader.acquireLatestImage();
        if (image == null) return;

        try {
            Image.Plane p = image.getPlanes()[0];
            ByteBuffer buf = p.getBuffer();
            int pixelStride = p.getPixelStride();
            int rowStride = p.getRowStride();
            int rowPadding = rowStride - pixelStride * image.getWidth();

            Bitmap bmp = Bitmap.createBitmap(
                    image.getWidth() + rowPadding / pixelStride,
                    image.getHeight(),
                    Bitmap.Config.ARGB_8888);
            bmp.copyPixelsFromBuffer(buf);

            InputImage input = InputImage.fromBitmap(bmp, 0);
            recognizer.process(input)
                    .addOnSuccessListener(this::drawResults)
                    .addOnFailureListener(e -> {});
        } finally {
            image.close();
        }
    }

    private void drawResults(Text text) {
        String all = text.getText();
        if (all == null || all.trim().isEmpty()) return;
        if (all.equals(lastText)) return;
        lastText = all;

        overlay.removeAllViews();

        for (Text.TextBlock block : text.getTextBlocks()) {
            Rect r = block.getBoundingBox();
            String src = block.getText();
            if (r == null || src == null || src.trim().length() < 2) continue;

            translator.translate(src)
                    .addOnSuccessListener(ko -> addBox(r, ko))
                    .addOnFailureListener(e -> addBox(r, src));
        }
    }

    private void addBox(Rect r, String s) {
        TextView tv = new TextView(this);
        tv.setText(s);
        tv.setTextSize(16);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC000000);
        tv.setPadding(8, 4, 8, 4);

        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                Math.max(160, r.width() + 80),
                FrameLayout.LayoutParams.WRAP_CONTENT);
        lp.leftMargin = Math.max(0, r.left);
        lp.topMargin = Math.max(0, r.top);
        overlay.addView(tv, lp);
    }

    @Override
    public void onDestroy() {
        if (overlay != null) wm.removeView(overlay);
        if (projection != null) projection.stop();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
}
