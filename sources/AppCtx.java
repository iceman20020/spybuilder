package com.local.rat;

import android.content.Context;
import android.content.ContextWrapper;

public class AppCtx extends ContextWrapper {
    private static AppCtx inst;
    public AppCtx(Context base) { super(base); }
    public static void init(Context c) { if (inst == null) inst = new AppCtx(c.getApplicationContext()); }
    public static Context get() { return inst; }
}
