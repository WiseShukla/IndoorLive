"""
WiFi Fingerprint Engine — Indoor localization for 4th floor R&D building.
Uses WiFi RSSI matching + step count from elevator for room-level accuracy.
"""

import os
import csv
import numpy as np
import json
import warnings

warnings.filterwarnings("ignore")


class WiFiFingerprintEngine:
    """WiFi fingerprint-based indoor localization engine."""

    RSSI_FLOOR = -100  # default value for APs not detected
    MIN_USEFUL_RSSI = -95  # ignore signals weaker than this

    # mobile hotspot SSIDs to filter out (they move around)
    MOBILE_SSID_KEYWORDS = [
        'hotspot', 'iphone', 'galaxy', 'redmi', 'oneplus', 'pixel',
        'realme', 'vivo', 'oppo', 'poco', 'samsung', 'android',
        'jio', 'airtel_rajesh', 'sunny', 'chinu', 'habibi',
        'dk lakda', 'anuj', 'ravi_', 'debarshi', 'shivam'
    ]

    # stable university APs we trust
    INFRASTRUCTURE_SSIDS = {
        'faculty-staff-n', 'eduroam', 'guest-n', 'sensor',
        'laptop-s', 'mobile-s'
    }

    CONFIDENCE_THRESHOLD = 0.50

    def __init__(self, data_dir=".", k=3):
        self.data_dir = data_dir
        self.k = k
        self.fingerprints = {}       # {location: [{bssid: rssi}, ...]}
        self.all_bssids = set()
        self.bssid_ssid_map = {}     # {bssid: ssid}
        self.classifier = None
        self.location_labels = []
        self.feature_bssids = []

    def load_data(self):
        """Load WiFi scan CSVs from the data directory. Filename = location label."""
        import re
        csv_files = [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]

        for csv_file in csv_files:
            # Clean filename to get true location label
            location = csv_file.replace('.csv', '').strip()
            # Remove timestamp _20260430_191356 even if there are trailing spaces
            location = re.sub(r'_\d{8}_\d{6}.*$', '', location)
            # Remove step modifiers _1step_ahead
            location = re.sub(r'_\d+step_ahead.*$', '', location)
            location = re.sub(r'_1step_behind.*$', '', location)
            
            # Format A401 to A-401 to match navigation graph
            match = re.match(r'^([ABab])(\d{3})(.*)$', location)
            if match:
                location = f"{match.group(1).upper()}-{match.group(2)}{match.group(3)}"

            filepath = os.path.join(self.data_dir, csv_file)
            scans = self._parse_csv(filepath)

            if scans:
                if location not in self.fingerprints:
                    self.fingerprints[location] = []
                self.fingerprints[location].extend(scans)
                for scan in scans:
                    for bssid in scan:
                        self.all_bssids.add(bssid)
                print(f"  Loaded {len(scans)} scan(s) from {csv_file} -> mapped to {location}")
            else:
                print(f"  WARNING: {csv_file} has no valid scans!")

        print(f"\nTotal locations loaded: {len(self.fingerprints)}")
        print(f"Total unique BSSIDs: {len(self.all_bssids)}")

    def _parse_csv(self, filepath):
        """Parse a WiFi scan CSV into list of {bssid: rssi} dicts."""
        scans = self._parse_csv_with_keys(filepath)
        return list(scans.values()) if scans else []

    def _parse_csv_with_keys(self, filepath):
        """Parse CSV, group rows by GPS coordinates. Returns {coord_key: {bssid: rssi}}."""
        scans_by_coords = {}

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bssid = row.get('BSSID', '').strip().lower()
                    ssid = row.get('SSID', '').strip()
                    try:
                        rssi_val = row.get('Signal Strength') or row.get('Signal_Level_dBm')
                        rssi = int(rssi_val) if rssi_val else self.RSSI_FLOOR
                    except (ValueError, TypeError):
                        rssi = self.RSSI_FLOOR

                    if not bssid:
                        continue

                    # treat 0 as "not detected"
                    if rssi == 0:
                        rssi = self.RSSI_FLOOR

                    # skip very weak signals
                    if rssi < self.MIN_USEFUL_RSSI:
                        continue

                    # skip locally administered MACs (usually mobile hotspots)
                    try:
                        first_octet = int(bssid.split(':')[0], 16)
                        if first_octet & 0x02:
                            continue
                    except (ValueError, IndexError):
                        pass

                    # skip known mobile hotspot names
                    ssid_lower = ssid.lower()
                    if any(kw in ssid_lower for kw in self.MOBILE_SSID_KEYWORDS):
                        continue

                    # skip hidden networks with random MACs
                    if not ssid and bssid:
                        try:
                            fo = int(bssid.split(':')[0], 16)
                            if fo & 0x02:
                                continue
                        except (ValueError, IndexError):
                            pass

                    scan_num = row.get('Scan#', '1')
                    coord_key = f"scan_{scan_num}"

                    if coord_key not in scans_by_coords:
                        scans_by_coords[coord_key] = {}

                    # keep the strongest signal per BSSID
                    if bssid not in scans_by_coords[coord_key] or rssi > scans_by_coords[coord_key][bssid]:
                        scans_by_coords[coord_key][bssid] = rssi

                    if ssid and bssid not in self.bssid_ssid_map:
                        self.bssid_ssid_map[bssid] = ssid

        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return {}

        return scans_by_coords

    def _build_feature_vector(self, scan_dict):
        """Convert {bssid: rssi} to a fixed-length vector for all known BSSIDs."""
        return [scan_dict.get(bssid, self.RSSI_FLOOR) for bssid in self.feature_bssids]

    def train(self):
        """Train the model using RandomForestClassifier."""
        from sklearn.ensemble import RandomForestClassifier

        self.feature_bssids = sorted(list(self.all_bssids))

        X = []
        y = []

        for location, scans in self.fingerprints.items():
            for scan in scans:
                X.append(self._build_feature_vector(scan))
                y.append(location)

        if not X:
            print("  ERROR: No data to train!")
            self.classifier = None
            return

        self.classifier = RandomForestClassifier(n_estimators=200,class_weight='balanced', random_state=42,n_jobs=-1)
        self.classifier.fit(X, y)
        self.location_labels = self.classifier.classes_

        print(f"\n  Model trained with {len(self.location_labels)} unique locations using RandomForestClassifier")

    def predict(self, scan_dict):
        """Predict location from a WiFi scan using RandomForestClassifier."""
        if self.classifier is None or self.classifier is True:
            return {'error': 'Model not trained'}

        known_bssid_count = sum(1 for bssid in scan_dict.keys() if bssid in self.feature_bssids)
        if known_bssid_count == 0:
            return {
                'predicted_location': 'Unknown (Not in College Building)',
                'confidence': 0.0,
                'top_matches': [{'location': 'Unknown', 'probability': 1.0}],
                'is_interpolated': False,
                'status': 'out_of_bounds'
            }

        vector = self._build_feature_vector(scan_dict)
        probas = self.classifier.predict_proba([vector])[0]
        classes = self.classifier.classes_

        # Sort classes by probability
        sorted_indices = np.argsort(probas)[::-1]

        predicted_location = classes[sorted_indices[0]]
        confidence = probas[sorted_indices[0]]

        top_matches = []
        for idx in sorted_indices[:5]:
            prob = probas[idx]
            if prob > 0.001:
                top_matches.append({'location': classes[idx], 'probability': round(float(prob), 4)})

        if not top_matches:
            return {'error': 'No matching locations found'}

        is_interpolated = False
        status = 'confident'
        if confidence < self.CONFIDENCE_THRESHOLD:
            is_interpolated = True
            status = 'low_signal' if confidence < 0.20 else 'interpolated'

        return {
            'predicted_location': predicted_location,
            'confidence': round(confidence, 4),
            'top_matches': top_matches,
            'is_interpolated': is_interpolated,
            'status': status
        }

    def predict_multi_scan(self, scan_list):
        """Predict from multiple scans using weighted majority voting."""
        if not scan_list:
            return {'error': 'No scans provided'}

        predictions = [self.predict(scan) for scan in scan_list]

        vote_scores = {}
        for pred in predictions:
            loc = pred['predicted_location']
            vote_scores[loc] = vote_scores.get(loc, 0) + pred['confidence']

        best_location = max(vote_scores, key=vote_scores.get)
        avg_confidence = vote_scores[best_location] / len(scan_list)

        best_pred = next(p for p in predictions if p['predicted_location'] == best_location)
        best_pred['confidence'] = round(avg_confidence, 4)
        best_pred['scan_count'] = len(scan_list)
        return best_pred

    def get_all_locations(self):
        """Return all known location labels."""
        return sorted(list(self.fingerprints.keys()))

    def predict_with_steps(self, scan_dict, step_count, nav_graph=None):
        """
        Predict location using WiFi + step count from elevator.
        WiFi determines the wing (A/B), steps determine exact corridor position.
        """
        if nav_graph is None:
            from navigation_engine import NavigationGraph
            nav_graph = NavigationGraph()

        # WiFi tells us which wing
        wifi_result = self.predict(scan_dict)
        wifi_zone = wifi_result['predicted_location']

        wing_votes = {'A': 0, 'B': 0}
        for match in wifi_result.get('top_matches', []):
            loc = match['location']
            prob = match['probability']
            if loc.startswith('B') or 'B-' in loc or 'B_' in loc:
                wing_votes['B'] += prob
            elif loc.startswith('A') or 'A-' in loc or 'A_' in loc:
                wing_votes['A'] += prob

        detected_wing = 'B' if wing_votes['B'] >= wing_votes['A'] else 'A'

        # step count mapping (calibrated: 28 steps elevator->corridor_mid, 5.3 steps per graph unit)
        ELEVATOR_TO_MID_STEPS = 28
        CORRIDOR_SCALE = 5.3
        corridor_steps = max(0, step_count - ELEVATOR_TO_MID_STEPS)

        # find which room in the detected wing matches the step count
        room_candidates = []
        for node_id, info in nav_graph.node_info.items():
            if info['type'] != 'room' or info['wing'] != detected_wing:
                continue

            result = nav_graph.find_shortest_path('corridor_mid', node_id)
            if result:
                path = result['path']
                total_dist = result['distance']

                # subtract the perpendicular door distance to get corridor-only distance
                if len(path) >= 2:
                    last_node, prev_node = path[-1], path[-2]
                    for neighbor, w in nav_graph.graph[prev_node]:
                        if neighbor == last_node:
                            corridor_dist = total_dist - w
                            break
                    else:
                        corridor_dist = total_dist
                else:
                    corridor_dist = total_dist

                room_total_steps = ELEVATOR_TO_MID_STEPS + corridor_dist * CORRIDOR_SCALE
                step_diff = abs(step_count - room_total_steps)
                room_candidates.append({
                    'room': node_id,
                    'expected_steps': round(room_total_steps, 1),
                    'step_diff': round(step_diff, 1),
                    'corridor_graph_dist': corridor_dist
                })

        room_candidates.sort(key=lambda x: x['step_diff'])

        if not room_candidates:
            return wifi_result

        best_room = room_candidates[0]['room']
        best_diff = room_candidates[0]['step_diff']
        step_confidence = max(0.1, 1.0 - best_diff / 30.0)

        top_step_matches = []
        for rc in room_candidates[:5]:
            top_step_matches.append({
                'location': rc['room'],
                'probability': round(max(0.01, 1.0 - rc['step_diff'] / 50.0), 4),
                'expected_steps': rc['expected_steps'],
                'step_diff': rc['step_diff']
            })

        return {
            'predicted_location': best_room,
            'confidence': round(step_confidence, 4),
            'top_matches': top_step_matches,
            'wifi_zone': wifi_zone,
            'wifi_wing': detected_wing,
            'step_count': step_count,
            'method': 'wifi+steps',
            'is_interpolated': best_diff > 10,
            'status': 'confident' if best_diff <= 10 else 'interpolated'
        }
