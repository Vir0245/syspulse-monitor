import os
import sys
import subprocess

# ==========================================
# 0. AUTO-BROWSER LAUNCHER (No Terminal Commands Needed)
# ==========================================
# If you click "Run" in VS Code/PyCharm (python app.py), this block automatically
# starts the web server, skips the terminal email prompt, and opens your browser.
if __name__ == "__main__" and os.environ.get("SYSPULSE_WEB_ACTIVE") != "1":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
    except Exception:
        ctx = None

    if ctx is None:
        os.environ["SYSPULSE_WEB_ACTIVE"] = "1"
        print("🌐 Starting SysPulse Pro Web Server... Opening in your browser!")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__),
            "--browser.gatherUsageStats=false"
        ])
        sys.exit(0)

import sqlite3
import time
import threading
import hashlib
import platform
from datetime import datetime
import psutil
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Safe import for OS desktop notifications
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except Exception:
    PLYER_AVAILABLE = False

# ==========================================
# 1. PAGE CONFIGURATION & WEBSITE STYLING
# ==========================================
st.set_page_config(
    page_title="SysPulse Pro | Web Login & Telemetry Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "system_monitor.db"

def inject_site_css(is_logged_in: bool):
    """Injects custom CSS for the website layout and hides sidebar on the login page."""
    hide_sidebar_css = "" if is_logged_in else """
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
    """
    st.markdown(f"""
    <style>
        {hide_sidebar_css}
        
        /* Hide default Streamlit top menu for a clean website feel */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}

        /* Main Website Background */
        .stApp {{
            background: radial-gradient(circle at 20% 10%, #0f172a 0%, #020617 75%);
            color: #f8fafc;
        }}

        /* Top Website Navigation Bar */
        .site-navbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 14px;
            padding: 14px 24px;
            margin-bottom: 20px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
        }}
        .brand-logo {{
            font-size: 1.5rem;
            font-weight: 800;
            background: linear-gradient(90deg, #00f2fe 0%, #4facfe 50%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .nav-badge {{
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.35);
            color: #38bdf8;
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 600;
        }}

        /* Website Login Card */
        .login-card-header {{
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.85), rgba(15, 23, 42, 0.95));
            border: 1px solid rgba(56, 189, 248, 0.35);
            border-top: 4px solid #00f2fe;
            border-radius: 16px;
            padding: 28px 24px 18px 24px;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
            margin-bottom: 16px;
        }}

        /* Glassmorphism Metric Cards */
        div[data-testid="stMetric"] {{
            background: rgba(30, 41, 59, 0.55);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-top: 3px solid #38bdf8;
            border-radius: 14px;
            padding: 16px 20px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-4px);
            box-shadow: 0 12px 28px 0 rgba(56, 189, 248, 0.22);
            border-color: rgba(56, 189, 248, 0.6);
        }}

        /* Hardware Spec Bar */
        .spec-banner {{
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            background: rgba(15, 23, 42, 0.75);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 12px;
            padding: 10px 18px;
            margin-bottom: 18px;
            font-size: 0.88rem;
            color: #cbd5e1;
        }}

        /* Pulsing Green Live Dot */
        .live-dot {{
            height: 10px;
            width: 10px;
            background-color: #10b981;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
            box-shadow: 0 0 10px #10b981;
            animation: pulse 1.5s infinite;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
            70% {{ transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }}
            100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
        }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE & AUTHENTICATION (SQLite3)
# ==========================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Users Table for Web Authentication
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'Student Admin',
            created_at TEXT
        )
    """)
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_users = [
            ("admin", hash_password("admin123"), "System Administrator", now_str),
            ("student", hash_password("college2026"), "Class Presenter", now_str)
        ]
        cursor.executemany(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            default_users
        )

    # Hardware Telemetry Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            cpu_percent REAL,
            ram_percent REAL,
            disk_read_mb REAL,
            disk_write_mb REAL,
            net_sent_kb REAL,
            net_recv_kb REAL
        )
    """)
    
    # Anomaly Audit Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            metric_type TEXT,
            measured_value REAL,
            threshold_value REAL,
            severity TEXT,
            message TEXT
        )
    """)
    conn.commit()
    conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, role FROM users WHERE username = ? AND password_hash = ?",
        (username.strip(), hash_password(password))
    )
    row = cursor.fetchone()
    conn.close()
    return row

def register_user(username, password, role="Student Admin"):
    if not username.strip() or not password.strip():
        return False, "Please enter both a username and a password."
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username.strip(), hash_password(password), role, datetime.now().strftime("%Y-%m-%d %H:%M"))
        )
        conn.commit()
        conn.close()
        return True, "Account created! Switch to the 'Sign In' tab to log in."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "That username is already taken. Please choose another."

