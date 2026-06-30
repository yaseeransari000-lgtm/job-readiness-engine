"""
app.py
-------
Job-Readiness Gap Engine - Main Flask Application
"""

import os
import sqlite3
from functools import wraps

import pdfplumber
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from skill_matcher import calculate_match, get_resource_link

app = Flask(__name__)
app.secret_key = "change-this-secret-key-in-production"

# Render standard temporary writable folder structure
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except Exception:
        pass


# ---------- DATABASE SETUP ----------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    try:
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
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database error ignored for stability: {e}")


# ---------- AUTH HELPER ----------

def login_required(f):
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

        try:
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
        except Exception:
            flash("Database temporary locked hai, please try again.", "error")
            return redirect(url_for("signup"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        try:
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            conn.close()

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                flash(f"Welcome back, {user['name']}!", "success")
                return redirect(url_for("dashboard"))
        except Exception:
            pass

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
    try:
        conn = get_db()
        history = conn.execute(
            "SELECT * FROM history WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
            (session["user_id"],)
        ).fetchall()
        conn.close()
    except Exception:
        history = []
    return render_template("dashboard.html", history=history, name=session.get("user_name"))


@app.route("/check", methods=["POST"])
@login_required
def check():
    job_description = request.form.get("job_description", "").strip()
    job_title = request.form.get("job_title", "Untitled Job").strip()
    resume_text = request.form.get("resume_text", "").strip()

    uploaded_file = request.files.get("resume_file")
    if uploaded_file and uploaded_file.filename.endswith(".pdf"):
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                extracted = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted.append(page_text)
                resume_text = "\n".join(extracted)
        except Exception:
            flash("PDF file read karne mein dikkhad aayi.", "error")
            return redirect(url_for("dashboard"))

    if not resume_text or not job_description:
        flash("Resume aur job description dono chahiye.", "error")
        return redirect(url_for("dashboard"))

    result = calculate_match(resume_text, job_description)

    missing_with_links = [
        {"skill": skill, "link": get_resource_link(skill)}
        for skill in result["missing_skills"]
    ]

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO history (user_id, match_percent, job_title) VALUES (?, ?, ?)",
            (session["user_id"], result["match_percent"], job_title)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

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
