# -----------------------------------------------------------------------------
# 3D Telemetry Engine & Live Lobby Scanner - MIT License Notice
# Copyright (c) 2026 Your Name. All rights reserved.
# -----------------------------------------------------------------------------

from datetime import datetime, timezone
import json
import math
import os
import re
import time
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

# Regex to pull names from generic lobby text outputs
# Matches structural formats like: PlayerName connected or LOBBY_JOIN: PlayerName
JOIN_PATTERN = re.compile(r'(?i)connected|entered|join')
NAME_PATTERN = re.compile(r'(?:"([^<"]+)"|join:\s*([^\s\n]+)|([^\s]+)\s+connected)')

def send_discord_alert(username, violation_count, details):
    if not DISCORD_WEBHOOK_URL or "your_webhook_id" in DISCORD_WEBHOOK_URL:
        print(f"[SKIPPED DISCORD] No webhook configured for alert: {username}")
        return

    current_utc_time = datetime.now(timezone.utc).isoformat()
    payload = {
        "username": "Telemetry Sentinel",
        "embeds": [{
            "title": "🚨 AUTOMATED LOBBY DETECTION ALERT",
            "color": 15158332,  
            "fields": [
                {"name": "Flagged Account", "value": f"`{username}`", "inline": True},
                {"name": "Total Incidents", "value": f"{violation_count} instances", "inline": True},
                {"name": "Violation Details", "value": details, "inline": False}
            ],
            "timestamp": current_utc_time,
            "footer": {"text": "Live Extraction Subsystem v1.1.0"}
        }]
    }
    data = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(DISCORD_WEBHOOK_URL, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                print(f"[DISCORD] Alert dispatched for user: {username}")
    except Exception as e:
        print(f"[DISCORD ERROR] Failed to send webhook: {e}")

def run_live_pipeline_monitor(log_filepath="lobby.log", data_filepath="telemetry.json"):
    """Watch loops infinitely, pulling player names and parsing structural telemetry data."""
    print(f"[ENGINE INITIALIZED] Watching '{log_filepath}' for names and '{data_filepath}' for metrics...")
    
    known_lobby = set()
    player_profiles = {}
    anomaly_counters = {}
    already_flagged = set()

    last_log_size = 0
    last_data_mtime = 0

    try:
        while True:
            # 1. SCAN FOR AUTOMATIC LOBBY NAMES
            if os.path.exists(log_filepath):
                current_size = os.path.getsize(log_filepath)
                if current_size > last_log_size:
                    with open(log_filepath, "r", encoding="utf-8", errors="ignore") as f:
                        f.seek(last_log_size)
                        new_lines = f.readlines()
                        for line in new_lines:
                            if JOIN_PATTERN.search(line):
                                match = NAME_PATTERN.search(line)
                                if match:
                                    # Extract whichever regex group captured the username string
                                    username = next(g for g in match.groups() if g is not None)
                                    if username not in known_lobby:
                                        known_lobby.add(username)
                                        print(f"[AUTO-INGEST] Extracted lobby player: '{username}'")
                    last_log_size = current_size

            # 2. PARSE MOVEMENT DISCREPANCIES FOR DETECTED PLAYERS
            if os.path.exists(data_filepath):
                current_mtime = os.path.getmtime(data_filepath)
                if current_mtime > last_data_mtime:
                    try:
                        with open(data_filepath, "r") as f:
                            telemetry_data = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        time.sleep(0.1) # Wait slightly if the file is actively being written to
                        continue

                    for entry in telemetry_data:
                        p_id = entry["player_id"]
                        
                        # Only validate metrics if the user belongs to our captured lobby list
                        if known_lobby and p_id not in known_lobby:
                            continue

                        event = entry["event"]
                        c_time = entry["client_time"]
                        s_time = entry["server_receive_time"]

                        if p_id not in player_profiles:
                            player_profiles[p_id] = {"last_c": None, "last_s": None, "x": None, "y": None, "z": None}
                            anomaly_counters[p_id] = 0

                        prof = player_profiles[p_id]

                        if event == "position":
                            x, y, z = entry["x"], entry["y"], entry["z"]
                            if prof["last_c"] is not None:
                                server_dt = s_time - prof["last_s"]
                                client_dt = c_time - prof["last_c"]
                                distance = math.sqrt((x-prof["x"])**2 + (y-prof["y"])**2 + (z-prof["z"])**2)

                                speed = distance / client_dt if (server_dt < MIN_PACKET_INTERVAL and client_dt > server_dt) else (distance / server_dt if server_dt > 0 else 0)

                                if speed > MAX_ALLOWED_SPEED:
                                    anomaly_counters[p_id] += 1
                                    if anomaly_counters[p_id] >= REQUIRED_ANOMALIES_TO_FLAG and p_id not in already_flagged:
                                        reason = f"Automated check failure. 3D speed reached {round(speed, 2)} units/s."
                                        send_discord_alert(p_id, anomaly_counters[p_id], reason)
                                        already_flagged.add(p_id)

                            prof["last_c"], prof["last_s"] = c_time, s_time
                            prof["x"], prof["y"], prof["z"] = x, y, z

                    last_data_mtime = current_mtime
            
            time.sleep(0.5) # Sleep for 500ms between directory sweeps to avoid high CPU usage
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Terminating loop monitor pipeline.")

if __name__ == "__main__":
    run_live_pipeline_monitor()
