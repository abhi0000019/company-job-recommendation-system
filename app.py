import streamlit as st
import sqlite3
import hashlib
import secrets
import re
from datetime import datetime
from pathlib import Path

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
</style>

""", unsafe_allow_html=True)

user = current_user()
if not user:
    st.title("🎯 CareerMatch")
    st.caption("Company Selection and Job Recommendation System")
    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("Find opportunities that match your skills")
        st.write("Create a profile, explore sample job listings, discover skill gaps and organize your applications in one place.")
        st.info("This academic prototype uses clearly labelled sample/demo job data. It does not verify live vacancies.")
    with right:
        tab1, tab2 = st.tabs(["Login", "Create account"])
        with tab1:
            email = st.text_input("Email address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", type="primary", use_container_width=True):
                if login_user(email, password):
                    st.rerun()
                else:
                    st.error("Invalid email or password.")
        with tab2:
            name = st.text_input("Full name", key="reg_name")
            reg_email = st.text_input("Email address", key="reg_email")
            p1 = st.text_input("Password (minimum 8 characters)", type="password", key="reg_pass")
            p2 = st.text_input("Confirm password", type="password", key="reg_confirm")
            if st.button("Create account", use_container_width=True):
                if not name.strip() or not reg_email.strip():
                    st.error("Please enter your name and email.")
                elif len(p1) < 8:
                    st.error("Password must contain at least 8 characters.")
                elif p1 != p2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = register_user(name, reg_email, p1)
                    (st.success if ok else st.error)(msg)
    st.stop()

# Sidebar navigation
with st.sidebar:
    st.title("🎯 CareerMatch")
    st.write(f"Welcome, **{user['name']}**")
    page = st.radio("Navigation", ["Dashboard", "My Profile", "Job Recommendations", "Company Recommendations", "Company Explorer", "Skill Gap & Roadmap", "Resume Analyzer", "Saved Jobs", "Application Tracker", "Compare Companies", "Admin / Demo Data"])
    if st.button("Logout", use_container_width=True):
        del st.session_state.user_id
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
    st.title("Job Recommendations")
    st.write("Recommendations are ranked using the overlap between your profile skills/interests and each job's required skills.")
    jobs = get_jobs()
    if not user["skills"] and not user["interests"]:
        st.warning("Add skills and career interests in My Profile to get personalized recommendations.")
    ranked = []
    for job in jobs:
        score, matched = score_job(user["skills"], user["interests"], job)
        ranked.append((score, matched, job))
    ranked.sort(key=lambda x: x[0], reverse=True)
    minimum = st.slider("Minimum match score", 0, 100, 0, 5)
    for score, matched, job in ranked:
        if score < minimum: continue
        with st.container(border=True):
            a,b = st.columns([4,1])
            with a:
                st.subheader(job["title"])
                st.write(f"**{job['company_name']}** · {job['location']} · {job['job_type']}")
                st.write(f"Required skills: {job['required_skills']}")
                st.write(f"Qualification: {job['min_qualification']} | Experience: {job['experience_level']}")
                st.write(f"Salary (illustrative): {job['salary_range']}")
                st.caption(job["description"])
                st.caption("Matched skills: " + (", ".join(matched) if matched else "No exact skill overlap yet"))
            with b:
                st.metric("Match", f"{score}%")
                if st.button("Save job", key=f"save_{job['id']}"):
                    save_job(job["id"])
                    st.success("Saved")
                if st.button("Track application", key=f"track_{job['id']}"):
                    with get_conn() as con:
                        con.execute("INSERT INTO applications(user_id,job_id,status,applied_on) VALUES(?,?,?,?)",
                                    (user["id"],job["id"],"Interested",datetime.now().strftime("%Y-%m-%d")))
                    st.success("Added to tracker")

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
