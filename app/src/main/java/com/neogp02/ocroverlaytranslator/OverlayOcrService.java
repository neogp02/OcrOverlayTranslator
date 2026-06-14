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
    private android.widget.ScrollView bottomPanel;
    private TextView bottomPanelText;
    private TextView closeButton;
    private String lastPanelText = ""; 
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
        overlay.setClickable(false);
        overlay.setFocusable(false);
        overlay.setEnabled(false);

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
        );

        wm.addView(overlay, lp);
    }

private void showStatus(String msg) {
        overlay.removeAllViews();

        TextView tv = new TextView(this);
        tv.setText(msg);
        tv.setTextSize(16);
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(0x66000000);
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

        ArrayList<OcrItem> elems = new ArrayList<>();

        for (Text.TextBlock block : result.getTextBlocks()) {
            for (Text.Line line : block.getLines()) {
                for (Text.Element el : line.getElements()) {
                    Rect r = el.getBoundingBox();
                    String text = cleanSourceKeepLines(el.getText());

                    if (r == null) continue;
                    if (text.length() < 1) continue;
                    if (!containsJpOrZh(text)) continue;

                    Rect rr = new Rect(r.left / 2, r.top / 2, r.right / 2, r.bottom / 2);
                    elems.add(new OcrItem(rr, text));
                }
            }
        }

        ArrayList<OcrItem> groups = groupElementsForBubbles(elems);

        groups.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 70) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        overlay.removeAllViews();
        placedBoxes.clear();

        StringBuilder panel = new StringBuilder();

        int max = Math.min(groups.size(), 60);

        for (int i = 0; i < max; i++) {
            OcrItem it = groups.get(i);

            panel.append("[")
                    .append(i + 1)
                    .append("] ")
                    .append("L=").append(it.rect.left)
                    .append(" T=").append(it.rect.top)
                    .append(" R=").append(it.rect.right)
                    .append(" B=").append(it.rect.bottom)
                    .append(" W=").append(it.rect.width())
                    .append(" H=").append(it.rect.height())
                    .append("\n")
                    .append(it.text)
                    .append("\n\n");
        }

        addBottomPanel(panel.toString());
    }


    
    private ArrayList<OcrItem> groupElementsForBubbles(ArrayList<OcrItem> elems) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(elems);

        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 55) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : sorted) {
            boolean added = false;

            for (ArrayList<OcrItem> g : groups) {
                Rect gr = rectOfLineGroup(g);
                Rect test = new Rect(gr);
                test.union(cur.rect);

                OcrItem anchor = g.get(0);

                int xDist = Math.abs(cur.rect.centerX() - anchor.rect.centerX());
                int yStartDist = Math.abs(cur.rect.top - anchor.rect.top);

                int yOverlap =
                        Math.min(cur.rect.bottom, gr.bottom)
                        - Math.max(cur.rect.top, gr.top);

                int yGap =
                        Math.max(0,
                                Math.max(cur.rect.top - gr.bottom,
                                         gr.top - cur.rect.bottom));

                boolean xClose = xDist <= 92;
                boolean yStartClose = yStartDist <= 42;
                boolean yConnected = yOverlap > -35 || yGap <= 65;
                boolean sizeOk = test.width() <= 165 && test.height() <= 320;

                if (xClose && yStartClose && yConnected && sizeOk) {
                    g.add(cur);
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

        for (ArrayList<OcrItem> g : groups) {
            Rect r = rectOfLineGroup(g);
            String text = orderLineGroupText(g);

            if (text.trim().length() > 0) {
                StringBuilder dbg = new StringBuilder();
                dbg.append(text.trim()).append("\n");

                dbg.append("---- members ----\n");
                for (OcrItem m : g) {
                    dbg.append("L=").append(m.rect.left)
                            .append(" T=").append(m.rect.top)
                            .append(" R=").append(m.rect.right)
                            .append(" B=").append(m.rect.bottom)
                            .append(" W=").append(m.rect.width())
                            .append(" H=").append(m.rect.height())
                            .append(" :: ")
                            .append(m.text)
                            .append("\n");
                }

                out.add(new OcrItem(r, dbg.toString().trim()));
            }
        }

        return out;
    }

private ArrayList<OcrItem> groupLinesByXYStart(ArrayList<OcrItem> lines) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(lines);

        sorted.sort((a, b) -> {
            // 먼저 위쪽
            if (Math.abs(a.rect.top - b.rect.top) > 45) {
                return Integer.compare(a.rect.top, b.rect.top);
            }

            // 같은 높이면 오른쪽부터
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : sorted) {
            boolean added = false;

            for (ArrayList<OcrItem> g : groups) {
                OcrItem anchor = g.get(0);

                Rect gr = rectOfLineGroup(g);
                Rect test = new Rect(gr);
                test.union(cur.rect);

                int xDist = Math.abs(cur.rect.centerX() - anchor.rect.centerX());
                int yStartDist = Math.abs(cur.rect.top - anchor.rect.top);

                // 핵심: y 길이/겹침이 아니라 시작점 기준
                boolean xClose = xDist <= 80;
                boolean yStartClose = yStartDist <= 28;

                // 아래쪽으로 이어지는 세로 대사는 허용, 위로 역결합은 금지
                boolean notAboveAnchor = cur.rect.top >= anchor.rect.top - 12;

                // 너무 큰 말풍선 방지
                boolean sizeOk = test.width() <= 150 && test.height() <= 310;

                if (xClose && yStartClose && notAboveAnchor && sizeOk) {
                    g.add(cur);
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

        for (ArrayList<OcrItem> g : groups) {
            Rect r = rectOfLineGroup(g);
            String text = orderLineGroupText(g);

            if (text.trim().length() > 0) {
                out.add(new OcrItem(r, text.trim()));
            }
        }

        return out;
    }


    private Rect rectOfLineGroup(ArrayList<OcrItem> group) {
        Rect r = new Rect(group.get(0).rect);
        for (OcrItem item : group) {
            r.union(item.rect);
        }
        return r;
    }

    private String orderLineGroupText(ArrayList<OcrItem> group) {
        ArrayList<OcrItem> sorted = new ArrayList<>(group);

        sorted.sort((a, b) -> {
            // 세로쓰기: 오른쪽 컬럼 먼저
            if (Math.abs(a.rect.centerX() - b.rect.centerX()) > 30) {
                return Integer.compare(b.rect.centerX(), a.rect.centerX());
            }

            // 같은 컬럼 안에서는 위에서 아래
            return Integer.compare(a.rect.top, b.rect.top);
        });

        StringBuilder sb = new StringBuilder();

        for (OcrItem item : sorted) {
            if (sb.length() > 0) sb.append("\n");
            sb.append(item.text);
        }

        return sb.toString();
    }


    private ArrayList<OcrItem> groupPanelItemsLoose(ArrayList<OcrItem> items) {
        ArrayList<ArrayList<OcrItem>> groups = new ArrayList<>();

        ArrayList<OcrItem> sorted = new ArrayList<>(items);

        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.top - b.rect.top) > 100) {
                return Integer.compare(a.rect.top, b.rect.top);
            }
            return Integer.compare(b.rect.centerX(), a.rect.centerX());
        });

        for (OcrItem cur : sorted) {
            boolean added = false;

            for (ArrayList<OcrItem> g : groups) {
                Rect gr = rectOfPanelItems(g);
                Rect test = new Rect(gr);
                test.union(cur.rect);

                int dx = Math.abs(cur.rect.centerX() - gr.centerX());
                int overlapY = Math.min(cur.rect.bottom, gr.bottom) - Math.max(cur.rect.top, gr.top);
                int gapY = Math.max(0, Math.max(cur.rect.top - gr.bottom, gr.top - cur.rect.bottom));

                boolean closeEnoughX = dx < 150;
                boolean relatedY = overlapY > -80 || gapY < 120;
                boolean sizeOk = test.width() < 230 && test.height() < 430;

                if (closeEnoughX && relatedY && sizeOk) {
                    g.add(cur);
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

        for (ArrayList<OcrItem> g : groups) {
            Rect area = rectOfPanelItems(g);
            String text = orderPanelGroupText(g);

            if (text.trim().length() > 0) {
                out.add(new OcrItem(area, text.trim()));
            }
        }

        return out;
    }

    private String orderPanelGroupText(ArrayList<OcrItem> group) {
        ArrayList<OcrItem> sorted = new ArrayList<>(group);

        sorted.sort((a, b) -> {
            if (Math.abs(a.rect.centerX() - b.rect.centerX()) > 35) {
                return Integer.compare(b.rect.centerX(), a.rect.centerX());
            }
            return Integer.compare(a.rect.top, b.rect.top);
        });

        StringBuilder sb = new StringBuilder();

        for (OcrItem item : sorted) {
            if (sb.length() > 0) sb.append("\n");
            sb.append(item.text);
        }

        return sb.toString();
    }

    private Rect rectOfPanelItems(ArrayList<OcrItem> items) {
        Rect r = new Rect(items.get(0).rect);

        for (OcrItem item : items) {
            r.union(item.rect);
        }

        return r;
    }

    private String buildPanelText(String[] srcs, String[] trans) {
        StringBuilder sb = new StringBuilder();

        for (int i = 0; i < srcs.length; i++) {
            int n = i + 1;

            sb.append("[")
                    .append(n)
                    .append("] 원문\n")
                    .append(srcs[i])
                    .append("\n\n");

            sb.append("[")
                    .append(n)
                    .append("] 번역\n")
                    .append(trans[i])
                    .append("\n\n");
        }

        return sb.toString();
    }


    private String normalizeForTranslate(String s) {
        if (s == null) return "";

        String t = s;

        // ML Kit OCR 자주 나는 오인식 보정
        t = t.replace("時距", "時間");
        t = t.replace("時臣", "時間");
        t = t.replace("時距が", "時間が");

        // 만화/구어체 보정
        t = t.replace("アガリ時間", "上がり時間");
        t = t.replace("あがり時間", "上がり時間");
        t = t.replace("出待ち?", "出待ち？");

        // 줄바꿈은 번역기에 문장 경계로 전달
        t = t.replace("\n", "。");

        return t.trim();
    }

    private interface PanelTranslateCallback {
        void onDone(String text);
    }

    private void translateForPanel(String src, String lang, PanelTranslateCallback cb) {
        if (src == null || src.trim().length() == 0) {
            cb.onDone("");
            return;
        }

        String fixedSrc = normalizeForTranslate(src);

        try {
            if ("zh".equals(lang) && zhTranslator != null) {
                zhTranslator.translate(fixedSrc)
                        .addOnSuccessListener(cb::onDone)
                        .addOnFailureListener(e -> cb.onDone(src));
            } else if (jpTranslator != null) {
                jpTranslator.translate(fixedSrc)
                        .addOnSuccessListener(cb::onDone)
                        .addOnFailureListener(e -> cb.onDone(src));
            } else {
                cb.onDone(src);
            }
        } catch (Throwable t) {
            cb.onDone(src);
        }
    }

private void addNumberMarker(Rect r, int number) {
        TextView tv = new TextView(this);
        tv.setText(String.valueOf(number));
        tv.setTextSize(10);
        tv.setTextColor(Color.WHITE);
        tv.setGravity(Gravity.CENTER);
        tv.setBackgroundColor(0x66000000);
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
        text = text.replace("\\n", "\n");

        if (wm == null) {
            wm = (WindowManager)getSystemService(WINDOW_SERVICE);
        }

        // 같은 내용이면 갱신하지 않음: 스크롤 위치 유지
        if (text.equals(lastPanelText) && bottomPanel != null) {
            return;
        }

        lastPanelText = text;

        if (bottomPanel != null && bottomPanelText != null) {
            bottomPanelText.setText(text);
            return;
        }

        bottomPanel = new android.widget.ScrollView(this);
        bottomPanel.setBackgroundColor(0xCC000000);
        bottomPanel.setFillViewport(false);
        bottomPanel.setVerticalScrollBarEnabled(true);
        bottomPanel.setClickable(true);
        bottomPanel.setFocusable(false);

        bottomPanelText = new TextView(this);
        bottomPanelText.setText(text);
        bottomPanelText.setTextSize(10);
        bottomPanelText.setTextColor(Color.WHITE);
        bottomPanelText.setPadding(12, 10, 12, 40);
        bottomPanelText.setSingleLine(false);

        bottomPanel.addView(
                bottomPanelText,
                new android.widget.ScrollView.LayoutParams(
                        android.widget.ScrollView.LayoutParams.MATCH_PARENT,
                        android.widget.ScrollView.LayoutParams.WRAP_CONTENT
                )
        );

        DisplayMetrics dm = getResources().getDisplayMetrics();

        int panelHeight = Math.min(360, dm.heightPixels / 3);
        int bottomOffset = 160;

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                dm.widthPixels,
                panelHeight,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
        );

        lp.gravity = Gravity.TOP | Gravity.LEFT;
        lp.x = 0;
        lp.y = dm.heightPixels - panelHeight - bottomOffset;

        wm.addView(bottomPanel, lp);

        addCloseButton();
    }



    private void addCloseButton() {
        if (closeButton != null) return;

        if (wm == null) {
            wm = (WindowManager)getSystemService(WINDOW_SERVICE);
        }

        closeButton = new TextView(this);
        closeButton.setText("×");
        closeButton.setTextSize(22);
        closeButton.setTextColor(Color.WHITE);
        closeButton.setGravity(Gravity.CENTER);
        closeButton.setBackgroundColor(0xCCAA0000);
        closeButton.setClickable(true);
        closeButton.setFocusable(false);

        closeButton.setOnClickListener(v -> {
            try {
                stopSelf();
            } catch (Throwable ignored) {}
        });

        DisplayMetrics dm = getResources().getDisplayMetrics();

        WindowManager.LayoutParams lp = new WindowManager.LayoutParams(
                64,
                64,
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
        );

        lp.gravity = Gravity.TOP | Gravity.LEFT;
        lp.x = dm.widthPixels - 80;
        lp.y = 90;

        wm.addView(closeButton, lp);
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
        tv.setBackgroundColor(0x66000000);
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
            if (bottomPanel != null && wm != null) wm.removeView(bottomPanel);
            if (closeButton != null && wm != null) wm.removeView(closeButton);
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


    
    private String orderedBlockText(Text.TextBlock block) {
        ArrayList<Text.Line> lines = new ArrayList<>(block.getLines());

        lines.sort((a, b) -> {
            Rect ar = a.getBoundingBox();
            Rect br = b.getBoundingBox();

            if (ar == null || br == null) return 0;

            // 세로쓰기: 오른쪽 줄 먼저
            if (Math.abs(ar.centerX() - br.centerX()) > 25) {
                return Integer.compare(br.centerX(), ar.centerX());
            }

            // 같은 줄이면 위에서 아래
            return Integer.compare(ar.top, br.top);
        });

        StringBuilder sb = new StringBuilder();

        for (Text.Line line : lines) {
            String t = line.getText();
            if (t == null) continue;

            if (sb.length() > 0) sb.append(" ");
            sb.append(t);
        }

        return sb.toString();
    }


    private String cleanSourceKeepLines(String s) {
        if (s == null) return "";

        return s
                .replace("\r", "")
                .replace(" ", "")
                .trim();
    }

private String cleanSource(String s) {
        if (s == null) return "";

        return s
                .replace(" ", "")
                .replace("\n", "")
                .trim();
    }

    private boolean containsJpOrZh(String s) {
        if (s == null) return false;

        for (char c : s.toCharArray()) {

            if ((c >= 0x3040 && c <= 0x30FF) ||
                (c >= 0x4E00 && c <= 0x9FFF)) {

                return true;
            }
        }

        return false;
    }


}