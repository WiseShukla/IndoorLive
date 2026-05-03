# WiFi Indoor Localization & Navigation System

> 4th Floor, R&D Building — Wireless Networks Project

## Overview

This project implements a **WiFi fingerprint-based indoor localization and navigation system** for the 4th floor of the R&D building. The system uses WiFi RSSI fingerprints collected from **39 reference points** across both wings (A-Wing and B-Wing) to determine a user's room-level location. It provides two client interfaces — an **Android mobile app** for real-time on-the-go localization and a **web browser dashboard** for visualization and navigation.

### Key Features

- **WiFi Fingerprinting**: Uses RSSI data from surrounding WiFi access points to predict the user's room via a **Random Forest classifier** (200 estimators, balanced class weights).
- **Multi-Scan Majority Voting**: Buffers multiple WiFi scans and uses weighted confidence voting to stabilize predictions against signal noise.
- **Indoor Navigation**: Graph-based shortest-path routing using **Dijkstra's algorithm** with human-readable turn-by-turn directions.
- **Dual Client Architecture**: Native Android app for mobile localization + Web browser dashboard for floor plan visualization.
- **Interactive Floor Plan**: Real-time HTML5 Canvas rendering with animated navigation paths and blue-dot position tracking.
- **Mobile Hotspot Filtering**: Automatically ignores transient mobile hotspot signals (phones, portable devices) to only use stable infrastructure APs.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                        │
│                                                                                  │
│   ┌──────────────────────────┐          ┌────────────────────────────────────┐   │
│   │   📱 Android App          │          │   🌐 Web Browser                    │   │
│   │   (IndoorNav Live)        │          │   http://<server-ip>:5000           │   │
│   │                           │          │                                    │   │
│   │  ┌─────────────────────┐  │          │  ┌──────────┐ ┌────────────────┐  │   │
│   │  │ WiFi Scanner        │  │          │  │  Canvas   │ │ Controls Panel │  │   │
│   │  │ (WifiManager API)   │  │          │  │Floor Plan │ │ • Simulate Loc │  │   │
│   │  └─────────┬───────────┘  │          │  │ + Blue    │ │ • Navigate To  │  │   │
│   │            │               │          │  │   Dot     │ │ • Room List    │  │   │
│   │  ┌─────────▼───────────┐  │          │  └──────────┘ └────────────────┘  │   │
│   │  │ Build JSON payload  │  │          │  ┌──────────────────────────────┐  │   │
│   │  │ {wifi_scan: [...]}  │  │          │  │ Directions Panel             │  │   │
│   │  └─────────┬───────────┘  │          │  │ • Turn-by-turn instructions  │  │   │
│   │            │               │          │  │ • Distance in steps          │  │   │
│   │  ┌─────────▼───────────┐  │          │  │ • Estimated walking time     │  │   │
│   │  │ Server IP Input     │  │          │  └──────────────────────────────┘  │   │
│   │  │ Localize / Navigate │  │          │                                    │   │
│   │  │ Result Text Display │  │          └──────────────────┬─────────────────┘   │
│   │  │ Embedded WebView ───┼──┼── loads /map endpoint ──────┘                     │
│   │  └─────────────────────┘  │                                                   │
│   └────────────┬──────────────┘                                                   │
└────────────────┼──────────────────────────────────────────────────────────────────┘
                 │
                 │  HTTP POST (JSON)
                 │  ┌──────────────────────────────────────┐
                 │  │ Localize:     /api/localize           │
                 │  │ Navigate:     /api/localize-and-navigate │
                 │  │ Payload:      {"wifi_scan": [...]}    │
                 │  └──────────────────────────────────────┘
                 ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                     SERVER LAYER — Flask Backend (app.py)                         │
