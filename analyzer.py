# -----------------------------------------------------------------------------
# Telemetry Analysis Engine - MIT License Notice
# Copyright (c) 2026 Your Name. All rights reserved.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR LIABILITY.
# -----------------------------------------------------------------------------

from datetime import datetime, timezone
import json
import math
import urllib.request

def load_application_config(config_filepath="config.json"):
    try:
        with open(config_filepath, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {
            "discord_settings": {"webhook_url": ""},
            "game_physics_limits": {"max_allowed_speed": 15.0, "min_packet_interval_seconds": 0.05},
            "detection_thresholds": {"required_anomalies_to_flag": 3}
        }

CONFIG = load_application_config()
DISCORD_WEBHOOK_URL = CONFIG["discord_settings"]["webhook_url"]
MAX_ALLOWED_SPEED = CONFIG["game_physics_limits"]["max_allowed_speed"]
MIN_PACKET_INTERVAL = CONFIG["game_physics_limits"]["min_packet_interval_seconds"]
REQUIRED_ANOMALIES_TO_FLAG = CONFIG["detection_thresholds"]["required_anomalies_to_flag"]

def send_discord_alert(username, violation_count, details):
    if not DISCORD_WEBHOOK_URL or "your_webhook_id" in DISCORD_WEBHOOK_URL:
        print(f"[SKIPPED DISCORD] No valid webhook URL configured for alert: {username}")
        return

    current_utc_time = datetime.now(timezone.utc).isoformat()
    payload = {
        "username": "Telemetry Sentinel",
        "embeds": [{
            "title": "🚨 3D DISCREPANCY LIMIT REACHED",
            "color": 15158332,  
            "fields": [
                {"name": "Suspected Account", "value": f"`{username}`", "inline": True},
                {"name": "Total Incidents", "value": f"{violation_count} instances", "inline": True},
                {"name": "Violation Flag Type", "value": details, "inline": False}
            ],
            "timestamp": current_utc_time,
            "footer": {"text": "3D Physics Engine Tracker"}
        }]
    }
    data = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(DISCORD_WEBHOOK_URL, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                print(f"[DISCORD] 3D Vector alert sent for user: {username}")
    except Exception as e:
        print(f"[DISCORD ERROR] Failed to send webhook: {e}")

def analyze_3d_telemetry(filepath):
    try:
        with open(filepath, "r") as file:
            telemetry_data = json.load(file)
    except FileNotFoundError:
        print(f"[ERROR] Could not find match data file '{filepath}'")
        return

    player_profiles = {}
    anomaly_counters = {}
    already_flagged = set()  

    for entry in telemetry_data:
        p_id = entry["player_id"]
        event = entry["event"]
        c_time = entry["client_time"]
        s_time = entry["server_receive_time"]

        # Track x, y, and z state vectors
        if p_id not in player_profiles:
            player_profiles[p_id] = {"last_client_time": None, "last_server_time": None, "x": None, "y": None, "z": None}
            anomaly_counters[p_id] = 0

        prof = player_profiles[p_id]

        if event == "position":
            x, y, z = entry["x"], entry["y"], entry["z"]
            
            if prof["last_client_time"] is not None:
                server_dt = s_time - prof["last_server_time"]
                client_dt = c_time - prof["last_client_time"]
                
                # --- NEW MATH BLOCK: 3D Euclidean Distance ---
                distance_3d = math.sqrt(
                    (x - prof["x"])**2 + 
                    (y - prof["y"])**2 + 
                    (z - prof["z"])**2
                )

                speed = distance_3d / client_dt if (server_dt < MIN_PACKET_INTERVAL and client_dt > server_dt) else (distance_3d / server_dt if server_dt > 0 else 0)

                if speed > MAX_ALLOWED_SPEED:
                    anomaly_counters[p_id] += 1
                    if anomaly_counters[p_id] >= REQUIRED_ANOMALIES_TO_FLAG and p_id not in already_flagged:
                        reason_msg = f"3D velocity boundary breached. Speed calculated at {round(speed, 2)} units/s (Max limit: {MAX_ALLOWED_SPEED})."
                        send_discord_alert(p_id, anomaly_counters[p_id], reason_msg)
                        already_flagged.add(p_id)

                     # Keep 3D coordinates updated in the user map profile
            prof["last_client_time"] = c_time
            prof["last_server_time"] = s_time
            prof["x"], prof["y"], prof["z"] = x, y, z

    # --- NEW TRACKING CONFIRMATION BLOCK ---
    print("\n" + "="*45)
    print("🎯 TELEMETRY PIPELINE DISPATCH SUMMARY")
    print("="*45)
    print(f"Status: SUCCESS (Process complete)")
    print(f"Total Unique Players Tracked: {len(player_profiles)}")
    
    # Check if anyone actually triggered an alert
    if len(already_flagged) == 0:
        print("Result: CLEAN MATCH (No suspicious activity or anomalies detected).")
    else:
        print(f"Result: ANOMALIES DETECTED. Flagged users: {list(already_flagged)}")
    print("="*45 + "\n")

# Run the 3D analytics tracking pass
analyze_3d_telemetry("telemetry.json")