def log_metrics_to_db(ts, cpu, ram, d_read, d_write, n_sent, n_recv):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO metrics_history 
        (timestamp, cpu_percent, ram_percent, disk_read_mb, disk_write_mb, net_sent_kb, net_recv_kb)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ts, cpu, ram, d_read, d_write, n_sent, n_recv))
    
    cursor.execute("""
        DELETE FROM metrics_history 
        WHERE id NOT IN (SELECT id FROM metrics_history ORDER BY id DESC LIMIT 500)
    """)
    conn.commit()
    conn.close()

def log_anomaly_to_db(ts, metric_type, value, threshold, severity, message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO anomaly_logs (timestamp, metric_type, measured_value, threshold_value, severity, message)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ts, metric_type, round(value, 2), threshold, severity, message))
    conn.commit()
    conn.close()

def get_recent_metrics(limit=35):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(f"SELECT * FROM metrics_history ORDER BY id DESC LIMIT {limit}", conn)
    conn.close()
    return df.iloc[::-1]

def get_anomaly_logs(limit=25):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(f"SELECT * FROM anomaly_logs ORDER BY id DESC LIMIT {limit}", conn)
    conn.close()
    return df

def clear_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM metrics_history")
    cursor.execute("DELETE FROM anomaly_logs")
    conn.commit()
    conn.close()

# ==========================================
# 3. ALERTS & MULTI-THREADED STRESS ENGINE
# ==========================================
def trigger_alert(title, message):
    st.toast(f"🚨 **{title}**: {message}", icon="⚠️")
    if PLYER_AVAILABLE and st.session_state.get("enable_desktop_notif", True):
        try:
            notification.notify(
                title=f"SysPulse Alert: {title}",
                message=message,
                app_name="SysPulse Pro",
                timeout=4
            )
        except Exception:
            pass

def cpu_stress_worker(duration_sec=8):
    end_time = time.time() + duration_sec
    while time.time() < end_time:
        _ = [x ** 2 for x in range(12000)]

def start_cpu_stress_test(threads=6, duration=8):
    for _ in range(threads):
        t = threading.Thread(target=cpu_stress_worker, args=(duration,), daemon=True)
        t.start()

# ==========================================
# 4. HARDWARE POLLING & GAUGES
# ==========================================
def poll_system_metrics():
    now_str = datetime.now().strftime("%H:%M:%S")
    current_time = time.time()
    
    cpu_pct = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    ram_pct = ram.percent
    
    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()
    
    if "prev_net" not in st.session_state:
        st.session_state.prev_net = net_io
        st.session_state.prev_disk = disk_io
        st.session_state.prev_time = current_time
        d_read_mb, d_write_mb, n_sent_kb, n_recv_kb = 0.0, 0.0, 0.0, 0.0
    else:
        dt = max(current_time - st.session_state.prev_time, 0.5)
        d_read_mb = ((disk_io.read_bytes - st.session_state.prev_disk.read_bytes) / (1024 * 1024)) / dt
        d_write_mb = ((disk_io.write_bytes - st.session_state.prev_disk.write_bytes) / (1024 * 1024)) / dt
        n_sent_kb = ((net_io.bytes_sent - st.session_state.prev_net.bytes_sent) / 1024) / dt
        n_recv_kb = ((net_io.bytes_recv - st.session_state.prev_net.bytes_recv) / 1024) / dt
        
        st.session_state.prev_net = net_io
        st.session_state.prev_disk = disk_io
        st.session_state.prev_time = current_time

    boot_ts = psutil.boot_time()
    uptime_hours = round((current_time - boot_ts) / 3600, 1)

    return {
        "timestamp": now_str,
        "cpu": cpu_pct,
        "ram": ram_pct,
        "ram_used_gb": round(ram.used / (1024**3), 2),
        "ram_total_gb": round(ram.total / (1024**3), 2),
        "disk_read_mb": max(round(d_read_mb, 2), 0.0),
        "disk_write_mb": max(round(d_write_mb, 2), 0.0),
        "net_sent_kb": max(round(n_sent_kb, 2), 0.0),
        "net_recv_kb": max(round(n_recv_kb, 2), 0.0),
        "uptime_hours": uptime_hours
    }

