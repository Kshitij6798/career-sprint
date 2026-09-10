import os
import json
import datetime
import streamlit as st
import pandas as pd
import requests
from dotenv import load_dotenv
from google import genai
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()

st.set_page_config(page_title="Career Sprint — Mission Control", page_icon="🎯", layout="wide")

# =========================================================
# STYLE
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

:root {
    --bg: #10141A;
    --surface: #1B212A;
    --surface-2: #212934;
    --border: #2C3540;
    --text: #EDEFF2;
    --text-muted: #8992A0;
    --accent: #5B9BD5;
    --critical: #E2574C;
    --warning: #E0A83D;
    --positive: #4FAE7E;
    --muted-tile: #4A5561;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background-color: var(--bg); color: var(--text); }
section[data-testid="stSidebar"] { background-color: var(--surface); border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] .stRadio label { font-size: 0.95rem; }

h1, h2, h3 { font-family: 'Inter', sans-serif; font-weight: 600; letter-spacing: -0.01em; }

.stButton>button {
    border-radius: 6px;
    border: 1px solid var(--border);
    background-color: var(--surface-2);
    color: var(--text);
    font-weight: 500;
}
.stButton>button:hover { border-color: var(--accent); color: var(--accent); }
.stButton>button[kind="primary"] { background-color: var(--accent); border-color: var(--accent); color: #0B0E12; }

.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"], .stDateInput input {
    background-color: var(--surface-2) !important;
    color: var(--text) !important;
    border-color: var(--border) !important;
    border-radius: 6px !important;
}

/* Countdown strip */
.countdown-row { display: flex; gap: 14px; flex-wrap: wrap; margin: 6px 0 22px 0; }
.tile {
    flex: 1 1 200px;
    background-color: var(--surface);
    border: 1px solid var(--border);
    border-left: 4px solid var(--muted-tile);
    border-radius: 8px;
    padding: 14px 16px;
}
.tile-critical { border-left-color: var(--critical); }
.tile-warning { border-left-color: var(--warning); }
.tile-neutral { border-left-color: var(--accent); }
.tile-passed { border-left-color: var(--muted-tile); opacity: 0.6; }
.tile-days { font-family: 'JetBrains Mono', monospace; font-size: 1.9rem; font-weight: 700; line-height: 1; }
.tile-label { color: var(--text-muted); font-size: 0.85rem; margin-top: 6px; }
.tile-date { color: var(--text-muted); font-size: 0.78rem; margin-top: 2px; }

/* Status badges */
.badge-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.badge {
    background-color: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 5px 14px;
    font-size: 0.85rem;
    color: var(--text);
}
.badge b { font-family: 'JetBrains Mono', monospace; }

/* Job feed cards */
.job-card {
    background-color: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
}
.job-title { font-weight: 600; font-size: 1.02rem; }
.job-meta { color: var(--text-muted); font-size: 0.85rem; margin: 2px 0 8px 0; }
.job-desc { color: var(--text); font-size: 0.88rem; }

.section-caption { color: var(--text-muted); margin-bottom: 18px; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR — nav + settings + connection status
# =========================================================
with st.sidebar:
    st.markdown("## 🎯 Career Sprint")
    section = st.radio(
        "Navigate",
        ["Dashboard", "Daily Timetable", "Job Tracker", "Job Feed", "Interview Prep"],
        label_visibility="collapsed",
        key="nav_section",
    )
    st.divider()

    with st.expander("⚙️ API keys"):
        gemini_key = st.text_input("Gemini API key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
        adzuna_id = st.text_input("Adzuna App ID", value=os.getenv("ADZUNA_APP_ID", ""))
        adzuna_key = st.text_input("Adzuna App Key", value=os.getenv("ADZUNA_APP_KEY", ""), type="password")
        st.caption("Stored for this session only. Put them in a .env file so you don't retype them — see README.")

    with st.expander("📅 Key dates"):
        if "project_end" not in st.session_state:
            st.session_state["project_end"] = datetime.date(2026, 9, 30)
        st.session_state["project_end"] = st.date_input("Project / contract end date", value=st.session_state["project_end"])
        st.caption("Edit this if the timeline changes. The grace-period math below updates automatically.")

# =========================================================
# CONNECTIONS
# =========================================================
@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key):
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

@st.cache_resource(show_spinner=False)
def get_db():
    try:
        if not firebase_admin._apps:
            if "FIREBASE_KEY_JSON" in os.environ:
                key_dict = json.loads(os.environ["FIREBASE_KEY_JSON"])
                cred = credentials.Certificate(key_dict)
            else:
                cred = credentials.Certificate(os.getenv("FIREBASE_KEY_PATH", "firebase-key.json"))
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception:
        return None

client = get_gemini_client(gemini_key)
db = get_db()

with st.sidebar:
    st.divider()
    st.caption("🟢 Gemini connected" if client else "⚪ Gemini not configured")
    st.caption("🟢 Firebase connected" if db else "⚪ Firebase not configured — data won't be saved")

# =========================================================
# COUNTDOWN STRIP (always visible)
# =========================================================
today = datetime.date.today()
project_end = st.session_state["project_end"]
grace_start = project_end + datetime.timedelta(days=1)
day45 = grace_start + datetime.timedelta(days=44)
day60 = grace_start + datetime.timedelta(days=59)

def days_until(d):
    return (d - today).days

def urgency_class(days):
    if days < 0:
        return "tile-passed"
    if days <= 7:
        return "tile-critical"
    if days <= 21:
        return "tile-warning"
    return "tile-neutral"

tiles = [
    ("Project ends", project_end),
    ("Grace period starts", grace_start),
    ("Day 45 — B-2 filing cutoff", day45),
    ("Day 60 — status must resolve", day60),
]
tile_html = '<div class="countdown-row">'
for label, d in tiles:
    days = days_until(d)
    cls = urgency_class(days)
    day_text = f"{days}d" if days >= 0 else "passed"
    tile_html += f'<div class="tile {cls}"><div class="tile-days">{day_text}</div><div class="tile-label">{label}</div><div class="tile-date">{d.strftime("%b %d, %Y")}</div></div>'
tile_html += '</div>'
st.markdown(tile_html, unsafe_allow_html=True)

# =========================================================
# HELPERS
# =========================================================
DEFAULT_WEEKDAY_TASKS = [
    {"id": "t1", "start": "06:30", "end": "08:30", "title": "DSA / Grind 75", "desc": "1 easy warm-up + 1 medium problem, high-frequency patterns only."},
    {"id": "t2", "start": "12:00", "end": "13:00", "title": "Job applications", "desc": "5–10 targeted applications, tailored to each posting."},
    {"id": "t3", "start": "18:30", "end": "19:30", "title": "Resume defense", "desc": "Talk out loud through the LangGraph / agentic project until fluent."},
    {"id": "t4", "start": "19:30", "end": "20:30", "title": "System design study", "desc": "RAG architecture, vector DB trade-offs, production LLM concerns."},
]

DEFAULT_WEEKEND_TASKS = [
    {"id": "w1", "start": "09:00", "end": "12:00", "title": "Timed mock interviews", "desc": "2–3 medium LeetCode problems back-to-back, under a timer."},
    {"id": "w2", "start": "13:00", "end": "15:00", "title": "Build something", "desc": "Small AI side project (FastAPI + LangGraph) to keep coding reflexes sharp."},
    {"id": "w3", "start": "18:00", "end": "20:00", "title": "Rest", "desc": "No prep. Burnout before a layoff is worse than a skipped session."},
]

def is_weekend(d):
    return d.weekday() >= 5

def get_task_templates():
    default = {"weekday": DEFAULT_WEEKDAY_TASKS, "weekend": DEFAULT_WEEKEND_TASKS}
    if db:
        try:
            doc = db.collection("config").document("task_template").get()
            if doc.exists:
                data = doc.to_dict()
                if data.get("weekday") and data.get("weekend"):
                    return data
        except Exception:
            pass
    return default

def save_task_templates(templates):
    if db:
        try:
            db.collection("config").document("task_template").set(templates)
        except Exception:
            pass

def get_tasks_for_date(templates, d):
    return templates["weekend"] if is_weekend(d) else templates["weekday"]

def time_to_minutes(t_str):
    h, m = map(int, t_str.split(":"))
    return h * 60 + m

def fmt_time(t_str):
    h, m = map(int, t_str.split(":"))
    period = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}:{m:02d} {period}"

def render_day_bar(tasks, completed_ids, is_today):
    if not tasks:
        return ""
    starts = [time_to_minutes(t["start"]) for t in tasks]
    ends = [time_to_minutes(t["end"]) for t in tasks]
    day_start = max(0, min(starts) - 30)
    day_end = min(24 * 60, max(ends) + 30)
    span = max(day_end - day_start, 1)

    segs = ""
    for t in tasks:
        s, e = time_to_minutes(t["start"]), time_to_minutes(t["end"])
        left = (s - day_start) / span * 100
        width = max((e - s) / span * 100, 1.5)
        done = t["id"] in completed_ids
        color = "var(--positive)" if done else "var(--accent)"
        opacity = "1" if done else "0.5"
        segs += f'<div title="{t["title"]}" style="position:absolute; left:{left}%; width:{width}%; top:0; bottom:0; background-color:{color}; opacity:{opacity}; border-radius:4px;"></div>'

    now_marker = ""
    if is_today:
        now = datetime.datetime.now()
        now_min = now.hour * 60 + now.minute
        if day_start <= now_min <= day_end:
            left = (now_min - day_start) / span * 100
            now_marker = (
                f'<div style="position:absolute; left:{left}%; top:-8px; bottom:-8px; width:2px; background-color:#FF6B6B; z-index:3;"></div>'
                f'<div style="position:absolute; left:{left}%; top:-24px; transform:translateX(-50%); font-size:0.7rem; color:#FF6B6B; font-weight:600; white-space:nowrap;">now</div>'
            )

    start_label = fmt_time(f"{day_start // 60:02d}:{day_start % 60:02d}")
    end_label = fmt_time(f"{day_end // 60:02d}:{day_end % 60:02d}")

    bar_inner = f'<div style="position:relative;height:100%;background-color:var(--surface-2);border-radius:6px;border:1px solid var(--border);">{segs}</div>'
    labels = f'<div style="display:flex;justify-content:space-between;font-size:0.72rem;color:var(--text-muted);margin-top:4px;"><span>{start_label}</span><span>{end_label}</span></div>'
    return f'<div style="position:relative;margin:30px 4px 6px 4px;height:26px;">{now_marker}{bar_inner}</div>{labels}'

def get_daily_progress(date_str):
    if db:
        try:
            doc = db.collection("daily_progress").document(date_str).get()
            if doc.exists:
                return set(doc.to_dict().get("completed", []))
        except Exception:
            pass
    return set()

def save_daily_progress(date_str, completed_set):
    if db:
        try:
            db.collection("daily_progress").document(date_str).set({"completed": list(completed_set)})
        except Exception:
            pass

PIPELINE_STATUSES = ["To Apply", "Applied", "Recruiter Screen", "Technical Screen", "Interviewing", "Offer", "Rejected"]
STATUS_COLORS = {
    "To Apply": "var(--text-muted)", "Applied": "var(--accent)", "Recruiter Screen": "var(--warning)",
    "Technical Screen": "var(--warning)", "Interviewing": "var(--warning)", "Offer": "var(--positive)",
    "Rejected": "var(--critical)",
}

def save_resume_to_db(resume_text):
    if db and resume_text:
        try:
            db.collection("config").document("current_resume").set({
                "text": resume_text,
                "updated_at": firestore.SERVER_TIMESTAMP,
            })
        except Exception:
            pass

def get_resume_from_db():
    if db:
        try:
            doc = db.collection("config").document("current_resume").get()
            if doc.exists:
                return doc.to_dict().get("text", "")
        except Exception:
            pass
    return ""

def get_pipeline():
    if not db:
        return []
    try:
        docs = db.collection("job_pipeline").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
        out = []
        for d in docs:
            item = d.to_dict()
            item["id"] = d.id
            out.append(item)
        return out
    except Exception:
        return []

def detect_sponsorship(text):
    """Scan job description for sponsorship keywords. Returns 'yes', 'no', or 'unclear'."""
    text_lower = (text or "").lower()
    
    positive = ["sponsor", "h-1b", "visa sponsor", "work authorization", "immigration support", "visa support", "employment authorization", "willing to sponsor"]
    negative = ["no sponsorship", "not sponsor", "us citizen", "us permanent resident", "no visa", "no h-1b"]
    
    has_positive = any(kw in text_lower for kw in positive)
    has_negative = any(kw in text_lower for kw in negative)
    
    if has_negative:
        return "no"
    if has_positive:
        return "yes"
    return "unclear"

def fetch_jobs(app_id, app_key, keywords, location, results=10):
    if not app_id or not app_key:
        return None, "missing_keys"
    try:
        url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
        params = {
            "app_id": app_id, "app_key": app_key, "results_per_page": results,
            "what": keywords, "content-type": "application/json",
        }
        if location:
            params["where"] = location
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if resp.status_code != 200 or "results" not in data:
            msg = data.get("exception") or data.get("display") or f"HTTP {resp.status_code} — check your App ID/Key"
            return None, msg
        return data.get("results", []), None
    except Exception as e:
        return None, str(e)

# =========================================================
# DASHBOARD
# =========================================================
if section == "Dashboard":
    st.title("Dashboard")
    st.markdown('<p class="section-caption">Today at a glance. The countdown above tracks the worst-case timeline — it doesn\'t mean termination is confirmed.</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    tasks = get_tasks_for_date(get_task_templates(), today)
    today_str = today.strftime("%Y-%m-%d")
    completed_today = get_daily_progress(today_str)
    with col1:
        pct = int(100 * len(completed_today) / len(tasks)) if tasks else 0
        st.metric("Today's study blocks done", f"{len(completed_today)}/{len(tasks)}", f"{pct}%")
    pipeline = get_pipeline()
    with col2:
        st.metric("Applications in pipeline", len(pipeline))
    with col3:
        upcoming = [p for p in pipeline if p.get("follow_up") and p["follow_up"] <= (today + datetime.timedelta(days=7)).strftime("%Y-%m-%d")]
        st.metric("Follow-ups due this week", len(upcoming))

    if pipeline:
        st.subheader("Pipeline by stage")
        counts = {}
        for p in pipeline:
            counts[p.get("status", "To Apply")] = counts.get(p.get("status", "To Apply"), 0) + 1
        badge_html = '<div class="badge-row">'
        for status in PIPELINE_STATUSES:
            if counts.get(status):
                badge_html += f'<div class="badge" style="border-left:3px solid {STATUS_COLORS[status]}"><b>{counts[status]}</b> &nbsp;{status}</div>'
        badge_html += '</div>'
        st.markdown(badge_html, unsafe_allow_html=True)
    else:
        st.info("No applications logged yet — head to Job Tracker to add your first one.")

# =========================================================
# DAILY TIMETABLE
# =========================================================
elif section == "Daily Timetable":
    st.title("Daily Timetable")
    st.markdown('<p class="section-caption">Weekdays and weekends run different routines. The bar below shows where you are in the day right now; the strip shows the week.</p>', unsafe_allow_html=True)

    if "tt_date" not in st.session_state:
        st.session_state["tt_date"] = today

    templates = get_task_templates()

    # --- Weekly streak strip ---
    week_start = st.session_state["tt_date"] - datetime.timedelta(days=st.session_state["tt_date"].weekday())
    week_dates = [week_start + datetime.timedelta(days=i) for i in range(7)]
    cols = st.columns(7)
    for i, wd in enumerate(week_dates):
        wd_str = wd.strftime("%Y-%m-%d")
        wd_tasks = get_tasks_for_date(templates, wd)
        wd_completed = get_daily_progress(wd_str)
        pct = int(100 * len(wd_completed) / len(wd_tasks)) if wd_tasks else 0
        dot = "🟢" if pct == 100 else ("🟡" if pct > 0 else "⚪")
        marker = "▸ " if wd == st.session_state["tt_date"] else ""
        with cols[i]:
            if st.button(f"{marker}{dot} {wd.strftime('%a')}", key=f"streak_{wd_str}", use_container_width=True, help=f"{pct}% complete"):
                st.session_state["tt_date"] = wd
                st.rerun()
            st.caption(("Today · " if wd == today else "") + f"{pct}%")

    st.write("")
    st.date_input("Jump to a date", value=st.session_state["tt_date"], key="tt_date")

    selected_dt = st.session_state["tt_date"]
    date_str = selected_dt.strftime("%Y-%m-%d")
    is_weekend_day = is_weekend(selected_dt)
    is_today_flag = selected_dt == today
    is_past_day = selected_dt < today
    tasks = get_tasks_for_date(templates, selected_dt)
    completed = get_daily_progress(date_str)

    st.caption("Weekend routine" if is_weekend_day else "Weekday routine")
    st.markdown(render_day_bar(tasks, completed, is_today_flag), unsafe_allow_html=True)

    now_min = None
    if is_today_flag:
        now = datetime.datetime.now()
        now_min = now.hour * 60 + now.minute

    new_completed = set()
    for t in tasks:
        is_done = t["id"] in completed
        if is_done:
            status_dot = "🟢"
        elif is_past_day:
            status_dot = "🔴"
        elif is_today_flag:
            s, e = time_to_minutes(t["start"]), time_to_minutes(t["end"])
            if s <= now_min < e:
                status_dot = "🔵"
            elif now_min >= e:
                status_dot = "🔴"
            else:
                status_dot = "⚪"
        else:
            status_dot = "⚪"

        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(f"{status_dot} **{fmt_time(t['start'])} – {fmt_time(t['end'])} — {t['title']}**")
            st.caption(t["desc"])
        with c2:
            checked = st.checkbox("Done", value=is_done, key=f"chk_{date_str}_{t['id']}")
        if checked:
            new_completed.add(t["id"])
        st.write("")

    if new_completed != completed:
        save_daily_progress(date_str, new_completed)

    progress = len(new_completed) / len(tasks) if tasks else 0
    st.progress(progress)
    st.caption(f"{len(new_completed)}/{len(tasks)} blocks complete for {date_str}")
    st.caption("🟢 done · 🔵 happening now · 🔴 missed · ⚪ upcoming")

    with st.expander(f"✏️ Edit {'weekend' if is_weekend_day else 'weekday'} routine"):
        with st.form("add_task_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_start = st.time_input("Start", value=datetime.time(9, 0))
            with c2:
                new_end = st.time_input("End", value=datetime.time(10, 0))
            with c3:
                new_title = st.text_input("Block title")
            new_desc = st.text_area("What happens in this block", height=70)
            if st.form_submit_button("Add block") and new_title:
                key = "weekend" if is_weekend_day else "weekday"
                templates[key].append({
                    "id": f"t{len(templates[key])+1}_{int(datetime.datetime.now().timestamp())}",
                    "start": new_start.strftime("%H:%M"), "end": new_end.strftime("%H:%M"),
                    "title": new_title, "desc": new_desc,
                })
                save_task_templates(templates)
                st.rerun()

        if tasks:
            remove_title = st.selectbox("Remove a block", [t["title"] for t in tasks])
            if st.button("Remove selected block", key="remove_task_block_btn"):
                key = "weekend" if is_weekend_day else "weekday"
                templates[key] = [t for t in templates[key] if t["title"] != remove_title]
                save_task_templates(templates)
                st.rerun()

# =========================================================
# JOB TRACKER
# =========================================================
elif section == "Job Tracker":
    st.title("Job Tracker")
    st.markdown('<p class="section-caption">Every application, its stage, and whether the company has said anything about H-1B sponsorship.</p>', unsafe_allow_html=True)

    with st.expander("➕ Add application", expanded=False):
        with st.form("add_app_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                company = st.text_input("Company")
                role = st.text_input("Role")
                url = st.text_input("Posting link")
            with c2:
                status = st.selectbox("Stage", PIPELINE_STATUSES)
                sponsorship = st.selectbox("H-1B sponsorship", ["Unknown / to ask", "Confirmed yes", "Confirmed no"])
                follow_up = st.date_input("Follow-up date", value=today + datetime.timedelta(days=5))
            notes = st.text_area("Notes", height=70)
            if st.form_submit_button("Save") and company and role:
                if db:
                    db.collection("job_pipeline").add({
                        "company": company, "role": role, "url": url, "status": status,
                        "sponsorship": sponsorship, "follow_up": follow_up.strftime("%Y-%m-%d"),
                        "notes": notes, "created_at": firestore.SERVER_TIMESTAMP,
                    })
                    st.rerun()
                else:
                    st.warning("Firebase isn't connected, so this can't be saved. See README to set it up.")

    pipeline = get_pipeline()
    if pipeline:
        counts = {}
        for p in pipeline:
            counts[p.get("status", "To Apply")] = counts.get(p.get("status", "To Apply"), 0) + 1
        badge_html = '<div class="badge-row">'
        for status in PIPELINE_STATUSES:
            if counts.get(status):
                badge_html += f'<div class="badge" style="border-left:3px solid {STATUS_COLORS[status]}"><b>{counts[status]}</b> &nbsp;{status}</div>'
        badge_html += '</div>'
        st.markdown(badge_html, unsafe_allow_html=True)

        ids = [p["id"] for p in pipeline]
        df = pd.DataFrame(pipeline)[["company", "role", "status", "sponsorship", "follow_up", "notes"]]
        df.columns = ["Company", "Role", "Status", "Sponsorship", "Follow-up", "Notes"]

        edited = st.data_editor(
            df, key="pipeline_editor", num_rows="fixed", use_container_width=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(options=PIPELINE_STATUSES),
                "Sponsorship": st.column_config.SelectboxColumn(options=["Unknown / to ask", "Confirmed yes", "Confirmed no"]),
            },
        )
        if st.button("💾 Save changes", key="save_pipeline_changes_btn"):
            if db:
                for i, row in edited.iterrows():
                    orig = df.iloc[i]
                    if not row.equals(orig):
                        db.collection("job_pipeline").document(ids[i]).update({
                            "company": row["Company"], "role": row["Role"], "status": row["Status"],
                            "sponsorship": row["Sponsorship"], "follow_up": row["Follow-up"], "notes": row["Notes"],
                        })
                st.success("Saved.")
                st.rerun()

        st.divider()
        remove_label = st.selectbox("Remove an application", [f'{p["company"]} — {p["role"]}' for p in pipeline])
        if st.button("🗑️ Remove from tracker", key="remove_app_btn"):
            idx = [f'{p["company"]} — {p["role"]}' for p in pipeline].index(remove_label)
            if db:
                db.collection("job_pipeline").document(ids[idx]).delete()
                st.rerun()
    else:
        st.info("Nothing logged yet — add your first application above.")

# =========================================================
# JOB FEED
# =========================================================
elif section == "Job Feed":
    st.title("Job Feed")
    st.markdown('<p class="section-caption">Pulls live listings on demand from Adzuna. This is a search you run, not a push notification — open the app and click Search when you want fresh results. Ask me to wire up a scheduled email digest if you want it to check automatically while the app is closed.</p>', unsafe_allow_html=True)

    if not adzuna_id or not adzuna_key:
        st.info("Add a free Adzuna App ID and App Key in the sidebar (⚙️ API keys) to turn this on — sign up at developer.adzuna.com. Everything else in the app works without it.")
    else:
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            keywords = st.text_input("Keywords", value="AI Engineer OR Platform Engineer OR RPA Developer")
        with c2:
            location = st.text_input("Location", value="", placeholder="e.g. Seattle, WA — leave blank for nationwide")
        with c3:
            num_results = st.number_input("Results", value=10, min_value=5, max_value=50, step=5, help="How many jobs to fetch")

        if st.button("🔍 Search jobs", key="search_adzuna_btn"):
            with st.spinner("Searching Adzuna…"):
                results, err = fetch_jobs(adzuna_id, adzuna_key, keywords, location, results=num_results)
            st.session_state["job_feed_searched"] = True
            if err == "missing_keys":
                st.warning("Missing Adzuna credentials.")
                st.session_state["job_feed_results"] = []
            elif err:
                st.error(f"Adzuna error: {err}")
                st.session_state["job_feed_results"] = []
            else:
                st.session_state["job_feed_results"] = results

        if st.session_state.get("job_feed_searched") and not st.session_state.get("job_feed_results"):
            st.info("No results for that search. Try broader keywords, or clear the location field entirely.")

        results = st.session_state.get("job_feed_results", [])
        if results:
            sponsor_filter = st.selectbox("Filter by sponsorship", ["All", "Mentions sponsorship", "No sponsorship", "Unclear"], help="🟢 mentions | 🔴 explicitly no | 🟡 unclear")
            
            filtered_jobs = []
            for job in results:
                full_desc = job.get("description", "")
                status = detect_sponsorship(full_desc)
                
                if sponsor_filter == "All":
                    filtered_jobs.append(job)
                elif sponsor_filter == "Mentions sponsorship" and status == "yes":
                    filtered_jobs.append(job)
                elif sponsor_filter == "No sponsorship" and status == "no":
                    filtered_jobs.append(job)
                elif sponsor_filter == "Unclear" and status == "unclear":
                    filtered_jobs.append(job)
            
            if not filtered_jobs:
                st.info(f"No jobs match the '{sponsor_filter}' filter.")
            else:
                st.caption(f"{len(filtered_jobs)} of {len(results)} jobs match your filter")
        else:
            filtered_jobs = []

        for job in filtered_jobs:
            title = job.get("title", "Untitled role")
            company = job.get("company", {}).get("display_name", "Unknown company")
            loc = job.get("location", {}).get("display_name", "")
            desc = (job.get("description") or "")[:280] + "…"
            link = job.get("redirect_url", "")
            full_desc = job.get("description", "")
            
            # Detect sponsorship mention
            sponsor_status = detect_sponsorship(full_desc)
            sponsor_badge = ""
            sponsor_color = ""
            sponsor_text = ""
            if sponsor_status == "yes":
                sponsor_badge = "🟢"
                sponsor_color = "var(--positive)"
                sponsor_text = "Sponsorship mentioned"
            elif sponsor_status == "no":
                sponsor_badge = "🔴"
                sponsor_color = "var(--critical)"
                sponsor_text = "No sponsorship"
            else:
                sponsor_badge = "🟡"
                sponsor_color = "var(--warning)"
                sponsor_text = "Sponsorship unclear"
            
            st.markdown(f'<div class="job-card"><div class="job-title">{title}</div><div class="job-meta">{company} · {loc}</div><div class="job-desc">{desc}</div><div style="margin-top:8px;font-size:0.85rem;color:{sponsor_color};">{sponsor_badge} {sponsor_text}</div></div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 1, 5])
            with c1:
                if st.button("＋ Save to tracker", key=f"save_{job.get('id')}"):
                    if db:
                        sponsor_value = "Confirmed yes" if sponsor_status == "yes" else ("Confirmed no" if sponsor_status == "no" else "Unknown / to ask")
                        db.collection("job_pipeline").add({
                            "company": company, "role": title, "url": link, "status": "To Apply",
                            "sponsorship": sponsor_value, "follow_up": (today + datetime.timedelta(days=5)).strftime("%Y-%m-%d"),
                            "notes": "Added from Job Feed", "created_at": firestore.SERVER_TIMESTAMP,
                        })
                        st.toast(f"Saved {title} at {company}")
            with c2:
                st.caption(f"Sponsor: {sponsor_status}")
            with c3:
                if link:
                    st.markdown(f"[View posting]({link})")

# =========================================================
# INTERVIEW PREP (integrated: resume + job fit + company prep)
# =========================================================
elif section == "Interview Prep":
    st.title("Interview Prep")
    st.markdown('<p class="section-caption">Upload your resume once, then prep for specific companies by analyzing the job posting against your background.</p>', unsafe_allow_html=True)

    # --- Show saved prep sessions ---
    if db:
        try:
            saved_preps = list(db.collection("interview_preps").order_by("created_at", direction=firestore.Query.DESCENDING).stream())
            if saved_preps:
                st.subheader("📚 Saved Prep Sessions")
                for prep in saved_preps[:5]:
                    data = prep.to_dict()
                    company = data.get("company", "Unknown")
                    role = data.get("role", "Unknown role")
                    analysis = data.get("analysis", {})
                    score = analysis.get("fit_score", "?")
                    c1, c2, c3 = st.columns([4, 1, 1])
                    with c1:
                        if st.button(f"**{company} — {role}** (Score: {score}/10)", key=f"load_prep_{prep.id}", help="Click to view this prep session"):
                            st.session_state["prep_analysis"] = analysis
                            st.session_state["selected_prep_company"] = company
                            st.session_state["selected_prep_role"] = role
                    with c2:
                        st.caption(data.get("created_at", "").strftime("%b %d") if hasattr(data.get("created_at", ""), "strftime") else "")
                    with c3:
                        if st.button("🗑️", key=f"del_prep_{prep.id}"):
                            db.collection("interview_preps").document(prep.id).delete()
                            st.rerun()
                st.divider()
        except Exception:
            pass

    if not client:
        st.info("Add a Gemini API key in the sidebar to turn on job analysis.")
    else:
        # --- Resume Management ---
        st.subheader("📄 Your Resume")
        
        # Load saved resume from DB on first load
        if "current_resume" not in st.session_state:
            saved_resume = get_resume_from_db()
            st.session_state["current_resume"] = saved_resume
        
        resume_mode = st.radio("Resume source", ["Paste text", "Upload file"], horizontal=True, label_visibility="collapsed")
        
        if resume_mode == "Paste text":
            resume_text = st.text_area("Paste your resume as plain text", height=150, key="resume_paste", value=st.session_state.get("current_resume", ""))
            if resume_text and resume_text != st.session_state.get("current_resume"):
                st.session_state["current_resume"] = resume_text
                save_resume_to_db(resume_text)
                st.success("Resume saved ✓")
        else:
            uploaded_file = st.file_uploader("Upload resume (.txt, .pdf, .docx)", type=["txt", "pdf", "docx"])
            if uploaded_file:
                if uploaded_file.type == "text/plain":
                    resume_text = uploaded_file.read().decode("utf-8")
                elif uploaded_file.type == "application/pdf":
                    try:
                        import PyPDF2
                        reader = PyPDF2.PdfReader(uploaded_file)
                        resume_text = "\n".join([page.extract_text() for page in reader.pages])
                    except ImportError:
                        st.error("PDF support requires PyPDF2 — run: pip install PyPDF2 --break-system-packages")
                        resume_text = None
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    try:
                        from docx import Document
                        doc = Document(uploaded_file)
                        resume_text = "\n".join([p.text for p in doc.paragraphs])
                    except ImportError:
                        st.error("DOCX support requires python-docx — run: pip install python-docx --break-system-packages")
                        resume_text = None
                else:
                    resume_text = None
                
                if resume_text:
                    st.session_state["current_resume"] = resume_text
                    save_resume_to_db(resume_text)
                    st.success(f"Loaded {len(resume_text)} characters from {uploaded_file.name} ✓ Saved")

        current_resume = st.session_state.get("current_resume", "")
        if current_resume:
            with st.expander("Preview current resume", expanded=False):
                st.text(current_resume[:500] + "…" if len(current_resume) > 500 else current_resume)
        else:
            st.caption("No resume loaded yet — paste or upload one above.")

        st.divider()

        # --- Prep for a specific company ---
        st.subheader("🎯 Prep for a Company")
        
        pipeline = get_pipeline()
        company_options = [f'{p["company"]} — {p["role"]}' for p in pipeline]
        
        prep_mode = st.radio("Job source", ["Pick from your pipeline", "Paste job description"], horizontal=True, label_visibility="collapsed")

        jd_text = ""
        selected_company = None
        if prep_mode == "Pick from your pipeline":
            if company_options:
                selected = st.selectbox("Select a company to prep for", company_options)
                idx = company_options.index(selected)
                selected_company = pipeline[idx]
                jd_text = selected_company.get("notes", "")
                if not jd_text:
                    st.info("This application doesn't have the job description saved. Paste it below to analyze, or go back to Job Tracker and add it to the Notes field.")
            else:
                st.info("No applications in your pipeline yet. Add one in Job Tracker first, then come back here to prep.")
        else:
            jd_text = st.text_area("Paste the job description", height=150, key="jd_paste_prep")

        analyze_col = st.columns(1)[0]
        with analyze_col:
            if st.button("📊 Analyze Fit & Get Resume Suggestions", key="analyze_btn_prep"):
                if not jd_text or not current_resume:
                    st.warning("Paste a resume and a job description first.")
                else:
                    with st.spinner("Analyzing job + resume…"):
                        try:
                            prompt = f"""You are a technical recruiter and career coach. Analyze this candidate's resume against the job posting.

CRITICAL: Only reference experiences, skills, and achievements that are EXPLICITLY mentioned in the resume. Do not invent, assume, or hallucinate details that aren't in the text. If something is unclear or missing, note it as a gap.

CANDIDATE RESUME:
{current_resume}

JOB DESCRIPTION:
{jd_text}

Return ONLY valid JSON, no markdown, in this exact shape:
{{
  "fit_score": <int 1-10>,
  "score_reason": "<one sentence, only referencing what's in the resume>",
  "keywords_to_add": ["<skills/techs in the job description but NOT in the resume>"],
  "keywords_to_emphasize": ["<skills EXPLICITLY in the resume that match the job>"],
  "talking_points": ["<up to 3 specific things from the resume to highlight>"],
  "resume_changes": ["<edits based ONLY on what's in the resume: reword to match job terms, add missing sections, etc.>"],
  "red_flags": ["<gaps between resume and job, or concerns in the job posting>"]
}}"""
                            response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
                            text = response.text.strip()
                            if text.startswith("```"):
                                text = text.strip("`").split("\n", 1)[-1] if "\n" in text else text[3:]
                            st.session_state["prep_analysis"] = json.loads(text)
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")

        # --- Display analysis results ---
        analysis = st.session_state.get("prep_analysis")
        if analysis:
            st.warning("⚠️ **AI-generated analysis** — Review carefully. Double-check all suggestions against your actual resume. If you see claims about skills/dates you don't remember, ignore them — this is AI and can hallucinate.")
            
            score = analysis.get("fit_score", 0)
            color = "var(--positive)" if score >= 8 else "var(--warning)" if score >= 5 else "var(--critical)"
            st.markdown(f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:2.2rem;font-weight:700;color:{color}">{score}/10</div>', unsafe_allow_html=True)
            st.caption(analysis.get("score_reason", ""))

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Resume gaps")
                for kw in analysis.get("keywords_to_add", []):
                    st.write(f"• **Add:** {kw}")
                for kw in analysis.get("keywords_to_emphasize", []):
                    st.write(f"• **Emphasize:** {kw}")

            with c2:
                st.subheader("Talking points")
                for tp in analysis.get("talking_points", []):
                    st.write(f"• {tp}")

            st.subheader("Resume edits")
            st.caption("Specific changes to make before the screen:")
            for change in analysis.get("resume_changes", []):
                st.write(f"→ {change}")

            flags = analysis.get("red_flags", [])
            if flags:
                st.subheader("Red flags")
                for f in flags:
                    st.warning(f)

            # Save this prep session
            if selected_company and st.button("💾 Save prep session for this company", key="save_prep_session_btn"):
                if db:
                    db.collection("interview_preps").add({
                        "company": selected_company["company"],
                        "role": selected_company["role"],
                        "analysis": analysis,
                        "created_at": firestore.SERVER_TIMESTAMP,
                    })
                    st.success("Saved. You can find this again later if you search your preps.")

        st.divider()

        # --- Defense reference (generic, always available) ---
        st.subheader("📚 Defense Reference")
        with st.expander("LangGraph + Chroma Resume Screening project"):
            st.markdown("""
- **Orchestration:** LangGraph state machine managing multi-step evaluation loops over candidate batches.
- **Retrieval:** Chroma vector store with embedding-based semantic search on resumes and job descriptions.
- **Evaluation:** GPT-4o-mini with Pydantic structured output for consistent scoring.
- **API:** FastAPI backend exposing async endpoints; Streamlit frontend for interactive testing.
- **How to defend:** "We chose LangGraph for its state management, Chroma for its simplicity (no external DB dependency), and structured outputs to lock down reliable scores."
            """)

        with st.expander("Platform Engineering at Capgemini"):
            st.markdown("""
- **LLM integration:** Replaced rule engines with REST-API-backed LLM calls, cutting manual intervention by 30%.
- **CI/CD:** Git-based pipelines automating bot testing and staging deployments.
- **How to defend:** "The shift from hardcoded logic to model-driven decisions made the system adaptable; the automation meant faster iteration."
            """)

        st.divider()

        # --- Scratchpad ---
        st.subheader("📝 Scratchpad")
        note = st.text_area("Jot down interviewer questions, patterns, company-specific intel", height=100, key="note_input_prep")
        if st.button("Save note to scratchpad", key="save_scratchpad_note_btn") and note:
            if db:
                db.collection("prep_notes").add({"note": note, "created_at": firestore.SERVER_TIMESTAMP})
                st.success("Saved")
            else:
                st.session_state.setdefault("local_notes", []).append(note)
                st.success("Saved (locally, since Firebase isn't connected)")

        if db:
            try:
                notes = list(db.collection("prep_notes").order_by("created_at", direction=firestore.Query.DESCENDING).stream())
                if notes:
                    st.subheader("Recent notes")
                    for n in notes[:5]:
                        data = n.to_dict()
                        c1, c2 = st.columns([6, 1])
                        with c1:
                            st.caption(data.get("note", ""))
                        with c2:
                            if st.button("🗑️", key=f"del_note_{n.id}"):
                                db.collection("prep_notes").document(n.id).delete()
                                st.rerun()
            except Exception:
                pass
        elif st.session_state.get("local_notes"):
            st.subheader("Local notes (not saved to Firebase)")
            for i, note in enumerate(st.session_state["local_notes"][:5]):
                c1, c2 = st.columns([6, 1])
                with c1:
                    st.caption(note)
                with c2:
                    if st.button("🗑️", key=f"del_local_{i}"):
                        st.session_state["local_notes"].pop(i)
                        st.rerun()