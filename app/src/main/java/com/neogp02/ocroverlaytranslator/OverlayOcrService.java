package com.neogp02.ocroverlaytranslator;

import android.app.*;
import android.content.*;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.IBinder;
import android.view.*;
import android.widget.*;

public class OverlayOcrService extends Service {
    public static int resultCode;
    public static Intent resultData;

    private WindowManager wm;
    private TextView box;
    private MediaProjection projection;

    @Override
    public void onCreate() {
        super.onCreate();

        try {
            startForeground(1, makeNotification());
            createOverlay();
            startProjectionTest();
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
                .setContentText("오버레이 테스트")
                .setSmallIcon(android.R.drawable.ic_menu_view)
                .build();
    }

    private void createOverlay() {
        wm = (WindowManager)getSystemService(WINDOW_SERVICE);

        box = new TextView(this);
        box.setText("OCR Overlay ON");
        box.setTextSize(18);
        box.setTextColor(Color.WHITE);
        box.setBackgroundColor(0xCC000000);
        box.setPadding(20, 12, 20, 12);

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,
                PixelFormat.TRANSLUCENT
        );

        lp.gravity = Gravity.TOP | Gravity.LEFT;
        lp.x = 30;
        lp.y = 120;

        wm.addView(box, lp);
    }

    private void startProjectionTest() {
        if (resultData == null) {
            box.setText("MediaProjection data 없음");
            return;
        }

        MediaProjectionManager mpm =
                (MediaProjectionManager)getSystemService(MEDIA_PROJECTION_SERVICE);

        projection = mpm.getMediaProjection(resultCode, resultData);

        if (projection != null) {
            box.setText("화면캡처 권한 OK");
        } else {
            box.setText("화면캡처 권한 실패");
        }
    }

    @Override
    public void onDestroy() {
        try {
            if (box != null && wm != null) wm.removeView(box);
            if (projection != null) projection.stop();
        } catch (Throwable ignored) {}
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
