import streamlit as st
import sqlite3
import hashlib
import secrets
import re
from datetime import datetime
from pathlib import Path
import json
import urllib.error
import urllib.parse
import urllib.request

DB_PATH = Path(__file__).parent / "database.db"

st.set_page_config(page_title="CareerMatch | Job & Company Recommendation", page_icon="🎯", layout="wide")

# -------------------- DATABASE --------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, salt TEXT NOT NULL,
            degree TEXT DEFAULT '', branch TEXT DEFAULT '',
            graduation_year INTEGER, experience TEXT DEFAULT '',
            skills TEXT DEFAULT '', interests TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS companies(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL, industry TEXT, location TEXT,
            description TEXT, website TEXT, size TEXT
        );
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER, title TEXT NOT NULL, location TEXT,
            job_type TEXT, required_skills TEXT, min_qualification TEXT,
            experience_level TEXT, salary_range TEXT, description TEXT,
            is_demo INTEGER DEFAULT 1,
            FOREIGN KEY(company_id) REFERENCES companies(id)
        );
        CREATE TABLE IF NOT EXISTS saved_jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, job_id INTEGER,
            UNIQUE(user_id, job_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        CREATE TABLE IF NOT EXISTS shortlisted_companies(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, company_id INTEGER,
            UNIQUE(user_id, company_id)
        );
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, job_id INTEGER, status TEXT DEFAULT 'Interested',
            applied_on TEXT, notes TEXT DEFAULT ''
        );
        """)
        count = con.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        if count == 0:
            companies = [
                ("TCS", "IT Services", "India", "Technology consulting, software services and digital transformation.", "https://www.tcs.com", "Large"),
                ("Infosys", "IT Services", "India", "Digital services, consulting and technology solutions.", "https://www.infosys.com", "Large"),
                ("Wipro", "IT Services", "India", "Information technology, consulting and business process services.", "https://www.wipro.com", "Large"),
                ("HCLTech", "IT Services", "India", "Engineering, cloud, software and IT infrastructure services.", "https://www.hcltech.com", "Large"),
                ("Accenture", "Consulting & IT", "India / Global", "Technology consulting and business transformation.", "https://www.accenture.com", "Large"),
                ("Tech Mahindra", "IT Services", "India", "Digital transformation, telecom and enterprise solutions.", "https://www.techmahindra.com", "Large"),
                ("Zoho", "Software Product", "India", "Business software and cloud-based applications.", "https://www.zoho.com", "Large"),
                ("Freshworks", "Software Product", "India / Global", "Customer and employee experience software products.", "https://www.freshworks.com", "Large"),
                ("IBM", "Technology", "India / Global", "Cloud, AI, enterprise software and consulting.", "https://www.ibm.com", "Large"),
                ("Deloitte", "Consulting", "India / Global", "Audit, consulting, risk advisory and technology services.", "https://www.deloitte.com", "Large")
            ]
            con.executemany("INSERT INTO companies(name,industry,location,description,website,size) VALUES(?,?,?,?,?,?)", companies)
            jobs = [
                (1,"Python Developer","India","Full-time","Python, SQL, Git","BCA / BSc / BTech","Fresher","₹3–6 LPA","Build and maintain Python applications."),
                (1,"Data Analyst","India","Full-time","Python, SQL, Excel, Power BI","Any graduate with relevant skills","Fresher","₹3–6 LPA","Analyze data and prepare business reports."),
                (2,"Junior Data Engineer","India","Full-time","Python, SQL, ETL","BCA / BSc / BTech","0–2 years","₹4–7 LPA","Support data pipelines and data platforms."),
                (3,"Frontend Developer","India","Full-time","HTML, CSS, JavaScript, React","Any graduate with relevant skills","Fresher","₹3–5 LPA","Develop responsive web interfaces."),
                (4,"Software Engineer Trainee","India","Full-time","C++, Java, OOP, SQL","BCA / BSc / BTech","Fresher","₹3–5 LPA","Work with engineering teams on software projects."),
                (5,"Associate Software Engineer","India","Full-time","Python, Java, SQL, Problem Solving","Any graduate with relevant skills","Fresher","₹4–7 LPA","Contribute to application development projects."),
                (6,"Data Science Intern","India","Internship","Python, Pandas, Statistics, ML","Pursuing bachelor's degree","Intern","Stipend varies","Assist with data preparation and model experiments."),
                (7,"Application Support Engineer","India","Full-time","SQL, Linux, Communication","Any graduate with relevant skills","Fresher","₹3–5 LPA","Support customers using business software."),
                (8,"QA Automation Intern","India","Internship","Python, Selenium, Testing","Pursuing bachelor's degree","Intern","Stipend varies","Create and execute automated test cases."),
                (9,"AI/ML Intern","India","Internship","Python, Machine Learning, Statistics","Pursuing bachelor's degree","Intern","Stipend varies","Assist in building and evaluating ML models."),
                (10,"Technology Analyst","India","Full-time","SQL, Python, Excel, Communication","Any graduate with relevant skills","Fresher","₹4–7 LPA","Support technology and analytics engagements.")
            ]
            con.executemany("""INSERT INTO jobs(company_id,title,location,job_type,required_skills,min_qualification,experience_level,salary_range,description)
                               VALUES(?,?,?,?,?,?,?,?,?)""", jobs)

init_db()

# -------------------- AUTHENTICATION --------------------
def make_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000).hex()
    return digest, salt

def verify_password(password, stored_hash, salt):
    return secrets.compare_digest(make_password(password, salt)[0], stored_hash)

def current_user():
    if "user_id" not in st.session_state:
        return None
    with get_conn() as con:
        return con.execute("SELECT * FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()

def register_user(name, email, password):
    digest, salt = make_password(password)
    try:
        with get_conn() as con:
            con.execute("INSERT INTO users(name,email,password_hash,salt) VALUES(?,?,?,?)",
                        (name.strip(), email.strip().lower(), digest, salt))
        return True, "Account created. Please log in."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."

def login_user(email, password):
    with get_conn() as con:
        user = con.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    if user and verify_password(password, user["password_hash"], user["salt"]):
        st.session_state.user_id = user["id"]
        return True
    return False


def admin_credentials():
    try:
        cfg = st.secrets["admin"]
        return str(cfg["email"]).strip().lower(), str(cfg["password_hash"]), str(cfg["salt"])
    except Exception:
        return "", "", ""

def verify_admin(email, password):
    admin_email, stored_hash, salt = admin_credentials()
    if not admin_email or not stored_hash or not salt:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
    return secrets.compare_digest(email.strip().lower(), admin_email) and secrets.compare_digest(digest, stored_hash)

# -------------------- RECOMMENDATION ENGINE --------------------
def tokens(value):
    return set(re.findall(r"[a-zA-Z0-9+#.]+", (value or "").lower()))

def score_job(user_skills, interests, job):
    user_terms = tokens(user_skills) | tokens(interests)
    required = tokens(job["required_skills"])
    if not required:
        return 0, []
    matched = sorted(user_terms & required)
    score = round(len(matched) / len(required) * 100)
    return score, matched

def extract_resume_text(uploaded_file):
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".txt"):
            return uploaded_file.getvalue().decode("utf-8", errors="ignore")
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if name.endswith(".docx"):
            from docx import Document
            import io
            doc = Document(io.BytesIO(uploaded_file.getvalue()))
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception as exc:
        st.error(f"Could not read this file: {exc}")
    return ""

# -------------------- LIVE JOBS API --------------------
@st.cache_data(ttl=300, show_spinner=False)
def search_jobsforce(q, city, state, job_type, work_mode, fresher, posted_within_days):
    """Fetch current public listings from JobsForce India; no API key is required."""
    params = {"per_page": 20, "page": 1}
    if q:
        params["q"] = q[:200]
    if city:
        params["city"] = city[:80]
    if state:
        params["state"] = state[:80]
    if job_type:
        params["job_type"] = job_type
    if work_mode:
        params["work_mode"] = work_mode
    if fresher:
        params["fresher"] = "true"
    if posted_within_days:
        params["posted_within_days"] = int(posted_within_days)

    url = "https://jobsforceindia.com/api/public/v1/jobs?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "CareerMatch/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            return {"error": "The jobs provider returned an unexpected response."}
        return payload
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return {"error": "The jobs provider is receiving too many requests. Please wait a minute and try again."}
        try:
            detail = json.loads(exc.read().decode("utf-8"))
            message = detail.get("error", {}).get("message", "")
        except Exception:
            message = ""
        return {"error": message or f"Jobs provider returned HTTP {exc.code}."}
    except urllib.error.URLError:
        return {"error": "Could not connect to JobsForce India. Check your internet connection and try again."}
    except Exception:
        return {"error": "Live job search is temporarily unavailable. Please try again later."}


# -------------------- UI --------------------
st.markdown("""

