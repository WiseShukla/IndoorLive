package com.indoor.nav;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.wifi.ScanResult;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.util.Log;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.List;
import java.util.Scanner;

public class MainActivity extends AppCompatActivity {

    private WifiManager wifiManager;
    private Button btnLocalizeOnly;
    private Button btnNavigate;
    private TextView tvResult;
    private EditText ipAddressInput;
    private EditText destinationInput;
    private WebView webView;

    private boolean currentIsNavigation = false;
    private static final int PERMISSIONS_REQUEST_CODE = 100;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        btnLocalizeOnly = findViewById(R.id.btnLocalizeOnly);
        btnNavigate = findViewById(R.id.btnNavigate);
        tvResult = findViewById(R.id.tvResult);
        ipAddressInput = findViewById(R.id.ipAddressInput);
        destinationInput = findViewById(R.id.destinationInput);
        webView = findViewById(R.id.webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webView.setWebViewClient(new WebViewClient());

        wifiManager = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);

        if (!wifiManager.isWifiEnabled()) {
            Toast.makeText(this, "Enabling WiFi...", Toast.LENGTH_LONG).show();
            wifiManager.setWifiEnabled(true);
        }

        btnLocalizeOnly.setOnClickListener(v -> checkPermissionsAndScan(false));
        btnNavigate.setOnClickListener(v -> checkPermissionsAndScan(true));
    }

    private void checkPermissionsAndScan(boolean isNavigation) {
        this.currentIsNavigation = isNavigation;
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.ACCESS_FINE_LOCATION},
                    PERMISSIONS_REQUEST_CODE);
        } else {
            scanWifi();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSIONS_REQUEST_CODE && grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            scanWifi();
        } else {
            Toast.makeText(this, "Location permission required to scan WiFi", Toast.LENGTH_LONG).show();
        }
    }

    private void scanWifi() {
        tvResult.setText("Scanning WiFi...");
        BroadcastReceiver wifiScanReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context c, Intent intent) {
                boolean success = intent.getBooleanExtra(WifiManager.EXTRA_RESULTS_UPDATED, false);
                if (success) {
                    scanSuccess();
                } else {
                    scanFailure();
                }
                unregisterReceiver(this);
            }
        };

        IntentFilter intentFilter = new IntentFilter();
        intentFilter.addAction(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION);
        registerReceiver(wifiScanReceiver, intentFilter);

        boolean success = wifiManager.startScan();
        if (!success) {
            scanFailure();
        }
    }

    private void scanSuccess() {
        List<ScanResult> results = wifiManager.getScanResults();
        try {
            JSONArray wifiArray = new JSONArray();
            for (ScanResult result : results) {
                JSONObject ap = new JSONObject();
                ap.put("bssid", result.BSSID);
                ap.put("rssi", result.level);
                wifiArray.put(ap);
            }
            
            JSONObject payload = new JSONObject();
            payload.put("wifi_scan", wifiArray);
            
            if (currentIsNavigation) {
                String dest = destinationInput.getText().toString().trim();
                if (dest.isEmpty()) {
                    runOnUiThread(() -> tvResult.setText("❌ Please enter a Destination Room to Navigate!"));
                    return;
                }
                payload.put("destination", dest);
            }
            
            sendDataToServer(payload.toString(), currentIsNavigation);

        } catch (Exception e) {
            e.printStackTrace();
            tvResult.setText("Error parsing scan results");
        }
    }

    private void scanFailure() {
        tvResult.setText("Scan failed. Using old results...");
        scanSuccess(); 
    }

    private void sendDataToServer(String jsonPayload, boolean hasDestination) {
        String ip = ipAddressInput.getText().toString().trim();
        if (ip.isEmpty()) {
            tvResult.setText("Please enter Server IP!");
            return;
        }

        final String endpoint = hasDestination ? "/api/localize-and-navigate" : "/api/localize";
        final String urlString = "http://" + ip + ":5000" + endpoint;
        tvResult.setText("Sending data to " + endpoint + "...");

        new Thread(() -> {
            try {
                URL url = new URL(urlString);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json; utf-8");
                conn.setRequestProperty("Accept", "application/json");
                conn.setDoOutput(true);

                try(OutputStream os = conn.getOutputStream()) {
                    byte[] input = jsonPayload.getBytes("utf-8");
                    os.write(input, 0, input.length);
                }

                int code = conn.getResponseCode();
                if (code == 200) {
                    Scanner scanner = new Scanner(conn.getInputStream());
                    String response = scanner.useDelimiter("\\A").hasNext() ? scanner.next() : "";
                    scanner.close();

                    JSONObject resObj = new JSONObject(response);
                    
                    StringBuilder finalTxt = new StringBuilder();
                    String startNode = "";
                    String endNode = "";
                    
                    if (hasDestination) {
                        JSONObject loc = resObj.optJSONObject("localization");
                        JSONObject nav = resObj.optJSONObject("navigation");
                        
                        if (loc != null) {
                            startNode = loc.optString("predicted_location", "");
                            String room = loc.optString("room_name", "Unknown");
                            finalTxt.append("📍 You are at: ").append(room).append("\n\n");
                        }
                        
                        if (nav != null) {
                            if (nav.has("error")) {
                                finalTxt.append("❌ Navigation Error: ").append(nav.optString("error"));
                            } else {
                                JSONArray path = nav.optJSONArray("path");
                                if (path != null && path.length() > 0) {
                                    startNode = path.getString(0);
                                    endNode = path.getString(path.length() - 1);
                                }
                                
                                finalTxt.append("🧭 DIRECTIONS:\n");
                                finalTxt.append("Distance: ").append(nav.optInt("distance")).append(" steps\n\n");
                                
                                JSONArray dirs = nav.optJSONArray("directions");
                                if (dirs != null) {
                                    for (int i=0; i<dirs.length(); i++) {
                                        finalTxt.append("→ ").append(dirs.getString(i)).append("\n");
                                    }
                                }
                            }
                        }
                        
                        if (!startNode.isEmpty() && !endNode.isEmpty() && !startNode.startsWith("Unknown")) {
                            final String mapUrl = "http://" + ip + ":5000/map?start=" + startNode + "&end=" + endNode;
                            runOnUiThread(() -> webView.loadUrl(mapUrl));
                        }

                    } else {
                        String loc = resObj.optString("room_name", "Unknown");
                        startNode = resObj.optString("predicted_location", "");
                        finalTxt.append("📍 Location: ").append(loc);
                        
                        if (!startNode.isEmpty() && !startNode.startsWith("Unknown")) {
                            final String mapUrl = "http://" + ip + ":5000/map?start=" + startNode;
                            runOnUiThread(() -> webView.loadUrl(mapUrl));
                        }
                    }
                    
                    runOnUiThread(() -> tvResult.setText(finalTxt.toString()));
                } else {
                    runOnUiThread(() -> tvResult.setText("Server Error: " + code));
                }
            } catch (Exception e) {
                e.printStackTrace();
                runOnUiThread(() -> tvResult.setText("Connection failed. Check IP & Network."));
            }
        }).start();
    }
}
