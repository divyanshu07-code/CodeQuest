from flask import Blueprint, render_template, request, redirect, session, flash, clean_url
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from database import get_db

# Organize routes into a neat blueprint module
main_bp = Blueprint('main', __name__)

# --- Authentication Guard Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@main_bp.route("/")
@login_required
def home():
    db = get_db()
    user_id = session["user_id"]

    # Highly optimized aggregate query fetching all 4 metric counts in a single network trip
    stats = db.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN difficulty = 'Easy' THEN 1 ELSE 0 END) as easy,
            SUM(CASE WHEN difficulty = 'Medium' THEN 1 ELSE 0 END) as medium,
            SUM(CASE WHEN difficulty = 'Hard' THEN 1 ELSE 0 END) as hard
        FROM problems 
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    recent = db.execute(
        "SELECT * FROM problems WHERE user_id = ? ORDER BY id DESC LIMIT 10", 
        (user_id,)
    ).fetchall()

    return render_template(
        "dashboard.html",
        total=stats['total'] or 0,
        easy=stats['easy'] or 0,
        medium=stats['medium'] or 0,
        hard=stats['hard'] or 0,
        recent=recent
    )

@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            return "Username and password are required credentials.", 400

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )
            db.commit()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return "That username is already taken.", 400

    return render_template("register.html")

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear() # Securely clears any dead session remnants before writing new cookies
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")

        return "Invalid username or password.", 401

    return render_template("login.html")

@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@main_bp.route("/add-problem", methods=["POST"])
@login_required
def add_problem():
    db = get_db()
    db.execute(
        """
        INSERT INTO problems (user_id, problem_name, platform, difficulty, topic, solved_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session["user_id"],
            request.form.get("problem_name"),
            request.form.get("platform"),
            request.form.get("difficulty"),
            request.form.get("topic"),
            request.form.get("solved_date")
        )
    )
    db.commit()
    return redirect("/")

@main_bp.route("/leaderboard")
def leaderboard():
    db = get_db()
    rankings = db.execute(
        """
        SELECT users.username, COUNT(problems.id) AS solved
        FROM users
        LEFT JOIN problems ON users.id = problems.user_id
        GROUP BY users.id
        ORDER BY solved DESC
        """
    ).fetchall()
    return render_template("leaderboard.html", rankings=rankings)

@main_bp.route("/delete-problem/<int:id>")
@login_required
def delete_problem(id):
    db = get_db()
    # Explicit ownership validation - ensures hackers cannot delete another user's entries
    db.execute("DELETE FROM problems WHERE id = ? AND user_id = ?", (id, session["user_id"]))
    db.commit()
    return redirect("/")