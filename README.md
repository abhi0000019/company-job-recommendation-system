# Company Selection and Job Recommendation System

A BCA Data Science & AI academic project built with Python, Streamlit and SQLite.

## Main features
- User registration and login with salted PBKDF2-HMAC-SHA256 password hashes
- Profile management (degree, specialization, graduation year, skills and interests)
- Skill-overlap job recommendation scoring
- Company explorer and company shortlisting
- Skill gap analysis and a suggested learning roadmap
- Resume text extraction from PDF, DOCX and TXT
- Save jobs and track application status
- Compare up to three companies
- Add illustrative sample jobs

> **Important:** The preloaded companies and job listings are demonstration data for the academic prototype. They are not verified live vacancies, and salary ranges are illustrative. Do not treat them as confirmed openings.

## Requirements
- Windows 10/11
- Python 3.10 or newer
- VS Code (recommended)

## Run in VS Code (Windows)

1. Extract `Company_Job_Recommendation_System.zip`.
2. Open the extracted folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   py -m venv venv
   ```

5. Activate it:

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run this once in the current terminal:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\venv\Scripts\Activate.ps1
   ```

6. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. Start the app:

   ```powershell
   streamlit run app.py
   ```

8. Streamlit will show a local URL, usually `http://localhost:8501`. Open it in your browser.
9. Select **Create account**, register, log in, and complete **My Profile**.

## Database
- SQLite database is created automatically as `database.db` on first run.
- Tables: users, companies, jobs, saved_jobs, shortlisted_companies and applications.
- To reset the demo database, stop the app and delete `database.db`. It will be recreated on the next run.

## Recommendation method
The prototype tokenizes the skills and interests in the user's profile and compares them with the required skills for each job. The displayed match score is:

`(number of matched required skills / number of required skills) × 100`

This is an explainable baseline recommender, not a trained predictive model. A future version can use TF-IDF, cosine similarity, job APIs and verified vacancy feeds.

## Security and production limitations
- Passwords are hashed with PBKDF2-HMAC-SHA256 and a per-user random salt.
- This is an educational prototype. Before public deployment, add email verification, rate limiting, password reset, CSRF/session hardening, authorization roles, secure secrets management, file-size limits, malware scanning and privacy/retention controls.
- The current Admin / Demo Data page is intentionally a demo data-entry page, not a role-protected production admin panel.
- Resume parsing works best with text-based PDFs and DOCX files. Scanned PDFs require OCR, which is not included.

## Suggested future enhancements
- Verified job API integration and vacancy expiry
- More advanced NLP recommendation model
- Admin roles and moderation
- Resume-to-job semantic matching
- Email alerts and interview calendar
- Deployment to Streamlit Community Cloud