│                     Python · Port 5000 · Host 0.0.0.0                            │
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                         API Router (app.py)                              │   │
│   │                                                                          │   │
│   │   GET  /                 → index.html (Web Dashboard)                    │   │
│   │   GET  /map              → map.html  (Mobile WebView map)                │   │
│   │   GET  /api/locations    → All 39 fingerprinted location labels           │   │
│   │   GET  /api/rooms        → All navigable rooms for dropdown              │   │
│   │   GET  /api/graph        → Graph nodes + edges for Canvas rendering      │   │
│   │   POST /api/localize     → WiFi scan → Room prediction                   │   │
│   │   POST /api/navigate     → Start + End → Shortest path + directions      │   │
│   │   POST /api/localize-and-navigate → WiFi scan + destination → Full nav   │   │
│   │   POST /api/simulate-localize     → Demo mode (no WiFi needed)           │   │
│   └──────────┬──────────────────────────────────┬────────────────────────────┘   │
│              │                                  │                                │
│   ┌──────────▼──────────────────┐    ┌──────────▼────────────────────────────┐   │
│   │  🧠 WiFi Fingerprint Engine  │    │  🗺️  Navigation Engine                │   │
│   │  (fingerprint_engine.py)    │    │  (navigation_engine.py)               │   │
│   │                              │    │                                       │   │
│   │  CLASS: WiFiFingerprintEngine│    │  CLASS: NavigationGraph               │   │
│   │                              │    │                                       │   │
│   │  • RandomForestClassifier    │    │  • 54 nodes:                          │   │
│   │    (200 trees, balanced)     │    │    - 37 rooms (A & B wing)            │   │
│   │  • 39 room-level labels     │    │    - 14 corridor waypoints            │   │
│   │  • 373 unique BSSIDs        │    │    - 3 landmarks (elevator,           │   │
│   │  • Feature: RSSI vector     │    │      door, mid corridor)              │   │
│   │                              │    │  • Weighted undirected graph          │   │
│   │  METHODS:                    │    │    (edge weights = walking steps)     │   │
│   │  • predict(scan)             │    │  • Dijkstra's shortest path           │   │
│   │    → single scan prediction  │    │  • Turn-by-turn direction gen         │   │
│   │  • predict_multi_scan(scans) │    │    ("Turn LEFT towards A-Wing")       │   │
│   │    → majority voting (3 buf) │    │                                       │   │
│   │  • predict_with_steps()      │    │  METHODS:                             │   │
│   │    → WiFi + PDR fusion       │    │  • find_shortest_path(start, end)     │   │
│   │                              │    │  • get_room_name(label)               │   │
│   │  FILTERS:                    │    │  • find_node_for_location(label)      │   │
│   │  • RSSI floor: -100 dBm     │    │  • get_navigable_rooms()              │   │
│   │  • Min useful: -95 dBm      │    │  • get_graph_data() → JSON for canvas │   │
│   │  • Mobile hotspot blacklist  │    │                                       │   │
│   │  • Locally-administered MAC  │    │                                       │   │
│   │    filter (bit 0x02)         │    │                                       │   │
│   └──────────┬───────────────────┘    └───────────────────────────────────────┘   │
│              │                                                                    │
│   ┌──────────▼──────────────────┐                                                │
│   │  📁 Training_data/          │                                                │
│   │  (WiFi Radio Map)           │                                                │
│   │                              │                                                │
│   │  92 CSV files from           │                                                │
│   │  39 reference points         │                                                │
│   │  across A-Wing & B-Wing     │                                                │
│   │                              │                                                │
│   │  Columns: BSSID, SSID,      │                                                │
│   │  Signal Strength, Scan#     │                                                │
│   └──────────────────────────────┘                                                │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow — How Localization Works

```
 ┌─────────────────────────────────────┐
 │  User stands near a room on the     │
 │  4th floor with the Android app     │
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │  Android WifiManager.startScan()    │
 │  Collects all visible APs:          │
 │  • BSSID (MAC address)              │
 │  • RSSI  (signal strength in dBm)   │
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │  Build JSON payload:                │
 │  {                                  │
 │    "wifi_scan": [                   │
 │      {"bssid":"aa:bb:cc:..","rssi":-45}, │
 │      {"bssid":"11:22:33:..","rssi":-67}  │
 │    ]                                │
 │  }                                  │
 └──────────────────┬──────────────────┘
                    │ HTTP POST
                    │ http://<server-ip>:5000/api/localize
                    ▼
 ┌─────────────────────────────────────┐
 │  Flask receives JSON and parses     │
 │  into {bssid: rssi} dictionary      │
 │                                     │
 │  Filters applied:                   │
 │  ✗ RSSI < -95 dBm (too weak)       │
 │  ✗ Locally-administered MACs        │
 │  ✗ Mobile hotspot SSIDs             │
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │  Random Forest Classifier           │
 │                                     │
 │  1. Build RSSI feature vector       │
 │     (373 BSSIDs, -100 for missing)  │
 │  2. predict_proba() → 39 classes    │
 │  3. Sort by probability             │
 │  4. Return top prediction +         │
 │     confidence + top-5 matches      │
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │  Server Response:                   │
 │  {                                  │
 │    "predicted_location":"B-405_right",│
 │    "room_name": "B-405",            │
 │    "confidence": 0.87,              │
 │    "position": {"x":1100, "y":440}, │
 │    "top_matches": [                 │
 │      {"location":"B-405_right",     │
 │       "probability": 0.87},         │
 │      {"location":"B-404_right",     │
 │       "probability": 0.06}          │
 │    ],                               │
 │    "status": "confident"            │
 │  }                                  │
 └──────────────────┬──────────────────┘
                    ▼
 ┌─────────────────────────────────────┐
 │  Android App:                       │
 │  • Displays "📍 Location: B-405"    │
 │  • Loads /map?start=B-405_right     │
 │    in embedded WebView              │
 │  • Blue dot appears at (1100, 440)  │
 │    on the floor plan canvas         │
 └─────────────────────────────────────┘
```