<style>
/* Overall background */
.stApp,
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 50%, #e0f2fe 100%) !important;
    color: #172554 !important;
}

/* Main page spacing */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}

/* Main headings */
.main h1, .main h2, .main h3 {
    color: #172554 !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
}

/* All normal text */
.main p,
.main li,
.main label,
.main span,
.main [data-testid="stWidgetLabel"],
.main [data-testid="stWidgetLabel"] p {
    color: #334155 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #172554 !important;
}
[data-testid="stSidebar"] * {
    color: #ffffff !important;
}

/* Input labels */
[data-testid="stWidgetLabel"] p,
.stTextInput label,
.stNumberInput label,
.stSelectbox label,
.stTextArea label {
    color: #26345c !important;
    font-weight: 650 !important;
}

/* Input fields */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stDateInput input {
    background: #ffffff !important;
    color: #172554 !important;
    border: 1px solid #c7d2fe !important;
    border-radius: 12px !important;
    min-height: 45px;
}

.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #94a3b8 !important;
}

/* Dropdowns */
[data-baseweb="select"] {
    background: #ffffff !important;
    color: #172554 !important;
    border-radius: 10px !important;
}

/* Buttons */
.stButton > button,
.stFormSubmitButton > button {
    background: linear-gradient(90deg, #5b4bdb, #3978e8) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 12px !important;
    min-height: 46px;
    font-weight: 700 !important;
    transition: 0.2s ease;
}

.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: #4338ca !important;
    color: #ffffff !important;
    border: none !important;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    color: #475569 !important;
    font-weight: 650 !important;
}

.stTabs [aria-selected="true"] {
    color: #5b4bdb !important;
}

/* Hero section */
.hero {
    padding: 34px;
    border-radius: 22px;
    background: linear-gradient(120deg, #172554, #4338ca, #2563eb);
    box-shadow: 0 12px 30px rgba(49, 46, 129, 0.18);
    margin-bottom: 24px;
}

.hero h1,
.hero p {
    color: #ffffff !important;
}

/* Information cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border: 1px solid #e0e7ff !important;
    border-radius: 18px !important;
    box-shadow: 0 6px 22px rgba(49, 46, 129, 0.07);
}

/* Metrics */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e0e7ff !important;
    border-radius: 16px !important;
    padding: 18px !important;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricValue"] {
    color: #172554 !important;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 14px !important;
}

/* Tables */
[data-testid="stDataFrame"] {
    background: #ffffff !important;
    border-radius: 12px !important;
}

