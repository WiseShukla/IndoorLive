"""
Flask Backend Server for Indoor Localization & Navigation
==========================================================
This is the main entry point for the application. It serves:

1. A REST API for WiFi fingerprint-based localization
2. A REST API for indoor navigation (shortest path + directions)
3. The frontend web interface (static HTML/CSS/JS)

API Endpoints:
    GET  /                      - Serve the main web interface
    GET  /api/locations          - Get all known locations
    GET  /api/rooms              - Get all navigable rooms
    GET  /api/graph              - Get the floor plan graph for rendering
    POST /api/localize           - Predict location from a WiFi scan
    POST /api/navigate           - Get navigation directions between two points
    POST /api/localize-and-navigate - Localize user and navigate to destination

Usage:
    python app.py
    Then open http://localhost:5000 in a browser.
"""

import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from fingerprint_engine import WiFiFingerprintEngine
from navigation_engine import NavigationGraph

# ============================================================
# Initialize Flask app
# ============================================================
app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)  # Enable CORS for all routes (needed for browser WiFi scanning)

# ============================================================
# Initialize engines
# ============================================================
print("=" * 60)
print("  Indoor Localization & Navigation System")
print("  4th Floor, R&D Building")
print("=" * 60)

# WiFi Fingerprint Engine
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Training_data')
print(f"\nLoading WiFi fingerprint data from: {DATA_DIR}")

engine = WiFiFingerprintEngine(data_dir=DATA_DIR, k=5)
engine.load_data()
engine.train()

# Navigation Graph
nav = NavigationGraph()
print("\nNavigation graph loaded successfully")
print(f"  Nodes: {len(nav.graph)}")
print(f"  Rooms: {len(nav.get_navigable_rooms())}")
print("=" * 60)


# ============================================================
# API Routes
# ============================================================

@app.route('/')
def index():
    """Serve the main web interface."""
    return send_from_directory('static', 'index.html')


@app.route('/map')
def map_view():
    """Serve the mobile-optimized map view."""
    return send_from_directory('static', 'map.html')


@app.route('/api/locations', methods=['GET'])
def get_locations():
    """
    Get all known WiFi fingerprint locations.
    
    Returns:
        JSON: {'locations': ['A-401_left', 'A-402_left', ...]}
    """
    locations = engine.get_all_locations()
    return jsonify({'locations': locations})


@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    """
    Get all navigable rooms for the destination dropdown.
    
    Returns:
        JSON: {'rooms': [{'id': 'A-401_left', 'name': 'Room A-401', ...}, ...]}
    """
    rooms = nav.get_navigable_rooms()
    return jsonify({'rooms': rooms})


@app.route('/api/graph', methods=['GET'])
def get_graph():
    """
    Get the floor plan graph structure for frontend rendering.
    
    Returns:
        JSON: {'nodes': [...], 'edges': [...]}
    """
    graph_data = nav.get_graph_data()
    return jsonify(graph_data)


@app.route('/api/localize', methods=['POST'])
def localize():
    """
    Predict user location from a WiFi scan.
    
    Request Body:
        {
            "wifi_scan": [
                {"bssid": "aa:bb:cc:dd:ee:ff", "rssi": -65},
                ...
            ]
        }
    
    Returns:
        JSON: {
            'predicted_location': 'A-401_left',
            'room_name': 'A-401',
            'confidence': 0.85,
            'top_matches': [...]
        }
    """
    data = request.get_json()

    if not data or 'wifi_scan' not in data:
        return jsonify({'error': 'Missing wifi_scan in request body'}), 400

    # Convert scan array to dictionary
    scan_dict = {}
    for ap in data['wifi_scan']:
        bssid = ap.get('bssid', '').strip().lower()
        rssi = ap.get('rssi', -100)
        if bssid and rssi != 0:
            scan_dict[bssid] = rssi

    if not scan_dict:
        return jsonify({'error': 'No valid WiFi data in scan'}), 400

    # Check for step count (WiFi + PDR fusion)
    step_count = data.get('step_count', 0)
    if step_count and int(step_count) > 0:
        result = engine.predict_with_steps(scan_dict, int(step_count), nav)
    else:
        result = engine.predict(scan_dict)

    result['room_name'] = nav.get_room_name(result['predicted_location'])
    
    # Add node position for the predicted location
    node_id = nav.find_node_for_location(result['predicted_location'])
    if node_id and node_id in nav.node_positions:
        result['position'] = {
            'x': nav.node_positions[node_id][0],
            'y': nav.node_positions[node_id][1]
        }

    return jsonify(result)


