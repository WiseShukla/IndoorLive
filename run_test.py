"""
Test script: Predict location from test_1.csv using WiFi + Step Count.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fingerprint_engine import WiFiFingerprintEngine
from navigation_engine import NavigationGraph


def main():
    # ---- Step 1: Load training data and train ----
    print("=" * 60)
    print("  LOADING TRAINING DATA")
    print("=" * 60)

    engine = WiFiFingerprintEngine(data_dir="Training_data", k=5)
    engine.load_data()
    engine.train()

    nav = NavigationGraph()

    # ---- Step 2: Parse the test scan ----
    print("\n" + "=" * 60)
    print("  PARSING TEST SCAN: test_data/mid_corridor_right_7steps_ahead_test3_20260430_193834.csv")
    print("=" * 60)

    test_scans = engine._parse_csv("test_data/mid_corridor_right_7steps_ahead_test3_20260430_193834.csv")
    print(f"  Found {len(test_scans)} scan(s) in the test file")

    if not test_scans:
        print("  ERROR: No valid scans found in test file!")
        return

    # Use up to 3 consecutive scans for a rolling window prediction
    scans_to_check = test_scans[:3]
    print(f"  Using {len(scans_to_check)} scan(s) for majority voting to improve stability...")

    # ---- Step 3: WiFi-Only Prediction ----
    print("\n" + "=" * 60)
    print("  WiFi-ONLY PREDICTION (Multi-Scan Voting)")
    print("=" * 60)

    wifi_result = engine.predict_multi_scan(scans_to_check)
    print(f"\n  Predicted Location : {wifi_result['predicted_location']}")
    print(f"  Confidence         : {wifi_result['confidence'] * 100:.2f}%")
    print(f"  Status             : {wifi_result['status']}")
    print(f"  Top Matches:")
    for match in wifi_result['top_matches']:
        bar_len = int(match['probability'] * 40)
        bar = "#" * bar_len
        print(f"    {match['location']:40s}  {match['probability']*100:6.2f}%  {bar}")

    # ---- Step 4: WiFi + Step Count Prediction ----
    # Disabled as per user request
    
    print("\n" + "=" * 60)
    print(f"  >> FINAL PREDICTED LOCATION: {wifi_result['predicted_location']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