/* CareerMatch landing page */
.cm-header{display:flex;align-items:center;justify-content:space-between;padding:8px 0 30px 0}
.cm-brand{font-size:1.65rem;font-weight:850;letter-spacing:-.7px;color:#172554}
.cm-brand span{color:#6254df}
.cm-pill{display:inline-block;padding:7px 13px;border:1px solid #dbe3ff;border-radius:30px;background:#ffffffb8;color:#5145cd;font-size:.78rem;font-weight:750}
.cm-left{padding:34px 28px 30px 0}
.cm-eyebrow{font-size:.76rem;font-weight:800;letter-spacing:.14em;color:#6254df;text-transform:uppercase;margin-bottom:16px}
.cm-title{font-size:clamp(2.3rem,4vw,3.65rem);line-height:1.08;font-weight:850;letter-spacing:-.055em;color:#172554;margin:0 0 18px}
.cm-title span{color:#6254df}
.cm-description{font-size:1.08rem;line-height:1.75;color:#52617e;margin-bottom:26px}
.cm-feature{display:flex;gap:13px;align-items:flex-start;margin:17px 0;color:#26345c}
.cm-feature-icon{display:flex;align-items:center;justify-content:center;flex:0 0 38px;height:38px;border-radius:12px;background:#e8eaff;color:#5145cd;font-size:1.1rem}
.cm-feature strong{display:block;color:#1e2b50;font-size:.96rem;margin-bottom:3px}
.cm-feature small{display:block;color:#64748b;font-size:.86rem;line-height:1.45}
.cm-trust{margin-top:28px;padding-top:18px;border-top:1px solid #dce4f7;color:#71809b;font-size:.8rem}
.cm-auth-card{background:#fff;border:1px solid #e4e9f7;border-radius:24px;padding:26px 28px;box-shadow:0 22px 65px rgba(44,55,112,.13);margin-top:8px}
.cm-auth-title{font-size:1.55rem;font-weight:800;color:#172554;letter-spacing:-.03em;margin-bottom:5px}
.cm-auth-sub{color:#71809b;font-size:.9rem;margin-bottom:18px}
.cm-footer{text-align:center;color:#8490a8;font-size:.78rem;padding:28px 0 8px}
.stTabs [data-baseweb="tab"]{padding:12px 18px}
@media(max-width:800px){.cm-left{padding:10px 0 20px}.cm-title{font-size:2.3rem}.cm-auth-card{padding:20px;margin-top:0}.cm-header{padding-bottom:15px}}


/* --- Global product polish: dashboard and every workspace page --- */
:root { color-scheme: light; }
html, body, [data-testid="stAppViewContainer"], .stApp {
    background: #f6f7fc !important;
}
[data-testid="stHeader"] {
    background: rgba(246,247,252,.92) !important;
}
[data-testid="stToolbar"] { right: 1rem; }
[data-testid="stMainBlockContainer"] {
    padding-top: 2.2rem !important;
    padding-left: clamp(1.5rem, 3vw, 3.2rem) !important;
    padding-right: clamp(1.5rem, 3vw, 3.2rem) !important;
    max-width: 1500px !important;
}
[data-testid="stSidebar"] {
    background: #172554 !important;
    border-right: 1px solid rgba(255,255,255,.08);
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1.3rem 1rem 1.5rem !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #e5eaff !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    border-radius: 9px !important;
    padding: .38rem .55rem !important;
    margin: .12rem 0 !important;
    transition: background .15s ease;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255,255,255,.10) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label p {
    color: #f8faff !important;
    font-weight: 550 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: rgba(129,140,248,.24) !important;
}
.main h1 {
    font-size: clamp(1.9rem, 3vw, 2.5rem) !important;
    margin-bottom: .45rem !important;
}
.main h2 { font-size: 1.5rem !important; }
.main h3 { font-size: 1.2rem !important; }
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border: 1px solid #e6eaf3 !important;
    border-radius: 16px !important;
    box-shadow: 0 5px 18px rgba(25,42,90,.055) !important;
    padding: .35rem !important;
}
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e6eaf3 !important;
    border-radius: 16px !important;
    padding: 1.05rem 1.15rem !important;
    box-shadow: 0 5px 18px rgba(25,42,90,.045) !important;
}
[data-testid="stMetricLabel"] p {
    color: #64748b !important;
    font-size: .84rem !important;
    font-weight: 650 !important;
}
[data-testid="stMetricValue"] {
    color: #172554 !important;
    font-weight: 780 !important;
}
[data-testid="stCaptionContainer"] p {
    color: #71809b !important;
}
[data-testid="stAlert"] {
    border-radius: 13px !important;
    border: 1px solid #e2e8f0 !important;
}
.stProgress > div > div > div > div {
    background: linear-gradient(90deg,#6558df,#3982ec) !important;
}
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: #6254df !important;
}
.stButton > button, .stFormSubmitButton > button {
    box-shadow: 0 4px 10px rgba(79,70,229,.14) !important;
}
[data-testid="stDataFrame"], [data-testid="stTable"] {
    border: 1px solid #e6eaf3 !important;
    border-radius: 13px !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e6eaf3 !important;
    border-radius: 13px !important;
}
[data-testid="stForm"] {
    background: #ffffff !important;
    border: 1px solid #e6eaf3 !important;
    border-radius: 16px !important;
    padding: 1.2rem !important;
}
@media (max-width: 800px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}


/* Authentication tabs: keep every tab label readable on the light card */
.stTabs [data-baseweb="tab"],
.stTabs [data-baseweb="tab"] *,
.stTabs button[role="tab"],
.stTabs button[role="tab"] * {
    color: #334155 !important;
    opacity: 1 !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"],
.stTabs [data-baseweb="tab"][aria-selected="true"] *,
.stTabs button[role="tab"][aria-selected="true"],
.stTabs button[role="tab"][aria-selected="true"] * {
    color: #5145cd !important;
}

</style>

""", unsafe_allow_html=True)

user = current_user()
if not user:
    st.markdown("""
    <div class="cm-header">
      <div class="cm-brand">Career<span>Match</span> 🎯</div>
      <div class="cm-pill">SMARTER CAREER DISCOVERY</div>
    </div>
    """, unsafe_allow_html=True)
    left, right = st.columns([1.08, 0.92], gap="large")
    with left:
        st.markdown("""
        <div class="cm-left">
          <div class="cm-eyebrow">YOUR CAREER, WITH DIRECTION</div>
          <div class="cm-title">Find work that fits.<br><span>Build what’s next.</span></div>
          <div class="cm-description">Bring your skills, interests and ambitions together. Explore career paths, discover skill gaps and keep your job search organised in one place.</div>
          <div class="cm-feature">
            <div class="cm-feature-icon">✦</div>
            <div><strong>Relevant job matches</strong><small>See how your current skills align with sample job opportunities.</small></div>
          </div>
          <div class="cm-feature">
            <div class="cm-feature-icon">⌁</div>
            <div><strong>Clear skill development</strong><small>Identify missing skills and follow a practical learning roadmap.</small></div>
          </div>
          <div class="cm-feature">
            <div class="cm-feature-icon">✓</div>
            <div><strong>Stay organised</strong><small>Save roles, shortlist companies and track application progress.</small></div>
          </div>
          <div class="cm-trust">A career-planning workspace designed to help you take the next step with confidence.</div>
        </div>
        """, unsafe_allow_html=True)
    with right:
        st.markdown('<div class="cm-auth-card">', unsafe_allow_html=True)
        st.markdown('<div class="cm-auth-title">Welcome to CareerMatch</div><div class="cm-auth-sub">Sign in or create an account to get started.</div>', unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["Log in", "Create account", "Admin Login"])
        with tab1:
            email = st.text_input("Email address", key="login_email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")
            if st.button("Log in to CareerMatch", type="primary", use_container_width=True):
                if login_user(email, password):
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
        with tab2:
            name = st.text_input("Full name", key="reg_name", placeholder="Your full name")
            reg_email = st.text_input("Email address", key="reg_email", placeholder="you@example.com")
            p1 = st.text_input("Password (minimum 8 characters)", type="password", key="reg_pass", placeholder="Create a password")
            p2 = st.text_input("Confirm password", type="password", key="reg_confirm", placeholder="Re-enter your password")
            if st.button("Create my account", type="primary", use_container_width=True):
                if not name.strip() or not reg_email.strip():
                    st.error("Please enter your name and email.")
                elif len(p1) < 8:
                    st.error("Password must contain at least 8 characters.")
                elif p1 != p2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = register_user(name, reg_email, p1)
                    (st.success if ok else st.error)(msg)

        with tab3:
            st.markdown("**Administrator access**")
            admin_email = st.text_input("Admin email", key="admin_login_email", placeholder="admin@example.com")
            admin_password = st.text_input("Admin password", type="password", key="admin_login_password", placeholder="Enter admin password")
            if st.button("Sign in as administrator", type="primary", use_container_width=True):
                if verify_admin(admin_email, admin_password):
                    st.session_state.is_admin = True
                    st.session_state.admin_email = admin_email.strip().lower()
                    st.rerun()
                else:
                    st.error("Admin credentials are incorrect or admin access has not been configured.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="cm-footer">CareerMatch · Company Selection &amp; Job Recommendation System<br>Academic prototype · Sample listings are illustrative and are not verified live vacancies.</div>', unsafe_allow_html=True)
    st.stop()


# Separate administrator session and control panel
if st.session_state.get("is_admin", False):
    st.sidebar.title("🛡️ CareerMatch Admin")
    st.sidebar.caption("Administrator console")
    if st.sidebar.button("Admin logout", use_container_width=True):
        st.session_state.pop("is_admin", None)
        st.session_state.pop("admin_email", None)
        st.rerun()
    st.title("Administrator Dashboard")
    st.caption("Restricted management area · Signed in as " + st.session_state.get("admin_email", "administrator"))
    with get_conn() as con:
        total_users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_companies = con.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        total_jobs = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        demo_jobs = con.execute("SELECT COUNT(*) FROM jobs WHERE is_demo=1").fetchone()[0]
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Registered users", total_users)
    m2.metric("Companies", total_companies)
    m3.metric("Total jobs", total_jobs)
    m4.metric("Sample jobs", demo_jobs)
    users_tab, jobs_tab, companies_tab = st.tabs(["Users", "Manage sample jobs", "Companies"])
    with users_tab:
        st.subheader("Registered users")
        with get_conn() as con:
            rows = con.execute("SELECT id,name,email,degree,branch,created_at FROM users ORDER BY id DESC").fetchall()
        if rows:
            st.dataframe([dict(row) for row in rows], use_container_width=True, hide_index=True)
        else:
            st.info("No registered users yet.")
    with jobs_tab:
        st.subheader("Add a sample job")
        companies = get_companies()
        company_map = {c["name"]: c["id"] for c in companies}
        with st.form("admin_add_job_form", clear_on_submit=True):
            company_name = st.selectbox("Company", list(company_map))
            title = st.text_input("Job title")
            location = st.text_input("Location", "India")
            job_type = st.selectbox("Job type", ["Full-time","Internship","Part-time","Contract"])
            skills = st.text_input("Required skills (comma-separated)")
            qualification = st.text_input("Minimum qualification")
            experience_level = st.selectbox("Experience", ["Fresher","Intern","0–2 years","2+ years"])
            salary = st.text_input("Salary range", "Not specified")
            description = st.text_area("Description")
            submitted = st.form_submit_button("Add sample job", type="primary")
        if submitted:
            if title.strip() and skills.strip():
                with get_conn() as con:
                    con.execute("""INSERT INTO jobs(company_id,title,location,job_type,required_skills,min_qualification,experience_level,salary_range,description,is_demo)
                                   VALUES(?,?,?,?,?,?,?,?,?,1)""",
                                (company_map[company_name],title.strip(),location.strip(),job_type,skills.strip(),qualification.strip(),experience_level,salary.strip(),description.strip()))
                st.success("Sample job added.")
                st.rerun()
            else:
                st.error("Job title and required skills are required.")
        st.subheader("Existing sample jobs")
        with get_conn() as con:
            job_rows = con.execute("SELECT jobs.id,jobs.title,companies.name AS company_name,jobs.required_skills FROM jobs JOIN companies ON jobs.company_id=companies.id ORDER BY jobs.id DESC").fetchall()
        for job in job_rows:
            c1,c2 = st.columns([5,1])
            c1.write(f"**{job['title']}** · {job['company_name']} · {job['required_skills']}")
            if c2.button("Delete", key=f"admin_delete_job_{job['id']}"):
                with get_conn() as con:
                    con.execute("DELETE FROM saved_jobs WHERE job_id=?", (job["id"],))
                    con.execute("DELETE FROM applications WHERE job_id=?", (job["id"],))
                    con.execute("DELETE FROM jobs WHERE id=?", (job["id"],))
                st.success("Job deleted.")
                st.rerun()
    with companies_tab:
        st.subheader("Company directory")
        company_rows = get_companies()
        if company_rows:
            st.dataframe([dict(row) for row in company_rows], use_container_width=True, hide_index=True)
        st.caption("Company records are displayed here. Editing and deletion can be added after the admin workflow is verified.")
    st.info("Job listings in this academic prototype are sample/demo data and are not verified live vacancies.")
    st.stop()

# Sidebar navigation
with st.sidebar:
    st.title("🎯 CareerMatch")
    st.write(f"Welcome, **{user['name']}**")
    page = st.radio("Navigation", ["Dashboard", "My Profile", "Job Recommendations", "Live Jobs", "Company Recommendations", "Company Explorer", "Skill Gap & Roadmap", "Resume Analyzer", "Saved Jobs", "Application Tracker", "Compare Companies"])
    if st.button("Logout", use_container_width=True):
        st.session_state.pop("user_id", None)
        st.session_state.pop("is_admin", None)
        st.session_state.pop("admin_email", None)
        st.rerun()

def get_jobs():
    with get_conn() as con:
        return con.execute("""SELECT jobs.*, companies.name AS company_name, companies.industry, companies.website
                              FROM jobs JOIN companies ON jobs.company_id=companies.id ORDER BY jobs.id""").fetchall()

def get_companies():
    with get_conn() as con:
        return con.execute("SELECT * FROM companies ORDER BY name").fetchall()

def save_job(job_id):
    with get_conn() as con:
        con.execute("INSERT OR IGNORE INTO saved_jobs(user_id,job_id) VALUES(?,?)", (user["id"], job_id))

def shortlist_company(company_id):
    with get_conn() as con:
        con.execute("INSERT OR IGNORE INTO shortlisted_companies(user_id,company_id) VALUES(?,?)", (user["id"], company_id))

if page == "Dashboard":
    st.markdown(f"""
    <div class="hero">
      <div style="font-size:.78rem;font-weight:800;letter-spacing:.14em;color:#cbd7ff;text-transform:uppercase;">CAREERMATCH • CAREER OVERVIEW</div>
      <h1>Welcome back, {user['name'].replace('<','&lt;').replace('>','&gt;')} 👋</h1>
      <p>Your next opportunity starts with the right skills, the right role and a clear plan.</p>
    </div>
    """, unsafe_allow_html=True)

    with get_conn() as con:
        saved = con.execute("SELECT COUNT(*) FROM saved_jobs WHERE user_id=?", (user["id"],)).fetchone()[0]
        apps = con.execute("SELECT COUNT(*) FROM applications WHERE user_id=?", (user["id"],)).fetchone()[0]
        shortlisted = con.execute("SELECT COUNT(*) FROM shortlisted_companies WHERE user_id=?", (user["id"],)).fetchone()[0]
        interviews = con.execute("SELECT COUNT(*) FROM applications WHERE user_id=? AND status='Interview'", (user["id"],)).fetchone()[0]
        recent = con.execute("""SELECT jobs.title, companies.name AS company_name, applications.status, applications.applied_on
                                FROM applications JOIN jobs ON applications.job_id=jobs.id
                                JOIN companies ON jobs.company_id=companies.id
                                WHERE applications.user_id=? ORDER BY applications.id DESC LIMIT 4""",
                             (user["id"],)).fetchall()

    st.markdown('<div class="section-kicker">YOUR ACTIVITY</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jobs saved", saved)
    m2.metric("Applications", apps)
    m3.metric("Companies shortlisted", shortlisted)
    m4.metric("Interviews", interviews)

    st.write("")
    left, right = st.columns([1.55, 1], gap="large")
    with left:
        st.markdown('<div class="section-kicker">CAREER DISCOVERY</div>', unsafe_allow_html=True)
        st.subheader("Your next steps")
        with st.container(border=True):
            st.markdown("**01  Complete your profile**")
            profile_fields = [user["degree"], user["branch"], user["graduation_year"], user["experience"], user["skills"], user["interests"]]
            completed = sum(1 for value in profile_fields if value not in (None, "", 0))
            completion = int(completed / len(profile_fields) * 100)
            st.progress(completion, text=f"Profile completeness · {completion}%")
            st.caption("A detailed profile helps the system find more relevant roles.")
            if not user["skills"] or not user["interests"]:
                st.warning("Add your skills and career interests to personalize recommendations.")
            else:
                st.success("Your skills and interests are ready for matching.")

        with st.container(border=True):
            st.markdown("**02  Explore matched opportunities**")
            ranked = []
            for job in get_jobs():
                score, matched = score_job(user["skills"], user["interests"], job)
                ranked.append((score, matched, job))
            ranked.sort(key=lambda x: x[0], reverse=True)
            best = ranked[0] if ranked else None
            if best and (user["skills"] or user["interests"]):
                st.write(f"**Top match:** {best[2]['title']} at {best[2]['company_name']}")
                st.caption(f"{best[0]}% skill match · {', '.join(best[1]) if best[1] else 'Build the listed skills to improve your match'}")
            else:
                st.write("Complete your profile to see your strongest job matches.")
            st.caption("Recommendations use the skills and interests saved in your profile.")

        with st.container(border=True):
            st.markdown("**03  Build skills for your target role**")
            st.write("Review missing skills and follow a practical learning roadmap.")
            st.caption("Use Skill Gap & Roadmap to choose a role and see what to learn next.")

    with right:
        st.markdown('<div class="section-kicker">APPLICATION PIPELINE</div>', unsafe_allow_html=True)
        st.subheader("Recent activity")
        with st.container(border=True):
            if recent:
                for item in recent:
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"{item['company_name']} · {item['status']} · {item['applied_on'] or 'Date not set'}")
                    st.divider()
            else:
                st.write("Your application activity will appear here.")
                st.caption("Add a role to your tracker from Job Recommendations.")

        st.markdown('<div class="section-kicker">QUICK INSIGHT</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("**A focused search works better**")
            st.write("Prioritize roles where you already meet several requirements, then use the skill-gap roadmap to close the remaining gaps.")
            st.info("Demo listings are for academic demonstration only. They are not verified live vacancies.")

    st.caption("CareerMatch · Personalized career planning workspace")

elif page == "My Profile":
    st.title("My Profile")
    with st.form("profile_form"):
        name = st.text_input("Full name", value=user["name"])
        degree = st.text_input("Degree (e.g. BCA)", value=user["degree"] or "")
        branch = st.text_input("Specialization (e.g. Data Science & AI)", value=user["branch"] or "")
        grad = st.number_input("Graduation year", min_value=2020, max_value=2040, value=int(user["graduation_year"] or 2028))
        experience = st.selectbox("Experience level", ["Fresher", "Internship experience", "0–2 years", "2+ years"],
                                  index=["Fresher","Internship experience","0–2 years","2+ years"].index(user["experience"] or "Fresher"))
        skills = st.text_area("Skills (comma-separated)", value=user["skills"] or "", placeholder="Python, SQL, C++, Excel, Statistics")
        interests = st.text_area("Career interests (comma-separated)", value=user["interests"] or "", placeholder="Data Analyst, Software Developer, AI/ML")
        submitted = st.form_submit_button("Save profile", type="primary")
        if submitted:
            with get_conn() as con:
                con.execute("""UPDATE users SET name=?,degree=?,branch=?,graduation_year=?,experience=?,skills=?,interests=? WHERE id=?""",
                            (name,degree,branch,int(grad),experience,skills,interests,user["id"]))
            st.success("Profile updated.")
            st.rerun()

elif page == "Job Recommendations":
    st.title("Personalized Live Job Recommendations")
    st.write("CareerMatch searches current external vacancies and ranks them against the skills and interests in your profile. Sample database jobs are not shown here.")

    profile_query = (user["interests"] or user["skills"] or "fresher").strip()
    if not user["skills"] and not user["interests"]:
        st.warning("Add your skills and career interests in My Profile to improve your recommendations. Showing fresher-friendly live vacancies for now.")

    with st.spinner("Finding live jobs that match your profile..."):
        result = search_jobsforce(profile_query, "", "", "", "", True, "7")

    if result.get("error"):
        st.error(result["error"])
        st.info("You can retry from the Live Jobs page after checking your internet connection.")
    else:
        listings = result.get("results", [])
        st.metric("Matching live listings", result.get("total", len(listings)))
        if not listings:
            st.info("No matching live jobs were returned. Update your skills/interests or try broader keywords in Live Jobs.")
        for job in listings:
            hiring = job.get("hiring") or {}
            location_data = job.get("location") or {}
            salary_data = job.get("salary") or {}
            experience_data = job.get("experience") or {}
            location_text = ", ".join(x for x in [location_data.get("city"), location_data.get("state"), location_data.get("country")] if x)
            if location_data.get("remote") or job.get("work_mode") == "remote":
                location_text = (location_text + " · " if location_text else "") + "Remote"
            skills_list = job.get("skills") or []
            match_score, matched_skills = score_job(
                user["skills"], user["interests"],
                {"required_skills": ", ".join(skills_list)}
            )
            with st.container(border=True):
                left, right = st.columns([4, 1])
                with left:
                    st.subheader(job.get("title") or "Untitled role")
                    st.write(f"**{hiring.get('display') or 'Employer details not provided'}** · {location_text or 'Location not specified'}")
                    st.write("**Experience:** " + (experience_data.get("label") or "Not specified"))
                    st.write("**Salary:** " + (salary_data.get("label") or "Not disclosed"))
                    if skills_list:
                        st.write("**Skills:** " + ", ".join(skills_list))
                    st.caption("Matched profile skills: " + (", ".join(matched_skills) if matched_skills else "No exact skill overlap identified"))
                    st.write(job.get("summary") or "No short description provided.")
                with right:
                    st.metric("Skill match", f"{match_score}%")
                    if job.get("url"):
                        st.link_button("View job", job["url"], use_container_width=True)
                    if job.get("apply_url"):
                        st.link_button("Apply", job["apply_url"], use_container_width=True)
        st.caption("These vacancies are fetched from JobsForce India. Verify the employer's posting and application page before applying.")

elif page == "Live Jobs":
    st.title("Live Job Search")
    st.write("Search current public vacancies from JobsForce India. These listings are fetched from the provider when you search; they are separate from CareerMatch's sample jobs.")

    with st.form("jobsforce_search_form"):
        default_query = (user["interests"] or user["skills"] or "")[:200]
        query = st.text_input("Job title or skills", value=st.session_state.get("live_jobs_q", default_query),
                              placeholder="e.g. Python Developer, Data Analyst, SQL")
        filter_a, filter_b, filter_c = st.columns(3)
        with filter_a:
            city = st.text_input("City", value=st.session_state.get("live_jobs_city", ""), placeholder="e.g. Lucknow")
        with filter_b:
            state = st.text_input("State", value=st.session_state.get("live_jobs_state", ""), placeholder="e.g. Uttar Pradesh")
        with filter_c:
            job_type_choice = st.selectbox("Job type", ["Any", "full-time", "part-time", "internship", "contract", "temporary"],
                                            index=["Any", "full-time", "part-time", "internship", "contract", "temporary"].index(st.session_state.get("live_jobs_type", "Any")))
        filter_d, filter_e = st.columns(2)
        with filter_d:
            work_mode_choice = st.selectbox("Work mode", ["Any", "remote", "hybrid", "onsite"],
                                             index=["Any", "remote", "hybrid", "onsite"].index(st.session_state.get("live_jobs_mode", "Any")))
        with filter_e:
            posted_choice = st.selectbox("Posted within", ["Any", "1", "3", "7", "14", "30"],
                                         index=["Any", "1", "3", "7", "14", "30"].index(st.session_state.get("live_jobs_posted", "7")))
        fresher_only = st.checkbox("Fresher-friendly jobs only", value=st.session_state.get("live_jobs_fresher", True))
        search_clicked = st.form_submit_button("Search live jobs", type="primary")

    if search_clicked:
        st.session_state["live_jobs_q"] = query.strip()
        st.session_state["live_jobs_city"] = city.strip()
        st.session_state["live_jobs_state"] = state.strip()
        st.session_state["live_jobs_type"] = job_type_choice
        st.session_state["live_jobs_mode"] = work_mode_choice
        st.session_state["live_jobs_posted"] = posted_choice
        st.session_state["live_jobs_fresher"] = fresher_only

    if "live_jobs_searched" not in st.session_state:
        st.session_state["live_jobs_searched"] = False
    if search_clicked:
        st.session_state["live_jobs_searched"] = True

    if st.session_state["live_jobs_searched"]:
        selected_type = st.session_state.get("live_jobs_type", "Any")
        selected_mode = st.session_state.get("live_jobs_mode", "Any")
        selected_posted = st.session_state.get("live_jobs_posted", "7")
        with st.spinner("Searching current vacancies..."):
            result = search_jobsforce(
                st.session_state.get("live_jobs_q", ""),
                st.session_state.get("live_jobs_city", ""),
                st.session_state.get("live_jobs_state", ""),
                "" if selected_type == "Any" else selected_type,
                "" if selected_mode == "Any" else selected_mode,
                st.session_state.get("live_jobs_fresher", True),
                "" if selected_posted == "Any" else selected_posted
            )

        if result.get("error"):
            st.error(result["error"])
        else:
            listings = result.get("results", [])
            st.metric("Matching live listings", result.get("total", len(listings)))
            for note in result.get("notes", []):
                st.caption(note)
            if not listings:
                st.info("No matching live jobs were returned. Try broader keywords or remove a filter.")
            for job in listings:
                hiring = job.get("hiring") or {}
                location_data = job.get("location") or {}
                salary_data = job.get("salary") or {}
                experience_data = job.get("experience") or {}
                location_text = ", ".join(x for x in [location_data.get("city"), location_data.get("state"), location_data.get("country")] if x)
                if location_data.get("remote") or job.get("work_mode") == "remote":
                    location_text = (location_text + " · " if location_text else "") + "Remote"
                with st.container(border=True):
                    left, right = st.columns([4, 1])
                    with left:
                        st.subheader(job.get("title") or "Untitled role")
                        st.write(f"**{hiring.get('display') or 'Employer details not provided'}** · {location_text or 'Location not specified'}")
                        details = [x for x in [job.get("job_type"), job.get("work_mode"), job.get("category")] if x]
                        if details:
                            st.caption(" · ".join(details))
                        st.write("**Experience:** " + (experience_data.get("label") or "Not specified"))
                        st.write("**Salary:** " + (salary_data.get("label") or "Not disclosed"))
                        skills_list = job.get("skills") or []
                        if skills_list:
                            st.write("**Skills:** " + ", ".join(skills_list))
                            match_score, matched_skills = score_job(user["skills"], user["interests"], {"required_skills": ", ".join(skills_list)})
                            st.caption("Profile skill match: " + str(match_score) + "% · Matched: " + (", ".join(matched_skills) if matched_skills else "No exact overlap yet"))
                        st.write(job.get("summary") or "No short description provided.")
                        dates = []
                        if job.get("posted_date"):
                            dates.append("Posted: " + job["posted_date"])
                        if job.get("valid_through"):
                            dates.append("Apply by: " + job["valid_through"])
                        if dates:
                            st.caption(" · ".join(dates))
                    with right:
                        if job.get("url"):
                            st.link_button("View job", job["url"], use_container_width=True)
                        if job.get("apply_url"):
                            st.link_button("Apply", job["apply_url"], use_container_width=True)
            st.caption("Listings are supplied by JobsForce India. Check the employer's posting and application page for the latest status before applying.")
    else:
        st.info("Enter a role or skill and select your filters, then choose Search live jobs.")
    st.caption("Live job search is separate from sample-job recommendations, saved jobs and the application tracker. Existing CareerMatch features and records remain unchanged.")

elif page == "Company Recommendations":
    st.title("Company Recommendations")
    st.write("Companies are ranked using the best skill-match score among their sample job listings.")
    jobs = get_jobs()
    company_scores = {}
    for job in jobs:
        score, matched = score_job(user["skills"], user["interests"], job)
        key = (job["company_id"], job["company_name"], job["industry"])
        if key not in company_scores or score > company_scores[key][0]:
            company_scores[key] = (score, matched, job["title"])
    ranked_companies = sorted(company_scores.items(), key=lambda item: item[1][0], reverse=True)
    if not user["skills"] and not user["interests"]:
        st.warning("Complete My Profile with skills and career interests to personalize company recommendations.")
    for (company_id, company_name, industry), (score, matched, role) in ranked_companies:
        with st.container(border=True):
            left, right = st.columns([4, 1])
            with left:
                st.subheader(company_name)
                st.write(f"**Industry:** {industry}")
                st.write(f"Best matching sample role: {role}")
                st.write("Matched skills: " + (", ".join(matched) if matched else "No exact skill overlap yet"))
            with right:
                st.metric("Company match", f"{score}%")
                if st.button("Shortlist", key=f"company_rec_{company_id}"):
                    shortlist_company(company_id)
                    st.success("Company shortlisted.")

elif page == "Company Explorer":
    st.title("Company Explorer")
    companies = get_companies()
    industries = sorted(set(c["industry"] for c in companies if c["industry"]))
    selected = st.selectbox("Filter by industry", ["All"] + industries)
    for company in companies:
        if selected != "All" and company["industry"] != selected: continue
        with st.container(border=True):
            st.subheader(company["name"])
            st.write(f"**Industry:** {company['industry']}  ·  **Location:** {company['location']}  ·  **Size:** {company['size']}")
            st.write(company["description"])
            st.write(f"Website: {company['website']}")
            if st.button("Shortlist company", key=f"short_{company['id']}"):
                shortlist_company(company["id"])
                st.success("Company shortlisted.")
            with get_conn() as con:
                count = con.execute("SELECT COUNT(*) FROM jobs WHERE company_id=?", (company["id"],)).fetchone()[0]
            st.caption(f"{count} sample job(s) in this prototype")

elif page == "Skill Gap & Roadmap":
    st.title("Skill Gap Analysis & Learning Roadmap")
    jobs = get_jobs()
    if not user["skills"]:
        st.warning("Add your current skills in My Profile first.")
    else:
        target = st.selectbox("Choose a target job", sorted(set(j["title"] for j in jobs)))
        job = next(j for j in jobs if j["title"] == target)
        have = tokens(user["skills"])
        required = [x.strip() for x in job["required_skills"].split(",")]
        matched = [x for x in required if tokens(x) & have]
        missing = [x for x in required if x not in matched]
        a,b = st.columns(2)
        a.metric("Skills matched", len(matched))
        b.metric("Skills to develop", len(missing))
        st.write("**You already have:** " + (", ".join(matched) if matched else "No listed skills matched yet"))
        st.write("**Suggested skills to learn:** " + (", ".join(missing) if missing else "You cover all listed skills!"))
        st.subheader("Suggested learning roadmap")
        roadmap = {
            "Python": ["Python basics and data structures", "Functions, OOP and file handling", "Build a small Python project"],
            "SQL": ["SELECT, WHERE and sorting", "JOIN, GROUP BY and subqueries", "Practice queries on a sample database"],
            "Excel": ["Formulas and formatting", "Pivot tables and charts", "Analyze a small dataset"],
            "Power BI": ["Import and clean data", "Build visuals and dashboards", "Create and publish a sample report"],
            "Machine Learning": ["Statistics and Python libraries", "Regression and classification", "Evaluate a model on a public dataset"],
            "HTML": ["HTML structure and semantic tags", "Forms, tables and links", "Build a multi-page website"],
            "CSS": ["Selectors and box model", "Flexbox and Grid", "Responsive page design"],
            "JavaScript": ["Variables, conditions and loops", "Functions and DOM", "Build an interactive web page"],
            "C++": ["Syntax, loops and functions", "OOP and STL basics", "Solve coding problems"]
        }
        for skill in missing:
            st.markdown(f"**{skill}**")
            steps = roadmap.get(skill, [f"Learn the fundamentals of {skill}", f"Practice with guided exercises", f"Build a small project using {skill}"])
            for i, step in enumerate(steps, 1):
                st.write(f"{i}. {step}")
        st.caption("Roadmap is a general study suggestion; customize it to the job description and your learning pace.")

elif page == "Resume Analyzer":
    st.title("Resume Analyzer")
    st.write("Upload a PDF, DOCX or TXT resume to extract text and compare detected skills with the demo job skill list.")
    upload = st.file_uploader("Upload resume", type=["pdf","docx","txt"])
    if upload:
        resume_text = extract_resume_text(upload)
        if resume_text:
            st.success("Resume text extracted.")
            with st.expander("View extracted text"):
                st.text(resume_text[:10000])
            known = ["Python","SQL","C++","Java","Excel","Power BI","Machine Learning","Statistics","HTML","CSS","JavaScript","React","Git","Linux","Pandas","Communication","Selenium"]
            found = [skill for skill in known if re.search(r"\b" + re.escape(skill) + r"\b", resume_text, re.I)]
            st.subheader("Detected skills")
            st.write(", ".join(found) if found else "No known skills detected. Try a text-based resume.")
            if st.button("Add detected skills to my profile"):
                existing = [x.strip() for x in (user["skills"] or "").split(",") if x.strip()]
                merged = list(dict.fromkeys(existing + found))
                with get_conn() as con:
                    con.execute("UPDATE users SET skills=? WHERE id=?", (", ".join(merged), user["id"]))
                st.success("Profile skills updated.")
        else:
            st.warning("No text could be extracted. The file may be scanned or unsupported.")

elif page == "Saved Jobs":
    st.title("Saved Jobs")
    with get_conn() as con:
        rows = con.execute("""SELECT jobs.*,companies.name AS company_name FROM saved_jobs
                              JOIN jobs ON saved_jobs.job_id=jobs.id JOIN companies ON jobs.company_id=companies.id
                              WHERE saved_jobs.user_id=?""", (user["id"],)).fetchall()
    if not rows: st.info("You have not saved any jobs yet.")
    for job in rows:
        with st.container(border=True):
            st.subheader(job["title"])
            st.write(f"{job['company_name']} · {job['location']} · {job['salary_range']}")
            if st.button("Remove saved job", key=f"remove_{job['id']}"):
                with get_conn() as con:
                    con.execute("DELETE FROM saved_jobs WHERE user_id=? AND job_id=?", (user["id"],job["id"]))
                st.rerun()

elif page == "Application Tracker":
    st.title("Application Tracker")
    with get_conn() as con:
        rows = con.execute("""SELECT applications.*,jobs.title,companies.name AS company_name FROM applications
                              JOIN jobs ON applications.job_id=jobs.id JOIN companies ON jobs.company_id=companies.id
                              WHERE applications.user_id=? ORDER BY applications.id DESC""", (user["id"],)).fetchall()
    if not rows: st.info("No applications tracked yet. Add a job from Job Recommendations.")
    for app in rows:
        with st.container(border=True):
            st.write(f"**{app['title']}** — {app['company_name']}")
            new_status = st.selectbox("Status", ["Interested","Applied","Assessment","Interview","Offer","Rejected"],
                                      index=["Interested","Applied","Assessment","Interview","Offer","Rejected"].index(app["status"]),
                                      key=f"status_{app['id']}")
            note = st.text_input("Notes", value=app["notes"] or "", key=f"note_{app['id']}")
            if st.button("Update", key=f"update_{app['id']}"):
                with get_conn() as con:
                    con.execute("UPDATE applications SET status=?,notes=? WHERE id=?", (new_status,note,app["id"]))
                st.success("Tracker updated.")

elif page == "Compare Companies":
    st.title("Compare Companies")
    companies = get_companies()
    names = [c["name"] for c in companies]
    chosen = st.multiselect("Select up to 3 companies", names, max_selections=3)
    if chosen:
        selected = [c for c in companies if c["name"] in chosen]
        cols = st.columns(len(selected))
        for col, company in zip(cols, selected):
            with col:
                st.subheader(company["name"])
                st.write(f"**Industry:** {company['industry']}")
                st.write(f"**Location:** {company['location']}")
                st.write(f"**Size:** {company['size']}")
                st.write(company["description"])
                with get_conn() as con:
                    jobs_count = con.execute("SELECT COUNT(*) FROM jobs WHERE company_id=?", (company["id"],)).fetchone()[0]
                st.metric("Sample roles", jobs_count)
                st.write(company["website"])

elif page == "Admin / Demo Data":
    st.title("Admin / Demo Data")
    st.warning("This is a student-project demo page, not a production admin console. Demo records are illustrative and are not verified vacancies.")
    st.subheader("Add a sample job")
    companies = get_companies()
    with st.form("add_job"):
        company_map = {c["name"]: c["id"] for c in companies}
        company_name = st.selectbox("Company", list(company_map))
        title = st.text_input("Job title")
        location = st.text_input("Location", "India")
        job_type = st.selectbox("Job type", ["Full-time","Internship","Part-time","Contract"])
        skills = st.text_input("Required skills (comma-separated)")
        qualification = st.text_input("Minimum qualification")
        experience_level = st.selectbox("Experience", ["Fresher","Intern","0–2 years","2+ years"])
        salary = st.text_input("Salary range", "Not specified")
        description = st.text_area("Description")
        if st.form_submit_button("Add sample job"):
            if title.strip() and skills.strip():
                with get_conn() as con:
                    con.execute("""INSERT INTO jobs(company_id,title,location,job_type,required_skills,min_qualification,experience_level,salary_range,description,is_demo)
                                   VALUES(?,?,?,?,?,?,?,?,?,1)""",
                                (company_map[company_name],title,location,job_type,skills,qualification,experience_level,salary,description))
                st.success("Sample job added.")
                st.rerun()
            else:
                st.error("Job title and required skills are compulsory.")
    st.subheader("Database summary")
    with get_conn() as con:
        st.write(f"Users: {con.execute('SELECT COUNT(*) FROM users').fetchone()[0]}")
        st.write(f"Companies: {con.execute('SELECT COUNT(*) FROM companies').fetchone()[0]}")
        st.write(f"Sample jobs: {con.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]}")