---

## Navigation Flow — How Pathfinding Works

```
 ┌──────────────────────────────────────┐
 │  User enters destination: "B-412"    │
 │  and presses NAVIGATE button         │
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │  POST /api/localize-and-navigate     │
 │  {                                   │
 │    "wifi_scan": [...],               │
 │    "destination": "B-412_Right"      │
 │  }                                   │
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │  Step 1: Localize (same as above)    │
 │  → predicted_location: "B-405_right" │
 │                                      │
 │  Step 2: Map to graph nodes          │
 │  → start_node: "B-405_Right"         │
 │  → end_node:   "B-412_Right"         │
 │                                      │
 │  Step 3: Dijkstra's shortest path    │
 │  → path: [B-405_Right, corridor_b2,  │
 │           corridor_b3, ...,          │
 │           corridor_b6, B-412_Right]  │
 │  → distance: 18 steps               │
 │                                      │
 │  Step 4: Generate directions         │
 │  → "📍 Start at: Room B-405"         │
 │  → "🚶 Exit into the corridor"       │
 │  → "🚶 Walk along corridor (~15 m)"  │
 │  → "🚪 Room B-412 is on your RIGHT"  │
 │  → "✅ You have arrived!"             │
 │  → "⏱️ Estimated: ~1 min"            │
 └──────────────────┬───────────────────┘
                    ▼
 ┌──────────────────────────────────────┐
 │  Android App:                        │
 │  • Shows directions as text list     │
 │  • Loads /map?start=...&end=...      │
 │  • WebView draws animated path       │
 │    from blue dot to destination      │
 └──────────────────────────────────────┘
```

---

## Floor Plan Layout

```
                              4th Floor, R&D Building

    ◄────────── A-WING (LEFT) ──────────►              ◄────────── B-WING (RIGHT) ──────────►

    NORTH SIDE (right rooms)                            NORTH SIDE (left rooms)
    ┌─────┬─────┬─────┬─────┬─────┐                    ┌─────┬─────┬─────┬─────┬─────┐
    │A-413│     │A-415│A-416│     │A-418│A-419│    │B-419│B-418│     │B-416│B-415│     │B-413│
    └──┬──┘     └──┬──┘──┬──┘     └──┬──┘──┬──┘    └──┬──┘──┬──┘     └──┬──┘──┬──┘     └──┬──┘
    ═══╪══════════╪════╪══════════╪════╪════╪══════╪════╪══════════╪════╪══════════╪══════╪═══
       │  CORRIDOR │    │ CORRIDOR │    │    │      │    │ CORRIDOR │    │ CORRIDOR │      │
    ═══╪══════════╪════╪══════════╪════╪════╪══╤═══╪════╪══════════╪════╪══════════╪══════╪═══
    ┌──┴──┬──┴──┬──┴──┬──┴──┬──┴──┬──┴──┐  │  ┌──┴──┬──┴──┬──┴──┬──┴──┬──┴──┬──┴──┐
    │A-412│A-411│A-410│A-409│A-408│A-407│  │  │     │     │     │     │     │     │
    │     │     │     │     │     │     │A-406│A-405│A-404│A-403│A-402│A-401│  DOOR │B-401│B-402│B-403│B-404│B-405│B-406│B-407│B-408│B-409│B-410│B-411│B-412│
    └─────┴─────┴─────┴─────┴─────┴─────┘  │  └─────┴─────┴─────┴─────┴─────┴─────┘
    SOUTH SIDE (left rooms)                 │  SOUTH SIDE (right rooms)
                                         ELEVATOR

    Room naming convention:
    • A-xxx_left  = A-Wing, south side of corridor
    • A-xxx_Right = A-Wing, north side of corridor
    • B-xxx_Right = B-Wing, south side of corridor
    • B-xxx_left  = B-Wing, north side of corridor
```

