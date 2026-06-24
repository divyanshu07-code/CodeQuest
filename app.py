from flask import Flask, render_template, request, redirect, session, g, jsonify, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
DATABASE = os.getenv('DATABASE_PATH', 'codequest.db')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Constants ---
VALID_DIFFICULTIES = ['Easy', 'Medium', 'Hard']
VALID_PLATFORMS = ['LeetCode', 'CodeForces', 'HackerRank', 'AtCoder', 'Other']
MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 20
MIN_PASSWORD_LENGTH = 6

# --- Validation Functions ---

def validate_username(username):
    """Validate username format."""
    if not username or len(username) < MIN_USERNAME_LENGTH or len(username) > MAX_USERNAME_LENGTH:
        return False, f"Username must be {MIN_USERNAME_LENGTH}-{MAX_USERNAME_LENGTH} characters"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscore, and hyphen"
    return True, "Valid"

def validate_password(password):
    """Validate password strength."""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    return True, "Valid"

def validate_problem_name(name):
    """Validate problem name."""
    if not name or len(name) > 200:
        return False
    return True

def validate_difficulty(difficulty):
    """Validate difficulty level."""
    return difficulty in VALID_DIFFICULTIES

def validate_platform(platform):
    """Validate platform."""
    return platform in VALID_PLATFORMS

