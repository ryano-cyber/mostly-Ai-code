from datetime import datetime, timezone
import json
import math
import urllib.request

def load_application_config(config_filepath="config.json"):
    """Reads the external JSON configuration file customized by the user."""
    try:
        with open(config_filepath, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"[CRITICAL ERROR] Missing '{config_filepath}' file! Restoring internal defaults.")
        # Fallback defaults if the customer accidentally deletes the file
        return {
            "discord_settings": {"webhook_url": ""},
            "game_physics_limits": {"max_allowed_speed": 15.0, "min_packet_interval_seconds": 0.05},
            "detection_thresholds": {"required_anomalies_to_flag": 3, "critical_headshot_streak": 5}
        }

# --- Load settings dynamically ---
CONFIG = load_application_config()

# Assign config variables smoothly for the rest of the script logic
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
            "title": "🚨 DISCREPANCY LIMIT REACHED",
            "color": 15158332,  
            "fields": [
                {"name": "Suspected Account", "value": f"`{username}`", "inline": True},
                {"name": "Total Incidents", "value": f"{violation_count} instances", "inline": True},
                {"name": "Violation Flag Type", "value": details, "inline": False}
            ],
            "timestamp": current_utc_time,
            "footer": {"text": "System Incident Clock Time"}
        }]
    }
    data = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(DISCORD_WEBHOOK_URL, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                print(f"[DISCORD] Notification sent for user: {username}")
    except Exception as e:
        print(f"[DISCORD ERROR] Failed to send webhook: {e}")

def analyze_telemetry_file(filepath):
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

        if p_id not in player_profiles:
            player_profiles[p_id] = {"last_client_time": None, "last_server_time": None, "x": None, "y": None}
            anomaly_counters[p_id] = 0

        prof = player_profiles[p_id]

        if event == "position":
            x, y = entry["x"], entry["y"]
            if prof["last_client_time"] is not None:
                server_dt = s_time - prof["last_server_time"]
                client_dt = c_time - prof["last_client_time"]
                distance = math.sqrt((x - prof["x"])**2 + (y - prof["y"])**2)

                speed = distance / client_dt if (server_dt < MIN_PACKET_INTERVAL and client_dt > server_dt) else (distance / server_dt if server_dt > 0 else 0)

                if speed > MAX_ALLOWED_SPEED:
                    anomaly_counters[p_id] += 1
                    if anomaly_counters[p_id] >= REQUIRED_ANOMALIES_TO_FLAG and p_id not in already_flagged:
                        reason_msg = f"Velocity limit violation ({MAX_ALLOWED_SPEED} units/s exceeded)."
                        send_discord_alert(p_id, anomaly_counters[p_id], reason_msg)
                        already_flagged.add(p_id)

            prof["last_client_time"] = c_time
            prof["last_server_time"] = s_time
            prof["x"], prof["y"] = x, y

# Execute using our data file
analyze_telemetry_file("telemetry.json")