---

## Algorithm Details

### Localization — WiFi Fingerprinting with Random Forest

**Offline Phase (Training):**
1. WiFi scans collected at each of 39 reference points using a custom Android scanner app.
2. Each CSV records BSSID (MAC), SSID, RSSI for every visible access point.
3. Filenames encode the location label (e.g., `B405_right_20260430_184550.csv`).
4. Preprocessing: Mobile hotspot SSIDs filtered, locally-administered MACs removed, signals below -95 dBm discarded.
5. A **Random Forest classifier** (200 estimators, balanced class weights) is trained on 373-dimensional RSSI vectors.

**Online Phase (Prediction):**
1. Android app captures a WiFi scan via `WifiManager.getScanResults()`.
2. Scan is sent as JSON to `POST /api/localize`.
3. Server converts scan into a 373-dimensional feature vector (RSSI per known BSSID, -100 for unseen APs).
4. Random Forest outputs probability distribution across all 39 room labels.
5. Top prediction returned with confidence score and top-5 alternatives.

**Confidence Thresholding:**
- `confident`: confidence ≥ 0.50
- `interpolated`: 0.20 ≤ confidence < 0.50
- `low_signal`: confidence < 0.20
- `out_of_bounds`: no known BSSIDs detected (user is outside the building)

### Navigation — Dijkstra's Shortest Path

1. The 4th floor is modeled as a **weighted undirected graph** with 54 nodes and ~70 edges.
2. **Node types**: rooms (37), corridor waypoints (14), landmarks (3: elevator, door, mid corridor).
3. **Edge weights** represent walking distance in approximate steps.
4. Dijkstra's algorithm finds the shortest path between any two nodes.
5. **Turn-by-turn directions** are generated by analyzing the path geometry:
   - Detects left/right turns from coordinate changes
   - Identifies wing transitions ("Turn RIGHT towards B-Wing")
   - Calculates total corridor walking distance
   - Estimates walking time (~1.2 m/s)

---

## Project Structure

```
WN_Project/
│
├── app.py                    # Flask server — main entry point (Port 5000)
│                              #   7 API endpoints, serves static frontend
│                              #   Initializes both engines on startup
│
├── fingerprint_engine.py     # WiFi fingerprinting engine
│                              #   WiFiFingerprintEngine class
│                              #   RandomForest (200 trees), 39 labels, 373 BSSIDs
│                              #   predict(), predict_multi_scan(), predict_with_steps()
│
├── navigation_engine.py      # Graph-based navigation engine
│                              #   NavigationGraph class
│                              #   54 nodes, Dijkstra's algorithm
│                              #   Turn-by-turn direction generation
│
├── evaluate_model.py         # Model evaluation (confusion matrix, accuracy)
├── run_test.py               # Quick test runner for predictions
├── requirements.txt          # Python dependencies (flask, scikit-learn, numpy, etc.)
├── README.md                 # This file
│
├── static/                   # Web frontend assets
│   ├── index.html            # Desktop web dashboard
│   ├── map.html              # Mobile-optimized map (loaded in Android WebView)
│   ├── styles.css            # Stylesheet
│   └── app.js                # Frontend JS (Canvas rendering, API calls)
│
├── Training_data/            # WiFi radio map — 92 CSV files, 39 locations
│   ├── A401_left_*.csv       #   Each CSV has columns: BSSID, SSID,
│   ├── B405_right_*.csv      #   Signal Strength, Scan#
│   ├── elevator_origin_*.csv
│   └── ...
│
├── AndroidApp_Source/         # Android app source code (Java)
│   └── app/src/main/java/com/indoor/nav/
│       └── MainActivity.java  # WiFi scanning, server communication, WebView
│
├── test_data/                # Test scans for offline evaluation
```

