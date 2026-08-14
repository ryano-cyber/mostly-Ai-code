# 🚨 3D Behavioral Telemetry Engine & Live Lobby Scanner

A modular, server-side validation system written in Python that automatically scans active match logs to ingest player lists and monitors live telemetry data arrays for 3D physics boundaries.

## 🛠️ System Architecture & Automated Features

* **Automated Name Extraction:** Employs an asynchronous log watcher using RegEx processing patterns to pull live usernames out of connection text traces (`lobby.log`) the exact millisecond they join a match.
* **Deterministic 3D Velocity Tracking:** Uses 3D Euclidean distance calculations ($v = \sqrt{\Delta x^2 + \Delta y^2 + \Delta z^2} / \Delta t$) to monitor vector thresholds.
* **Network Burst Shield:** Measures server network arrival timing differences against client clock steps to handle packet-loss compression spikes smoothly.
* **Discord Integration Layer:** Packages incident summaries into JSON payloads and dispatches localized alerts to private operational server nodes.

## 🗂️ Project Repository Layout

* `analyzer.py` - Core multi-threaded Python engine running the background file watchers.
* `config.json` - System threshold limits dashboard configuration parameters.
* `LICENSE` - Commercial protection under the MIT software liability shield.
* `.gitignore` - Production security file preventing sensitive token data leaks.

## 🚀 Installation & Execution

1. Configure your private destination endpoints inside `config.json`.
2. Start the continuous automated folder execution monitor pipeline:
   ```bash
   python analyzer.py
   ```
3. Append incoming console text data directly into `lobby.log` to watch the engine parse live configurations instantly.
