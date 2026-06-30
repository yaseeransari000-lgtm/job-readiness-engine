"""
app.py
-------
Job-Readiness Gap Engine - Main Flask Application

Features:
- Signup/Login (apna simple session-based auth, koi extra library nahi)
- Resume (text ya PDF) vs Job Description match karna
- Match score, missing skills, aur free learning resources dikhana
- History save karna har user ke liye (SQLite database)
"""

import os
import sqlite3
from functools import wraps

import pdfplumber
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from skill_matcher import calculate_match, get_resource_link

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"  # production mein ise env variable se lena

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------- DATABASE SETUP ----------

def get_db():
    """Ek naya database connection deta hai."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows ko dictionary jaisa access karne ke liye
    return conn


def init_db():
    """App start hote hi tables bana deta hai agar already nahi hain."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            match_percent INTEGER NOT NULL,
            job_title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()


# ---------- AUTH HELPER ----------

def login_required(f):
    """Decorator: jo bhi route pe lagao, wahan login zaroori ho jaata hai."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Pehle login karo.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------- AUTH ROUTES ----------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Saare fields bharo.", "error")
            return redirect(url_for("signup"))

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("Ye email already registered hai. Login karo.", "error")
            conn.close()
            return redirect(url_for("login"))

        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash)
        )
        conn.commit()
        conn.close()

        flash("Account ban gaya! Ab login karo.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Email ya password galat hai.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logout ho gaya.", "success")
    return redirect(url_for("login"))


# ---------- MAIN APP ROUTES ----------

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    history = conn.execute(
        "SELECT * FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (session["user_id"],)
    ).fetchall()
    conn.close()
    return render_template("dashboard.html", history=history, name=session.get("user_name"))


@app.route("/check", methods=["POST"])
@login_required
def check():
    job_description = request.form.get("job_description", "").strip()
    job_title = request.form.get("job_title", "Untitled Job").strip()
    resume_text = request.form.get("resume_text", "").strip()

    # Agar PDF upload kiya hai toh usse text nikal lo
    uploaded_file = request.files.get("resume_file")
    if uploaded_file and uploaded_file.filename.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            extracted = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted.append(page_text)
            resume_text = "\n".join(extracted)

    if not resume_text or not job_description:
        flash("Resume aur job description dono chahiye.", "error")
        return redirect(url_for("dashboard"))

    result = calculate_match(resume_text, job_description)

    # Har missing skill ke liye learning resource attach karo
    missing_with_links = [
        {"skill": skill, "link": get_resource_link(skill)}
        for skill in result["missing_skills"]
    ]

    # History mein save karo
    conn = get_db()
    conn.execute(
        "INSERT INTO history (user_id, match_percent, job_title) VALUES (?, ?, ?)",
        (session["user_id"], result["match_percent"], job_title)
    )
    conn.commit()
    conn.close()

    return render_template(
        "result.html",
        match_percent=result["match_percent"],
        matched_skills=result["matched_skills"],
        missing_skills=missing_with_links,
        total_required=result["total_required"],
        job_title=job_title,
        warning=result["warning"]
    )

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
