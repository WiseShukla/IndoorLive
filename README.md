# WiFi Indoor Localization & Navigation System

> 4th Floor, R&D Building — Wireless Networks Project

## Overview

This project implements a **WiFi fingerprint-based indoor localization and navigation system** for the 4th floor of the R&D building. Users can determine their current location using WiFi signal fingerprints and receive turn-by-turn navigation directions to any room on the floor.

### Key Features

- **WiFi Fingerprinting**: Uses RSSI (Received Signal Strength Indicator) data from surrounding WiFi access points to localize the user via Random Forest classification.
- **Indoor Navigation**: Graph-based shortest-path routing using Dijkstra's algorithm with human-readable turn-by-turn directions.
- **Interactive Floor Plan**: Real-time canvas-based visualization with animated navigation paths.
- **Web-Based Frontend**: Works on any modern browser (desktop or mobile).

## System Architecture

```
┌─────────────────────────────────────────────────┐
│                 Web Browser (Frontend)           │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Canvas   │  │ Controls │  │  Directions   │  │
│  │Floor Plan │  │ Panel    │  │  Panel        │  │
│  └──────────┘  └──────────┘  └───────────────┘  │
└─────────────────────┬───────────────────────────┘
                      │ REST API (HTTP)
┌─────────────────────┴───────────────────────────┐
│              Flask Backend (Python)               │
│  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Fingerprint     │  │  Navigation          │  │
│  │  Engine (RF)     │  │  Engine (Dijkstra)   │  │
│  └────────┬─────────┘  └──────────────────────┘  │
│           │                                       │
│  ┌────────┴─────────┐                             │
│  │  WiFi Scan CSVs  │                             │
│  │  (Radio Map)     │                             │
│  └──────────────────┘                             │
└───────────────────────────────────────────────────┘
```

## Algorithm

### Localization (WiFi Fingerprinting with Random Forest)

1. **Offline Phase (Training)**:
   - WiFi scans are collected at each known location (room/corridor/elevator).
   - Each scan records the BSSID (MAC address) and RSSI of all visible access points.
   - A fingerprint database (radio map) is built, mapping locations → RSSI vectors.

2. **Online Phase (Prediction)**:
   - A new WiFi scan is captured from the user's device.
   - The scan is converted to a feature vector (RSSI values for all known BSSIDs).
   - A Random Forest classifier with multi-scan majority voting finds the closest matching location.
   - The predicted location is returned with confidence scores.

### Navigation (Dijkstra's Shortest Path)

1. The floor layout is modeled as a weighted undirected graph.
2. Rooms, corridors, and landmarks are nodes; walkable paths are edges with distance weights.
3. Dijkstra's algorithm computes the shortest path from the user's location to the destination.
4. Turn-by-turn directions are generated from the path topology.

## Project Structure

```
WN_Project/
├── app.py                  # Flask server (main entry point)
├── fingerprint_engine.py   # WiFi fingerprinting & Random Forest classifier
├── navigation_engine.py    # Graph-based navigation with Dijkstra
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── static/
│   ├── index.html          # Web frontend
│   ├── styles.css          # Stylesheet
│   └── app.js              # Frontend JavaScript
├── Training_data/          # WiFi scan data for each location
│   ├── A401_left_...csv
│   └── ...
└── test_data/              # Test scans for evaluation
```

## Setup & Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Steps

```bash
# 1. Navigate to the project directory
cd WN_Project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python app.py

# 4. Open in browser
# Navigate to http://localhost:5000
```

## Usage

1. **Open the web interface** at `http://localhost:5000`
2. **Localize**: Select your current location from the dropdown and click "Localize Me"
3. **Navigate**: Select a destination room and click "Navigate"
4. **Follow Directions**: Turn-by-turn directions appear in the sidebar; the path is animated on the floor plan

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/locations` | List all known fingerprint locations |
| GET | `/api/rooms` | List all navigable rooms |
| GET | `/api/graph` | Get floor plan graph for rendering |
| POST | `/api/localize` | Predict location from WiFi scan data |
| POST | `/api/navigate` | Get path and directions between two points |
| POST | `/api/localize-and-navigate` | Combined localization + navigation |
| POST | `/api/simulate-localize` | Simulate localization for demo/testing |

## Data Collection

WiFi fingerprints were collected using a WiFi scanner app on Android. At each reference point:
- Multiple WiFi scans were captured
- SSID, BSSID, RSSI, and GPS coordinates were recorded
- Data was exported as CSV files

## Technologies Used

- **Backend**: Python, Flask, scikit-learn, NumPy, pandas
- **Frontend**: HTML5 Canvas, Vanilla CSS, JavaScript
- **Algorithm**: Random Forest Classifier, Dijkstra's Shortest Path
- **Data**: WiFi RSSI fingerprints from 92 reference points

## Team Members

| Name | Contribution |
|------|-------------|
| Member 1 | WiFi data collection, fingerprint engine |
| Member 2 | Navigation algorithm, graph modeling |
| Member 3 | Frontend development, canvas rendering |
| Member 4 | Backend API, system integration |
| Member 5 | Testing, documentation, report writing |

## License

This project is developed for academic purposes as part of the Wireless Networks course.