def create_gauge_chart(value, title, threshold, color="#38bdf8"):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%", "font": {"size": 28, "color": "#f8fafc"}},
        title={"text": title, "font": {"size": 15, "color": "#94a3b8"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#475569"},
            "bar": {"color": "#ef4444" if value >= threshold else color},
            "bgcolor": "rgba(15, 23, 42, 0.6)",
            "borderwidth": 1,
            "bordercolor": "#334155",
            "steps": [
                {"range": [0, threshold], "color": "rgba(56, 189, 248, 0.08)"},
                {"range": [threshold, 100], "color": "rgba(239, 68, 68, 0.18)"}
            ],
            "threshold": {
                "line": {"color": "#f97316", "width": 3},
                "thickness": 0.8,
                "value": threshold
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=210,
        margin=dict(l=20, r=20, t=40, b=10)
    )
    return fig

# ==========================================
# 5. FULL-PAGE WEBSITE LOGIN PORTAL
# ==========================================
def render_web_login_portal():
    """Renders a full-screen website authentication page right inside the browser."""
    # Top Website Header Bar
    st.markdown("""
    <div class="site-navbar">
        <div class="brand-logo">🛡️ SysPulse Pro</div>
        <div class="nav-badge">🔒 Authentication Required</div>
    </div>
    """, unsafe_allow_html=True)

    _, center_col, _ = st.columns([1, 1.35, 1])

    with center_col:
        st.markdown("""
        <div class="login-card-header">
            <div style="font-size: 3rem; margin-bottom: 6px;">🌐</div>
            <div class="brand-logo" style="font-size: 2rem;">Web Security Portal</div>
            <p style="color: #94a3b8; font-size: 0.92rem; margin-top: 6px;">
                Sign in on this page to access real-time network &amp; system telemetry.
            </p>
        </div>
        """, unsafe_allow_html=True)

        tab_signin, tab_signup = st.tabs(["🔑 Sign In to Dashboard", "📝 Create New Account"])

        with tab_signin:
            with st.form("web_login_form", clear_on_submit=False):
                username = st.text_input("Username", value="admin", placeholder="Enter username")
                password = st.text_input("Password", value="admin123", type="password", placeholder="Enter password")
                login_submitted = st.form_submit_button("🚀 Sign In to Web Dashboard", use_container_width=True, type="primary")

                if login_submitted:
                    user = verify_user(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.username = user[0]
                        st.session_state.user_role = user[1]
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password. Try `admin` / `admin123`.")

            st.markdown("""
            <div style="background: rgba(15, 23, 42, 0.7); border: 1px dashed rgba(56, 189, 248, 0.35); border-radius: 10px; padding: 12px 16px; margin-top: 10px; font-size: 0.85rem; color: #cbd5e1;">
                🎓 <b>Pre-Loaded Demo Accounts (Already filled in above!):</b><br>
                • Admin Account: <code>admin</code> / <code>admin123</code><br>
                • Student Account: <code>student</code> / <code>college2026</code>
            </div>
            """, unsafe_allow_html=True)

        with tab_signup:
            with st.form("web_signup_form", clear_on_submit=True):
                new_user = st.text_input("Choose a Username", placeholder="e.g., rahul_cs")
                new_pass = st.text_input("Choose a Password", type="password", placeholder="Create a strong password")
                new_role = st.selectbox("Select Your Role", ["Student Admin", "Network Analyst", "Lab Researcher"])
                signup_submitted = st.form_submit_button("✨ Create Account on Site", use_container_width=True)

                if signup_submitted:
                    ok, msg = register_user(new_user, new_pass, new_role)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

# ==========================================
# 6. INITIALIZE SESSION & ROUTE WEB PAGE
# ==========================================
init_db()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = 0

inject_site_css(st.session_state.authenticated)

# Show the Full-Page Web Login Portal if not signed in
if not st.session_state.authenticated:
    render_web_login_portal()
    st.stop()

# ==========================================
# 7. AUTHENTICATED WEBSITE DASHBOARD
# ==========================================
# Top Website Navigation Bar with User Badge & Log Out Button on the Page
nav_col1, nav_col2 = st.columns([4.5, 1])
with nav_col1:
    st.markdown(f"""
    <div class="site-navbar" style="margin-bottom: 10px;">
        <div class="brand-logo">⚡ SysPulse Pro | Live System &amp; Network Monitor</div>
        <div class="nav-badge">👤 {st.session_state.username} ({st.session_state.user_role})</div>
    </div>
    """, unsafe_allow_html=True)
with nav_col2:
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    if st.button("🔒 Log Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# Sidebar Controls
with st.sidebar:
    st.title("🎛️ Control Center")
    live_monitoring = st.toggle("🟢 Live Auto-Refresh", value=True)
    refresh_rate = st.slider("Polling Interval (sec)", 1, 5, 1)

    st.divider()
    st.subheader("🚨 Breach Thresholds")
    cpu_thresh = st.slider("CPU Alert Limit (%)", 10, 100, 75)
    ram_thresh = st.slider("RAM Alert Limit (%)", 10, 100, 85)
    net_thresh = st.slider("Network Alert Limit (KB/s)", 50, 5000, 1000)

    st.session_state.enable_desktop_notif = st.checkbox("OS Desktop Notifications (Plyer)", value=True)
    alert_cooldown = st.number_input("Notification Cooldown (sec)", 5, 60, 10)

    st.divider()
    st.subheader("🎓 Class Presentation Demo")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("🔥 Stress CPU", use_container_width=True):
            start_cpu_stress_test(threads=6, duration=8)
            st.toast("Spawning 6 worker threads for 8 seconds!", icon="🔥")
    with col_s2:
        if st.button("⚡ Fake Spike", use_container_width=True):
            now_s = datetime.now().strftime("%H:%M:%S")
            log_anomaly_to_db(now_s, "CPU (Simulated)", 97.2, cpu_thresh, "CRITICAL", f"Triggered by {st.session_state.username}")
            trigger_alert("CRITICAL CPU Spike", f"CPU reached 97.2% (Limit: {cpu_thresh}%)")

    if st.button("🗑️ Clear SQLite History", use_container_width=True):
        clear_database()
        st.toast("Telemetry & Anomaly logs cleared!", icon="🧹")

# Poll Metrics & Log to SQLite
current = poll_system_metrics()
log_metrics_to_db(
    current["timestamp"], current["cpu"], current["ram"],
    current["disk_read_mb"], current["disk_write_mb"],
    current["net_sent_kb"], current["net_recv_kb"]
)

os_info = f"{platform.system()} {platform.release()}"
cores_physical = psutil.cpu_count(logical=False) or 1
cores_logical = psutil.cpu_count(logical=True) or 1

st.markdown(f"""
<div class="spec-banner">
    <div><span class="live-dot"></span><b>LIVE STREAM ACTIVE</b></div>
    <div>🖥️ <b>OS:</b> {os_info}</div>
    <div>⚙️ <b>CPU Cores:</b> {cores_physical} Physical / {cores_logical} Logical</div>
    <div>⏱️ <b>System Uptime:</b> {current['uptime_hours']} hrs</div>
    <div>🗄️ <b>Database:</b> SQLite3 (SHA-256 Web Auth)</div>
</div>
""", unsafe_allow_html=True)

# Check Thresholds & Fire Alerts
now_epoch = time.time()
if current["cpu"] >= cpu_thresh:
    msg = f"CPU at {current['cpu']}% breached {cpu_thresh}% limit"
    log_anomaly_to_db(current["timestamp"], "CPU", current["cpu"], cpu_thresh, "CRITICAL", msg)
    if now_epoch - st.session_state.last_alert_time > alert_cooldown:
        trigger_alert("High CPU Usage", msg)
        st.session_state.last_alert_time = now_epoch

if current["ram"] >= ram_thresh:
    msg = f"RAM at {current['ram']}% breached {ram_thresh}% limit"
    log_anomaly_to_db(current["timestamp"], "RAM", current["ram"], ram_thresh, "HIGH", msg)
    if now_epoch - st.session_state.last_alert_time > alert_cooldown:
        trigger_alert("High Memory Usage", msg)
        st.session_state.last_alert_time = now_epoch

total_net_kb = current["net_sent_kb"] + current["net_recv_kb"]
if total_net_kb >= net_thresh:
    msg = f"Network traffic ({total_net_kb:.1f} KB/s) exceeded {net_thresh} KB/s"
    log_anomaly_to_db(current["timestamp"], "NETWORK", total_net_kb, net_thresh, "WARNING", msg)
    if now_epoch - st.session_state.last_alert_time > alert_cooldown:
        trigger_alert("Network Traffic Spike", msg)
        st.session_state.last_alert_time = now_epoch

# --- TOP KPI METRIC CARDS ---
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric(
        "💻 CPU Load",
        f"{current['cpu']}%",
        delta="BREACH!" if current["cpu"] >= cpu_thresh else "Optimal",
        delta_color="inverse" if current["cpu"] >= cpu_thresh else "normal"
    )
with kpi2:
    st.metric(
        "🧠 RAM Allocation",
        f"{current['ram']}%",
        delta=f"{current['ram_used_gb']} / {current['ram_total_gb']} GB",
        delta_color="off"
    )
with kpi3:
    st.metric(
        "🌐 Network (Down / Up)",
        f"↓ {current['net_recv_kb']} KB/s",
        delta=f"↑ {current['net_sent_kb']} KB/s",
        delta_color="off"
    )
with kpi4:
    st.metric(
        "💽 Disk I/O (Read / Write)",
        f"R: {current['disk_read_mb']} MB/s",
        delta=f"W: {current['disk_write_mb']} MB/s",
        delta_color="off"
    )

# --- RADIAL GAUGES + LIVE NEON CHARTS ---
history_df = get_recent_metrics(limit=35)

gauge_col1, gauge_col2, chart_col = st.columns([1, 1, 2.2])

with gauge_col1:
    st.plotly_chart(
        create_gauge_chart(current["cpu"], "CPU Speedometer", cpu_thresh, "#00f2fe"),
        use_container_width=True
    )

with gauge_col2:
    st.plotly_chart(
        create_gauge_chart(current["ram"], "RAM Speedometer", ram_thresh, "#a855f7"),
        use_container_width=True
    )

with chart_col:
    fig_sys = go.Figure()
    fig_sys.add_trace(go.Scatter(
        x=history_df["timestamp"], y=history_df["cpu_percent"],
        mode="lines", fill="tozeroy", name="CPU %",
        line=dict(color="#00f2fe", width=2.5),
        fillcolor="rgba(0, 242, 254, 0.12)"
    ))
    fig_sys.add_trace(go.Scatter(
        x=history_df["timestamp"], y=history_df["ram_percent"],
        mode="lines", name="RAM %",
        line=dict(color="#a855f7", width=2.5)
    ))
    fig_sys.add_hline(y=cpu_thresh, line_dash="dot", line_color="#f97316", annotation_text="CPU Limit")
    fig_sys.update_layout(
        title=dict(text="📈 Real-Time CPU & Memory Telemetry", font=dict(size=15, color="#e2e8f0")),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.5)",
        height=225,
        margin=dict(l=10, r=10, t=35, b=10),
        yaxis=dict(range=[0, 105]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_sys, use_container_width=True)

# --- NETWORK & DISK CHARTS ---
net_col, disk_col = st.columns(2)

with net_col:
    fig_net = go.Figure()
    fig_net.add_trace(go.Scatter(
        x=history_df["timestamp"], y=history_df["net_recv_kb"],
        mode="lines", fill="tozeroy", name="Download (KB/s)",
        line=dict(color="#10b981", width=2),
        fillcolor="rgba(16, 185, 129, 0.15)"
    ))
    fig_net.add_trace(go.Scatter(
        x=history_df["timestamp"], y=history_df["net_sent_kb"],
        mode="lines", name="Upload (KB/s)",
        line=dict(color="#f43f5e", width=2)
    ))
    fig_net.update_layout(
        title=dict(text="🌐 Live Network Packet Throughput (KB/s)", font=dict(size=15, color="#e2e8f0")),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.5)",
        height=250,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_net, use_container_width=True)

with disk_col:
    fig_disk = go.Figure()
    fig_disk.add_trace(go.Bar(
        x=history_df["timestamp"], y=history_df["disk_read_mb"],
        name="Disk Read (MB/s)", marker_color="#38bdf8"
    ))
    fig_disk.add_trace(go.Bar(
        x=history_df["timestamp"], y=history_df["disk_write_mb"],
        name="Disk Write (MB/s)", marker_color="#f59e0b"
    ))
    fig_disk.update_layout(
        title=dict(text="💽 Disk I/O Read/Write Activity (MB/s)", font=dict(size=15, color="#e2e8f0")),
        barmode="group",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.5)",
        height=250,
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_disk, use_container_width=True)

# --- BOTTOM TABS: ANOMALIES & PROCESSES ---
tab1, tab2 = st.tabs(["🚨 SQLite Anomaly & Breach Audit Log", "⚙️ Active OS Process Inspector"])

with tab1:
    anomalies_df = get_anomaly_logs(limit=25)
    if anomalies_df.empty:
        st.info("No threshold breaches recorded yet. Click **'🔥 Stress CPU'** or **'⚡ Fake Spike'** in the sidebar!")
    else:
        st.dataframe(anomalies_df, use_container_width=True, hide_index=True)
        csv_data = anomalies_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Export Audit Logs to CSV",
            data=csv_data,
            file_name="syspulse_anomaly_audit.csv",
            mime="text/csv"
        )

with tab2:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    proc_df = pd.DataFrame(procs)
    if not proc_df.empty:
        proc_df = proc_df.sort_values(by="memory_percent", ascending=False).head(10)
        proc_df["memory_percent"] = proc_df["memory_percent"].round(2)
        st.dataframe(proc_df, use_container_width=True, hide_index=True)

# Auto-refresh loop
if live_monitoring:
    time.sleep(refresh_rate)
    st.rerun()