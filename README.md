# 🛡️ SysPulse Pro: Real-Time Network & System Performance Monitor

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![SQLite3](https://img.shields.io/badge/SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com/python/)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)

**SysPulse Pro** is a full-stack system telemetry, network monitoring, and anomaly detection web application built in Python. Designed as an interactive dashboard, it polls real-time hardware and network metrics (`psutil`), authenticates users via **SHA-256 encrypted credentials**, logs threshold breaches to a local **SQLite3** relational database, and triggers automated desktop and web notifications (`plyer`) when system resources exceed user-defined thresholds.

---

## ✨ Key Features

* **🔐 SHA-256 Web Authentication Portal:** Full-page login and user registration gate backed by SQLite3 using parameterized queries to prevent SQL injection.
* **⚡ Real-Time Hardware & Network Telemetry:** Live tracking of CPU utilization, RAM allocation, Disk Read/Write throughput (MB/s), and Network Upload/Download packet rates (KB/s).
* **🎛️ Cyber-Glass Interactive UI:** Custom glassmorphism CSS styling, live Plotly radial speedometer gauges, and dark-mode neon time-series charts.
* **🗄️ Automated SQLite3 Anomaly Auditing:** Automatically records timestamped threshold breaches with severity levels (`WARNING`, `HIGH`, `CRITICAL`) and supports 1-click CSV export for administrative reports.
* **🔥 Multi-Threaded CPU Stress Tester:** Built-in demonstration tool that spawns 6 background daemon threads (`threading`) to spike CPU cores on demand without freezing the web interface.
* **🔔 Smart Alert Cooldown Engine:** Dispatches OS-level desktop notifications (`plyer`) and web toast alerts with a configurable cooldown timer to prevent alert fatigue.
* **🔍 Live OS Process Inspector:** Queries active system processes (`PID`, `Process Name`, `CPU %`, `Memory %`) sorted dynamically by resource consumption.

---

## 🛠️ Tech Stack

| Layer | Technology | Role in Project |
| :--- | :--- | :--- |
| **Frontend & Server** | `Streamlit` + Custom CSS3 | Cyber-Glass dashboard UI, session routing, and live auto-refresh |
| **Hardware Polling** | `psutil` | Cross-platform CPU, RAM, Disk I/O, Network throughput, and OS process inspection |
| **Database & Security** | `sqlite3` + `hashlib` | Persistent storage for SHA-256 hashed user accounts, telemetry history, and anomaly logs |
| **Data Visualization** | `Plotly` & `Pandas` | Interactive radial gauges, time-series area charts, and CSV report generation |
| **Concurrency** | `threading` | Non-blocking background compute threads for live CPU stress testing |
| **Alerting** | `plyer` + `st.toast` | Cross-platform desktop notifications and in-browser alert banners |

---

## 🏗️ System Architecture & Core Concepts

### 1. Differential Rate Calculation (Disk & Network I/O)
Because operating system counters (`psutil.net_io_counters()` and `psutil.disk_io_counters()`) return cumulative bytes transferred since system boot, **SysPulse Pro** caches the previous poll state in memory and calculates real-time throughput across each polling interval ($\Delta t$):

$$\text{Throughput (KB/s)} = \frac{\text{Bytes}_{\text{current}} - \text{Bytes}_{\text{previous}}}{1024 \times (t_{\text{current}} - t_{\text{previous}})}$$

### 2. Database Schema (`system_monitor.db`)
The application automatically initializes three SQLite tables on first launch:
1. **`users`**: Stores `id`, `username` (UNIQUE), `password_hash` (SHA-256 hex digest), `role`, and `created_at`.
2. **`metrics_history`**: Stores rolling time-series snapshots (`cpu_percent`, `ram_percent`, `disk_read_mb`, `disk_write_mb`, `net_sent_kb`, `net_recv_kb`). Includes an automated pruning query (`LIMIT 500`) to maintain $O(1)$ storage overhead.
3. **`anomaly_logs`**: Persistent audit log storing `timestamp`, `metric_type`, `measured_value`, `threshold_value`, `severity`, and `message`.

---

## 🚀 Installation & Running Locally

### Prerequisites
* Python 3.9 or higher installed on your machine.

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR-USERNAME/syspulse-pro.git](https://github.com/YOUR-USERNAME/syspulse-pro.git)
cd syspulse-pro
