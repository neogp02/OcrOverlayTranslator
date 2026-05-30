package com.neogp02.ocroverlaytranslator;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.media.projection.MediaProjectionManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int REQ_CAPTURE = 1001;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);

        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 10);
        }

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(40, 80, 40, 40);

        TextView title = new TextView(this);
        title.setText("OCR Overlay Translator\n\n1. 오버레이 권한 허용\n2. 화면 캡처 시작\n\n현재 버전: 권한/오버레이 테스트용");
        title.setTextSize(18);

        Button overlay = new Button(this);
        overlay.setText("1. 오버레이 권한 열기");
        overlay.setOnClickListener(v -> {
            Intent i = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:" + getPackageName()));
            startActivity(i);
        });

        Button start = new Button(this);
        start.setText("2. 화면 캡처 시작");
        start.setOnClickListener(v -> {
            if (!Settings.canDrawOverlays(this)) {
                Toast.makeText(this, "먼저 오버레이 권한을 허용하세요", Toast.LENGTH_LONG).show();
                return;
            }

            MediaProjectionManager mpm =
                    (MediaProjectionManager)getSystemService(MEDIA_PROJECTION_SERVICE);
            startActivityForResult(mpm.createScreenCaptureIntent(), REQ_CAPTURE);
        });

        root.addView(title);
        root.addView(overlay);
        root.addView(start);
        setContentView(root);
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);

        if (req == REQ_CAPTURE && res == RESULT_OK && data != null) {
            OverlayOcrService.resultCode = res;
            OverlayOcrService.resultData = data;
            startForegroundService(new Intent(this, OverlayOcrService.class));
            Toast.makeText(this, "오버레이 서비스 시작", Toast.LENGTH_SHORT).show();
        }
    }
}