def validate_date(date_str):
    """Validate date format."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# --- Database Management ---

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Closes the database automatically at the end of every request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database schemas safely within the application context."""
    with app.app_context():
        db = get_db()
        
        try:
            db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
            """)

            db.execute("""
            CREATE TABLE IF NOT EXISTS problems(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                problem_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                topic TEXT,
                solved_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            db.execute("""
            CREATE TABLE IF NOT EXISTS contests(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                contest_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                rank INTEGER,
                rating_change INTEGER,
                contest_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """)

            db.execute("""
            CREATE TABLE IF NOT EXISTS problem_stats(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total_solved INTEGER DEFAULT 0,
                easy_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                hard_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id)
            )
            """)

            db.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise

# --- Authentication Guard Decorator ---

def login_required(f):
    """Decorator to protect routes from unauthorized guest access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator for future admin functionality."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or not session.get("is_admin"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# --- Application Routes ---

@app.route("/")
@login_required
def home():
    """Dashboard with user statistics."""
    try:
        db = get_db()
        user_id = session["user_id"]

        # Fetch stats
        total = db.execute(
            "SELECT COUNT(*) FROM problems WHERE user_id=?", 
            (user_id,)
        ).fetchone()[0]
        
        easy = db.execute(
            "SELECT COUNT(*) FROM problems WHERE user_id=? AND difficulty=?", 
            (user_id, 'Easy')
        ).fetchone()[0]
        
        medium = db.execute(
            "SELECT COUNT(*) FROM problems WHERE user_id=? AND difficulty=?", 
            (user_id, 'Medium')
        ).fetchone()[0]
        
        hard = db.execute(
            "SELECT COUNT(*) FROM problems WHERE user_id=? AND difficulty=?", 
            (user_id, 'Hard')
        ).fetchone()[0]
        
        # Recent problems with pagination
        recent = db.execute(
            "SELECT * FROM problems WHERE user_id=? ORDER BY solved_date DESC, id DESC LIMIT 10", 
            (user_id,)
        ).fetchall()

        # Platform statistics
        platform_stats = db.execute(
            """SELECT platform, COUNT(*) as count FROM problems 
               WHERE user_id=? GROUP BY platform""",
            (user_id,)
        ).fetchall()

        return render_template(
            "dashboard.html",
            username=session.get("username"),
            total=total,
            easy=easy,
            medium=medium,
            hard=hard,
            recent=recent,
            platform_stats=platform_stats
        )
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        flash("An error occurred loading your dashboard", "error")
        return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register new user."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        valid, msg = validate_username(username)
        if not valid:
            flash(msg, "error")
            return render_template("register.html"), 400

        valid, msg = validate_password(password)
        if not valid:
            flash(msg, "error")
            return render_template("register.html"), 400

        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("register.html"), 400

        hashed_password = generate_password_hash(password)
        db = get_db()

        try:
            db.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )
            db.commit()
            logger.info(f"New user registered: {username}")
            flash("Registration successful! Please log in.", "success")
            return redirect("/login")
        except sqlite3.IntegrityError:
            logger.warning(f"Registration attempt with existing username: {username}")
            flash("Username already exists. Choose another.", "error")
            return render_template("register.html"), 400
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash("An error occurred during registration", "error")
            return render_template("register.html"), 500

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login user."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password required", "error")
            return render_template("login.html"), 400

        try:
            db = get_db()
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

            if user and check_password_hash(user["password"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                
                # Update last login
                db.execute(
                    "UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?",
                    (user["id"],)
                )
                db.commit()
                
                logger.info(f"User logged in: {username}")
                flash(f"Welcome back, {username}!", "success")
                return redirect("/")

            logger.warning(f"Failed login attempt for username: {username}")
            flash("Invalid username or password", "error")
            return render_template("login.html"), 401
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash("An error occurred during login", "error")
            return render_template("login.html"), 500

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logout user."""
    username = session.get("username")
    session.clear()
    logger.info(f"User logged out: {username}")
    flash("You have been logged out.", "info")
    return redirect("/login")


@app.route("/profile")
@login_required
def profile():
    """User profile page."""
    try:
        db = get_db()
        user_id = session["user_id"]
        
        user = db.execute(
            "SELECT username, created_at, last_login FROM users WHERE id=?",
            (user_id,)
        ).fetchone()

        stats = db.execute(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN difficulty='Easy' THEN 1 ELSE 0 END) as easy,
                SUM(CASE WHEN difficulty='Medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN difficulty='Hard' THEN 1 ELSE 0 END) as hard
             FROM problems WHERE user_id=?""",
            (user_id,)
        ).fetchone()

        return render_template("profile.html", user=user, stats=stats)
    except Exception as e:
        logger.error(f"Error loading profile: {str(e)}")
        flash("Error loading profile", "error")
        return redirect("/")


@app.route("/add-problem", methods=["GET", "POST"])
@login_required
def add_problem():
    """Add new problem."""
    if request.method == "POST":
        try:
            problem_name = request.form.get("problem_name", "").strip()
            platform = request.form.get("platform", "").strip()
            difficulty = request.form.get("difficulty", "").strip()
            topic = request.form.get("topic", "").strip()
            solved_date = request.form.get("solved_date", "").strip()

            # Validation
            if not validate_problem_name(problem_name):
                flash("Invalid problem name", "error")
                return redirect("/add-problem")

            if not validate_platform(platform):
                flash("Invalid platform", "error")
                return redirect("/add-problem")

            if not validate_difficulty(difficulty):
                flash("Invalid difficulty", "error")
                return redirect("/add-problem")

            if not validate_date(solved_date):
                flash("Invalid date format (use YYYY-MM-DD)", "error")
                return redirect("/add-problem")

            db = get_db()
            db.execute(
                """INSERT INTO problems 
                   (user_id, problem_name, platform, difficulty, topic, solved_date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session["user_id"], problem_name, platform, difficulty, topic, solved_date)
            )
            db.commit()
            logger.info(f"Problem added by user {session['user_id']}: {problem_name}")
            flash("Problem added successfully!", "success")
            return redirect("/")
        except Exception as e:
            logger.error(f"Error adding problem: {str(e)}")
            flash("Error adding problem", "error")
            return redirect("/add-problem")

    return render_template("add_problem.html", 
                         difficulties=VALID_DIFFICULTIES,
                         platforms=VALID_PLATFORMS)


@app.route("/edit-problem/<int:problem_id>", methods=["GET", "POST"])
@login_required
def edit_problem(problem_id):
    """Edit existing problem."""
    try:
        db = get_db()
        problem = db.execute(
            "SELECT * FROM problems WHERE id=? AND user_id=?",
            (problem_id, session["user_id"])
        ).fetchone()

        if not problem:
            flash("Problem not found or unauthorized", "error")
            return redirect("/")

        if request.method == "POST":
            problem_name = request.form.get("problem_name", "").strip()
            platform = request.form.get("platform", "").strip()
            difficulty = request.form.get("difficulty", "").strip()
            topic = request.form.get("topic", "").strip()
            solved_date = request.form.get("solved_date", "").strip()

            # Validation
            if not validate_problem_name(problem_name):
                flash("Invalid problem name", "error")
                return redirect(f"/edit-problem/{problem_id}")

            if not validate_platform(platform):
                flash("Invalid platform", "error")
                return redirect(f"/edit-problem/{problem_id}")

            if not validate_difficulty(difficulty):
                flash("Invalid difficulty", "error")
                return redirect(f"/edit-problem/{problem_id}")

            if not validate_date(solved_date):
                flash("Invalid date format", "error")
                return redirect(f"/edit-problem/{problem_id}")

            db.execute(
                """UPDATE problems 
                   SET problem_name=?, platform=?, difficulty=?, topic=?, 
                       solved_date=?, updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND user_id=?""",
                (problem_name, platform, difficulty, topic, solved_date, 
                 problem_id, session["user_id"])
            )
            db.commit()
            logger.info(f"Problem {problem_id} updated by user {session['user_id']}")
            flash("Problem updated successfully!", "success")
            return redirect("/")

        return render_template("edit_problem.html", 
                             problem=problem,
                             difficulties=VALID_DIFFICULTIES,
                             platforms=VALID_PLATFORMS)
    except Exception as e:
        logger.error(f"Error editing problem: {str(e)}")
        flash("Error editing problem", "error")
        return redirect("/")


@app.route("/leaderboard")
def leaderboard():
    """Global leaderboard."""
    try:
        db = get_db()
        
        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page

        rankings = db.execute(
            """SELECT users.id, users.username, COUNT(problems.id) AS solved
               FROM users
               LEFT JOIN problems ON users.id = problems.user_id
               GROUP BY users.id
               ORDER BY solved DESC
               LIMIT ? OFFSET ?""",
            (per_page, offset)
        ).fetchall()

        total_users = db.execute("SELECT COUNT(DISTINCT id) FROM users").fetchone()[0]
        total_pages = (total_users + per_page - 1) // per_page

        return render_template("leaderboard.html", 
                             rankings=rankings,
                             page=page,
                             total_pages=total_pages)
    except Exception as e:
        logger.error(f"Error loading leaderboard: {str(e)}")
        flash("Error loading leaderboard", "error")
        return render_template("leaderboard.html", rankings=[], page=1, total_pages=1)


@app.route("/user/<username>")
def user_profile(username):
    """Public user profile."""
    try:
        db = get_db()
        user = db.execute("SELECT id, username FROM users WHERE username=?", (username,)).fetchone()

        if not user:
            flash("User not found", "error")
            return redirect("/leaderboard")

        stats = db.execute(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN difficulty='Easy' THEN 1 ELSE 0 END) as easy,
                SUM(CASE WHEN difficulty='Medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN difficulty='Hard' THEN 1 ELSE 0 END) as hard
             FROM problems WHERE user_id=?""",
            (user["id"],)
        ).fetchone()

        problems = db.execute(
            "SELECT * FROM problems WHERE user_id=? ORDER BY solved_date DESC LIMIT 20",
            (user["id"],)
        ).fetchall()

        return render_template("user_profile.html", 
                             user=user, 
                             stats=stats, 
                             problems=problems)
    except Exception as e:
        logger.error(f"Error loading user profile: {str(e)}")
        flash("Error loading user profile", "error")
        return redirect("/leaderboard")


@app.route("/delete-problem/<int:problem_id>", methods=["POST"])
@login_required
def delete_problem(problem_id):
    """Delete problem (only owner)."""
    try:
        db = get_db()
        result = db.execute(
            "DELETE FROM problems WHERE id=? AND user_id=?",
            (problem_id, session["user_id"])
        )
        
        if result.rowcount == 0:
            flash("Problem not found or unauthorized", "error")
        else:
            db.commit()
            logger.info(f"Problem {problem_id} deleted by user {session['user_id']}")
            flash("Problem deleted successfully!", "success")
    except Exception as e:
        logger.error(f"Error deleting problem: {str(e)}")
        flash("Error deleting problem", "error")

    return redirect("/")


@app.route("/add-contest", methods=["GET", "POST"])
@login_required
def add_contest():
    """Add contest participation."""
    if request.method == "POST":
        try:
            contest_name = request.form.get("contest_name", "").strip()
            platform = request.form.get("platform", "").strip()
            rank = request.form.get("rank", "")
            rating_change = request.form.get("rating_change", "")
            contest_date = request.form.get("contest_date", "").strip()

            if not contest_name or not platform or not contest_date:
                flash("Contest name, platform, and date are required", "error")
                return redirect("/add-contest")

            if not validate_date(contest_date):
                flash("Invalid date format", "error")
                return redirect("/add-contest")

            db = get_db()
            db.execute(
                """INSERT INTO contests 
                   (user_id, contest_name, platform, rank, rating_change, contest_date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (session["user_id"], contest_name, platform, rank or None, 
                 rating_change or None, contest_date)
            )
            db.commit()
            logger.info(f"Contest added by user {session['user_id']}: {contest_name}")
            flash("Contest added successfully!", "success")
            return redirect("/")
        except Exception as e:
            logger.error(f"Error adding contest: {str(e)}")
            flash("Error adding contest", "error")
            return redirect("/add-contest")

    return render_template("add_contest.html", platforms=VALID_PLATFORMS)


# --- Error Handlers ---

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    logger.warning(f"404 error: {request.path}")
    return render_template("error.html", error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"500 error: {str(error)}")
    return render_template("error.html", error="Internal server error"), 500

@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 errors."""
    return render_template("error.html", error="Access forbidden"), 403


if __name__ == "__main__":
    init_db()
    # Never use debug=True in production
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)