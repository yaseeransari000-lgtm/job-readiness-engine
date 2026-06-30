# Job-Readiness Gap Engine

Resume aur Job Description compare karke match score, missing skills, aur free learning resources deta hai.

## Run karne ka tareeka

1. Dependencies install karo:
   ```
   pip install -r requirements.txt
   ```

2. App run karo:
   ```
   python3 app.py
   ```

3. Browser mein kholo: http://127.0.0.1:5000

Pehli baar /signup pe jaake account banao, fir login karo.

## Project Structure
- `app.py` — Flask app, routes, auth, database
- `skill_matcher.py` — matching engine (resume vs JD)
- `skills_database.json` — known skills ki list (yahan aur skills add kar sakte ho)
- `templates/` — HTML pages
- `static/` — CSS + JS (animations)
- `database.db` — auto-create hoga pehli run pe (SQLite)

## Free Deployment
Render.com ya Railway.app pe free deploy ho sakta hai — GitHub repo connect karo,
build command: `pip install -r requirements.txt`, start command: `python app.py`