@app.route('/api/navigate', methods=['POST'])
def navigate():
    """
    Get navigation directions between two points.
    
    Request Body:
        {
            "start": "elevator",         # Starting node ID
            "end": "B-412_Right"         # Destination node ID
        }
    
    Returns:
        JSON: {
            'path': ['elevator', 'door_elevator', ...],
            'distance': 45.0,
            'directions': ['Start at Elevator', ...],
            'path_positions': [[500, 520], ...]
        }
    """
    data = request.get_json()

    if not data or 'start' not in data or 'end' not in data:
        return jsonify({'error': 'Missing start or end in request body'}), 400

    start = data['start']
    end = data['end']

    # Try to find matching nodes
    start_node = nav.find_node_for_location(start)
    end_node = nav.find_node_for_location(end)

    if not start_node:
        return jsonify({'error': f'Unknown start location: {start}'}), 400
    if not end_node:
        return jsonify({'error': f'Unknown destination: {end}'}), 400

    result = nav.find_shortest_path(start_node, end_node)

    if result is None:
        return jsonify({'error': 'No path found between these locations'}), 404

    return jsonify(result)


@app.route('/api/localize-and-navigate', methods=['POST'])
def localize_and_navigate():
    """
    Combined endpoint: localize the user and navigate to a destination.
    
    Request Body:
        {
            "wifi_scan": [...],          # Current WiFi scan data
            "destination": "B-412_Right" # Destination node ID
        }
    
    Returns:
        JSON: {
            'localization': {...},   # Localization result
            'navigation': {...}      # Navigation result with path & directions
        }
    """
    data = request.get_json()

    if not data or 'wifi_scan' not in data or 'destination' not in data:
        return jsonify({'error': 'Missing wifi_scan or destination'}), 400

    # Step 1: Localize (with optional step count)
    scan_dict = {}
    for ap in data['wifi_scan']:
        bssid = ap.get('bssid', '').strip().lower()
        rssi = ap.get('rssi', -100)
        if bssid and rssi != 0:
            scan_dict[bssid] = rssi

    if not scan_dict:
        return jsonify({'error': 'No valid WiFi data'}), 400

    step_count = data.get('step_count', 0)
    if step_count and int(step_count) > 0:
        loc_result = engine.predict_with_steps(scan_dict, int(step_count), nav)
    else:
        loc_result = engine.predict(scan_dict)
    loc_result['room_name'] = nav.get_room_name(loc_result['predicted_location'])

    # Step 2: Navigate
    start_node = nav.find_node_for_location(loc_result['predicted_location'])
    end_node = nav.find_node_for_location(data['destination'])

    if not start_node:
        return jsonify({
            'localization': loc_result,
            'navigation': {'error': 'Could not map predicted location to graph'}
        })

    if not end_node:
        return jsonify({
            'localization': loc_result,
            'navigation': {'error': f'Unknown destination: {data["destination"]}'}
        })

    nav_result = nav.find_shortest_path(start_node, end_node)

    return jsonify({
        'localization': loc_result,
        'navigation': nav_result if nav_result else {'error': 'No path found'}
    })


@app.route('/api/simulate-localize', methods=['POST'])
def simulate_localize():
    """
    Simulate localization by returning a selected location (for demo/testing).
    Used when real WiFi scanning is not available in the browser.
    
    Request Body:
        {
            "location": "A-401_left"  # Simulated current location
        }
    
    Returns:
        JSON: Same as /api/localize
    """
    data = request.get_json()
    location = data.get('location', 'elevator')
    step_count = data.get('step_count', 0)

    node_id = nav.find_node_for_location(location)
    position = None
    if node_id and node_id in nav.node_positions:
        position = {
            'x': nav.node_positions[node_id][0],
            'y': nav.node_positions[node_id][1]
        }

    return jsonify({
        'predicted_location': location,
        'room_name': nav.get_room_name(location),
        'confidence': 1.0,
        'top_matches': [{'location': location, 'probability': 1.0}],
        'position': position,
        'step_count': int(step_count) if step_count else 0,
        'simulated': True
    })


# ============================================================
# Main entry point
# ============================================================
if __name__ == '__main__':
    print("\n>>> Starting server at http://localhost:5000")
    print("    Open this URL in your browser to use the application.\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
