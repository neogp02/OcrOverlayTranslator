package com.neogp02.ocroverlaytranslator;

import android.app.*;
import android.content.*;
import android.graphics.*;
import android.graphics.ColorMatrix;
import android.graphics.ColorMatrixColorFilter;
import android.hardware.display.DisplayManager;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.*;
import android.util.DisplayMetrics;
import android.view.*;
import android.widget.*;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions;
import java.nio.ByteBuffer;

public class OverlayOcrService extends Service {
    public static int resultCode;
    public static Intent resultData;

    private WindowManager wm;
    private FrameLayout overlay;
    private MediaProjection projection;
    private ImageReader reader;
    private Handler handler;
    private TextRecognizer recognizer;
    private String lastText = "";

    @Override
    public void onCreate() {
        super.onCreate();

        try {
            handler = new Handler(Looper.getMainLooper());
            recognizer = TextRecognition.getClient(
                    new JapaneseTextRecognizerOptions.Builder().build()
            );

            startForeground(1, makeNotification());
            createOverlay();
            startCapture();
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
                .setContentText("OCR 원문 표시 테스트")
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
        addStatusBox("OCR 준비 중...");
    }

    private void addStatusBox(String text) {
        overlay.removeAllViews();

        TextView tv = new TextView(this);
        tv.setText(text);
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
            addStatusBox("MediaProjection data 없음");
            return;
        }

        MediaProjectionManager mpm =
                (MediaProjectionManager)getSystemService(MEDIA_PROJECTION_SERVICE);

        projection = mpm.getMediaProjection(resultCode, resultData);

        if (projection == null) {
            addStatusBox("화면캡처 권한 실패");
            return;
        }

        projection.registerCallback(new MediaProjection.Callback() {
            @Override
            public void onStop() {
                try {
                    addStatusBox("화면캡처 중지됨");
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

        addStatusBox("화면캡처 권한 OK / OCR 시작");

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

            Bitmap processed = preprocessForOcr(bitmap);

            InputImage input = InputImage.fromBitmap(processed, 0);

            recognizer.process(input)
                    .addOnSuccessListener(this::showOcrResult)
                    .addOnFailureListener(e -> addStatusBox("OCR 실패: " + e.getMessage()));

        } catch (Throwable e) {
            addStatusBox("캡처/OCR 예외: " + e.getClass().getSimpleName());
        } finally {
            image.close();
        }
    }


    private Bitmap preprocessForOcr(Bitmap src) {
        try {
            int scale = 2;
            Bitmap scaled = Bitmap.createScaledBitmap(
                    src,
                    src.getWidth() * scale,
                    src.getHeight() * scale,
                    true
            );

            Bitmap out = Bitmap.createBitmap(
                    scaled.getWidth(),
                    scaled.getHeight(),
                    Bitmap.Config.ARGB_8888
            );

            Canvas canvas = new Canvas(out);
            Paint paint = new Paint();

            ColorMatrix cm = new ColorMatrix();
            cm.setSaturation(0);

            ColorMatrix contrast = new ColorMatrix(new float[] {
                    1.8f, 0, 0, 0, -80,
                    0, 1.8f, 0, 0, -80,
                    0, 0, 1.8f, 0, -80,
                    0, 0, 0, 1, 0
            });

            cm.postConcat(contrast);
            paint.setColorFilter(new ColorMatrixColorFilter(cm));

            canvas.drawBitmap(scaled, 0, 0, paint);

            return out;
        } catch (Throwable e) {
            return src;
        }
    }

    private void showOcrResult(Text result) {
        String text = result.getText();

        if (text == null || text.trim().isEmpty()) {
            addStatusBox("OCR 결과 없음");
            return;
        }

        text = text.trim();

        if (text.equals(lastText)) return;
        lastText = text;

        overlay.removeAllViews();

        int count = 0;

        for (Text.TextBlock block : result.getTextBlocks()) {
            Rect r = block.getBoundingBox();
            String src = block.getText();

            if (r == null || src == null || src.trim().length() < 2) continue;

            addTextBox(r, src.trim());
            count++;

            if (count >= 8) break;
        }

        if (count == 0) {
            addStatusBox("OCR 블록 없음");
        }
    }

    private void addTextBox(Rect r, String text) {
        TextView tv = new TextView(this);
        tv.setText(text);
        tv.setTextSize(15);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0xCC000000);
        tv.setPadding(8, 4, 8, 4);

        FrameLayout.LayoutParams fp = new FrameLayout.LayoutParams(
                Math.max(120, r.width() + 40),
                FrameLayout.LayoutParams.WRAP_CONTENT
        );

        fp.leftMargin = Math.max(0, r.left);
        fp.topMargin = Math.max(0, r.top);

        overlay.addView(tv, fp);
    }

    @Override
    public void onDestroy() {
        try {
            if (handler != null) handler.removeCallbacksAndMessages(null);
            if (overlay != null && wm != null) wm.removeView(overlay);
            if (projection != null) projection.stop();
            if (recognizer != null) recognizer.close();
        } catch (Throwable ignored) {}

        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