---

## Setup & Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Android Studio (only if modifying the Android app)

### Backend Setup

```bash
# 1. Navigate to the project directory
cd WN_Project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
python app.py

# 4. Open in browser
# Navigate to http://localhost:5000
```

### Android App Setup

```bash
# 1. Build the APK
cd AndroidApp_Source
./gradlew assembleDebug

# 2. Install on device
# Transfer app/build/outputs/apk/debug/app-debug.apk to your phone

# 3. Open the app and enter the server's local IP (e.g., 192.168.52.54)
```

---

## Usage

### Android App (Primary Interface)
1. Launch **IndoorNav Live** on your phone.
2. Enter the **Server IP Address** (e.g., `192.168.52.54`).
3. Press **Localize Only** → See your predicted room (e.g., "📍 Location: B-405").
4. To navigate: type a destination room (e.g., `B-412`) and press **Navigate**.
5. The app shows turn-by-turn directions and loads the floor plan map with your blue dot and the navigation path highlighted.

### Web Browser (Dashboard)
1. Open `http://<server-ip>:5000` in any browser.
2. The interactive floor plan renders all rooms and corridors on an HTML5 Canvas.
3. Use the **Simulate Localize** dropdown to pick a room (since browsers can't scan WiFi).
4. Select a destination and click **Navigate** to see the animated shortest path.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Web dashboard (index.html) |
| `GET`  | `/map` | Mobile map page (for Android WebView) |
| `GET`  | `/api/locations` | All 39 fingerprinted location labels |
| `GET`  | `/api/rooms` | All navigable rooms with metadata |
| `GET`  | `/api/graph` | Graph nodes + edges for Canvas rendering |
| `POST` | `/api/localize` | Predict room from WiFi scan |
| `POST` | `/api/navigate` | Shortest path between two nodes |
| `POST` | `/api/localize-and-navigate` | Localize + navigate in one call |
| `POST` | `/api/simulate-localize` | Demo/testing (no WiFi needed) |

### Example: Localize Request & Response

**Request:**
```json
POST /api/localize
{
  "wifi_scan": [
    {"bssid": "aa:bb:cc:dd:ee:ff", "rssi": -45},
    {"bssid": "11:22:33:44:55:66", "rssi": -67}
  ]
}
```

**Response:**
```json
{
  "predicted_location": "B-405_right",
  "room_name": "B-405",
  "confidence": 0.87,
  "status": "confident",
  "is_interpolated": false,
  "position": {"x": 1100, "y": 440},
  "top_matches": [
    {"location": "B-405_right", "probability": 0.87},
    {"location": "B-404_right", "probability": 0.06},
    {"location": "B-406_right", "probability": 0.04}
  ]
}
```

---

## Data Collection

WiFi fingerprints were collected using a custom Android WiFi scanner app at 39 reference points:

| Area | Locations | CSV Files | Examples |
|------|-----------|-----------|----------|
| A-Wing (left rooms) | 12 rooms | 33 files | A-401 through A-412 |
| A-Wing (right rooms) | 5 rooms | 12 files | A-413, A-415, A-416, A-418, A-419 |
| B-Wing (right rooms) | 12 rooms | 40 files | B-401 through B-412 |
| B-Wing (left rooms) | 5 rooms | 11 files | B-413, B-415, B-416, B-418, B-419 |
| Landmarks | 5 points | 6 files | elevator_origin, mid_corridor, etc. |

At each point, 2–7 scans were captured with columns: `BSSID`, `SSID`, `Signal Strength`, `Scan#`.

---

## Technologies Used

| Component | Technology |
|-----------|------------|
| **Backend Server** | Python 3, Flask, Flask-CORS |
| **ML Classifier** | scikit-learn `RandomForestClassifier` (200 trees, balanced weights) |
| **Pathfinding** | Dijkstra's Algorithm on weighted undirected graph |
| **Web Frontend** | HTML5 Canvas, Vanilla CSS, JavaScript |
| **Android App** | Java, Android SDK (`WifiManager`, `WebView`) |
| **Data Format** | CSV (BSSID, SSID, RSSI per scan) |
| **Libraries** | NumPy, scikit-learn |

---

## License

This project is developed for academic purposes as part of the Wireless Networks course.
