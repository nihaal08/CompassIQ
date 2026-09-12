"""
CompassIQ — AI-Powered Customer Support Ticket Management System
================================================================
MCA Academic Mini-Project demonstrating:
- Role-Based Access Control (Customer, Agent, Admin)
- AI-Powered Ticket Classification using TF-IDF + Logistic Regression
- SQLite Database with Relational Schema
- Flask Web Application with Clean RESTful Routes

Core Evaluation Flows:
1. Authentication (Auto-approved registration, login, logout)
2. Customer Portal (Create tickets, view history, submit feedback)
3. AI Inference (TF-IDF text classification for category & priority)
4. Agent Portal (Department queues, ticket resolution, replies)
5. Admin Portal (System metrics, category distribution analytics)
"""

import os
import sys
import subprocess
import random
import string
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, g
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from db import query_db, modify_db, init_db_schema
from ai_engine import predict_and_retrieve, load_ai_engine

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize CSRF protection for form security
csrf = CSRFProtect(app)

# ============================================================================
# FLOW 1: AUTHENTICATION (Auto-Approved Registration, Login, Logout)
# ============================================================================

def generate_ticket_id():
    """
    Generates unique alphanumeric ticket ID (e.g. TKT-748921).
    Used for creating identifiable ticket references.
    """
    random_num = ''.join(random.choices(string.digits, k=6))
    return f"TKT-{random_num}"


def get_current_user():
    """
    Retrieves current logged in user from database using session user_id.
    Returns user dictionary or None if not logged in.
    """
    if 'user_id' not in session:
        return None
    try:
        user = query_db(
            "SELECT user_id, full_name, email, role, department, bill_no_product_id, account_status FROM users WHERE user_id = ?",
            (session['user_id'],),
            one=True
        )
        return user
    except Exception as e:
        print(f"[Auth Helper Error] {e}")
        return None


@app.before_request
def load_logged_in_user():
    """
    Flask before_request hook to load current user into Flask's g object.
    This makes user information available across all routes.
    """
    g.user = get_current_user()


def login_required(f):
    """
    Decorator to protect routes that require user authentication.
    Redirects to login page if user is not logged in or not approved.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login'))
        if g.user['account_status'] != 'APPROVED':
            session.clear()
            flash("Your account is not authorized to access this resource.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorator to restrict route access to specific user roles.
    Used for RBAC (Role-Based Access Control) implementation.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user is None:
                flash("Please sign in first.", "warning")
                return redirect(url_for('login'))
            if g.user['role'] not in roles:
                flash("Access denied: You do not have permission to view this portal.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def customer_required(f):
    """Decorator requiring customer role."""
    return login_required(role_required('customer')(f))


def agent_required(f):
    """Decorator requiring agent role."""
    return login_required(role_required('agent')(f))


def admin_required(f):
    """Decorator requiring admin role."""
    return login_required(role_required('admin')(f))


@app.route('/')
def index():
    """
    Root route serving the public landing page.
    - Logged in users see "Go to Dashboard" button in navbar
    - Not logged in users see the full landing page with CTA to login
    """
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration route with auto-approval for streamlined demo flow.
    - GET: Renders registration form
    - POST: Creates new user with APPROVED status (no admin approval needed)
    - Validates input, checks for existing email, hashes password
    """
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Step 1: Read and validate form data
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        bill_no_product_id = request.form.get('bill_no_product_id', '').strip()

        # Form validation
        if not full_name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return render_template('register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html')

        # Step 2: Check for existing user
        existing_user = query_db("SELECT user_id FROM users WHERE email = ?", (email,), one=True)
        if existing_user:
            flash("An account with this email address already exists.", "danger")
            return render_template('register.html')

        # Step 3: Create user with auto-approval
        hashed_password = generate_password_hash(password)

        try:
            modify_db(
                """INSERT INTO users (full_name, email, password_hash, role, department, bill_no_product_id, account_status)
                   VALUES (?, ?, ?, 'customer', 'None', ?, 'APPROVED')""",
                (full_name, email, hashed_password, bill_no_product_id)
            )
            flash(
                "Registration successful! Your account has been automatically approved.",
                "success"
            )
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Registration failed: {e}", "danger")
            return render_template('register.html')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User authentication route.
    - GET: Renders login form
    - POST: Validates credentials, creates session, redirects to role-specific dashboard
    - Checks account status (BANNED users are blocked)
    """
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Step 1: Read and validate credentials
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both email and password.", "warning")
            return render_template('login.html')

        # Step 2: Authenticate user
        user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)

        if not user or not check_password_hash(user['password_hash'], password):
            flash("Invalid email or password. Please verify your credentials.", "danger")
            return render_template('login.html')

        # Step 3: Check account status
        if user['account_status'] == 'BANNED':
            flash("Your account has been suspended by administration. Please contact support.", "danger")
            return render_template('login.html')

        # Step 4: Create session and redirect
        session.clear()
        session['user_id'] = user['user_id']
        session['role'] = user['role']
        session['full_name'] = user['full_name']

        flash(f"Welcome back, {user['full_name']}!", "success")

        # Role-based redirect
        if user['role'] == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif user['role'] == 'agent':
            return redirect(url_for('agent_dashboard'))
        elif user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    User logout route.
    Clears session and redirects to login page.
    """
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('login'))


# ============================================================================
# FLOW 2: CUSTOMER PORTAL (Create Tickets, View History, Submit Feedback)
# ============================================================================

@app.route('/customer/dashboard')
@customer_required
def customer_dashboard():
    """
    Customer dashboard showing all tickets created by the current customer.
    Displays ticket list with agent assignment and status information.
    """
    # Fetch all tickets created by customer with agent details
    tickets = query_db(
        """SELECT t.*, u.full_name as agent_name
           FROM tickets t
           LEFT JOIN users u ON t.assigned_agent_id = u.user_id
           WHERE t.customer_id = ?
           ORDER BY t.created_at DESC""",
        (g.user['user_id'],)
    )
    return render_template('customer_dashboard.html', tickets=tickets)


@app.route('/create_ticket', methods=['POST'])
@app.route('/customer/tickets/create', methods=['POST'])
@customer_required
def create_ticket():
    """
    Ticket creation route with AI-powered classification.
    - Step 1: Read and validate form data (subject, description)
    - Step 2: Call AI engine for category and priority prediction
    - Step 3: Insert ticket with AI predictions into database
    - Step 4: Create initial reply message
    """
    # Step 1: Read and validate form data
    subject = request.form.get('subject', '').strip()
    description = request.form.get('description', '').strip()

    if not subject or not description:
        flash("Subject and Description cannot be empty.", "warning")
        return redirect(url_for('customer_dashboard'))

    # Step 2: AI Inference for category and priority prediction
    ai_result = predict_and_retrieve(subject, description, top_k=3)
    
    predicted_category = ai_result['predicted_category']
    predicted_priority = ai_result['predicted_priority']
    assigned_dept = ai_result['assigned_department']

    ticket_id = generate_ticket_id()

    try:
        # Step 3: Insert ticket with AI predictions
        modify_db(
            """INSERT INTO tickets (ticket_id, customer_id, subject, description,
                                   predicted_category, predicted_priority,
                                   assigned_department, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'Submitted')""",
            (ticket_id, g.user['user_id'], subject, description,
             predicted_category, predicted_priority, assigned_dept)
        )

        # Step 4: Insert initial ticket reply message
        modify_db(
            """INSERT INTO ticket_replies (ticket_id, sender_id, message)
               VALUES (?, ?, ?)""",
            (ticket_id, g.user['user_id'], description)
        )

        flash(f"Ticket {ticket_id} created successfully! Routed to {assigned_dept} team.", "success")

    except Exception as e:
        flash(f"Failed to submit ticket: {e}", "danger")

    return redirect(url_for('customer_dashboard'))


@app.route('/customer/tickets/<ticket_id>')
@customer_required
def view_customer_ticket(ticket_id):
    """
    Customer ticket details endpoint (AJAX).
    Returns ticket information and conversation history in JSON format.
    Used for populating ticket detail modals.
    """
    # Step 1: Fetch ticket with ownership verification
    ticket = query_db(
        """SELECT t.*, u.full_name as agent_name
           FROM tickets t
           LEFT JOIN users u ON t.assigned_agent_id = u.user_id
           WHERE t.ticket_id = ? AND t.customer_id = ?""",
        (ticket_id, g.user['user_id']),
        one=True
    )
    if not ticket:
        return jsonify({
            'success': False,
            'message': 'Ticket not found or unauthorized'
        }), 404

    # Step 2: Fetch conversation replies
    replies = query_db(
        """SELECT r.*, u.full_name as sender_name, u.role as sender_role
           FROM ticket_replies r
           JOIN users u ON r.sender_id = u.user_id
           WHERE r.ticket_id = ?
           ORDER BY r.created_at ASC""",
        (ticket_id,)
    )

    return jsonify({
        'success': True,
        'status': 'success',
        'ticket': ticket,
        'replies': replies,
        'similar_matches': []  # Empty array for API compatibility
    })


@app.route('/customer/tickets/<ticket_id>/reply', methods=['POST'])
@customer_required
def customer_ticket_reply(ticket_id):
    """
    Customer reply submission endpoint (AJAX).
    - Step 1: Validate reply message
    - Step 2: Verify ticket ownership and status
    - Step 3: Insert reply into database
    - Step 4: Return new reply for immediate UI update
    """
    # Step 1: Read and validate message
    message = request.form.get('message', '').strip()
    if not message:
        return jsonify({'success': False, 'message': 'Reply message cannot be empty.'}), 400

    # Step 2: Verify ownership and status
    ticket = query_db(
        "SELECT status FROM tickets WHERE ticket_id = ? AND customer_id = ?",
        (ticket_id, g.user['user_id']),
        one=True
    )
    if not ticket:
        return jsonify({'success': False, 'message': 'Unauthorized or invalid ticket.'}), 403

    if ticket['status'] in ['Resolved', 'Closed']:
        return jsonify({'success': False, 'message': 'This ticket is resolved or closed. Replies are locked.'}), 403

    # Step 3: Insert reply
    modify_db(
        "INSERT INTO ticket_replies (ticket_id, sender_id, message) VALUES (?, ?, ?)",
        (ticket_id, g.user['user_id'], message)
    )
    
    # Step 4: Fetch new reply for UI update
    new_reply = query_db(
        """SELECT r.*, u.full_name as sender_name, u.role as sender_role
           FROM ticket_replies r
           JOIN users u ON r.sender_id = u.user_id
           WHERE r.ticket_id = ? 
           ORDER BY r.created_at DESC LIMIT 1""",
        (ticket_id,),
        one=True
    )
    
    return jsonify({
        'success': True,
        'message': 'Reply sent successfully.',
        'reply': new_reply
    })


@app.route('/customer/tickets/<ticket_id>/feedback', methods=['POST'])
@customer_required
def submit_feedback(ticket_id):
    """
    Customer satisfaction feedback submission.
    - Step 1: Validate rating (1-5 stars)
    - Step 2: Verify ticket is resolved
    - Step 3: Update ticket with satisfaction score and feedback
    """
    # Step 1: Read and validate rating
    score = request.form.get('satisfaction_score', type=int)
    feedback = request.form.get('customer_feedback', '').strip()

    if not score or score < 1 or score > 5:
        flash("Please provide a rating between 1 and 5 stars.", "warning")
        return redirect(url_for('customer_dashboard'))

    # Step 2: Verify ticket status
    ticket = query_db(
        "SELECT status FROM tickets WHERE ticket_id = ? AND customer_id = ?",
        (ticket_id, g.user['user_id']),
        one=True
    )
    if not ticket or ticket['status'] not in ['Resolved', 'Closed']:
        flash("Feedback can only be submitted for resolved tickets.", "danger")
        return redirect(url_for('customer_dashboard'))

    # Step 3: Update ticket with feedback
    modify_db(
        """UPDATE tickets
           SET satisfaction_score = ?, customer_feedback = ?, status = 'Closed'
           WHERE ticket_id = ? AND customer_id = ?""",
        (score, feedback, ticket_id, g.user['user_id'])
    )
    flash("Thank you! Your satisfaction feedback has been recorded.", "success")
    return redirect(url_for('customer_dashboard'))


# ============================================================================
# FLOW 3: AI INFERENCE (Called during ticket creation)
# ============================================================================

# AI inference is handled in ai_engine.py predict_and_retrieve() function
# Called from create_ticket() route above


# ============================================================================
# FLOW 4: AGENT PORTAL (Department Queues, Ticket Resolution, Replies)
# ============================================================================

@app.route('/agent/dashboard')
@agent_required
def agent_dashboard():
    """
    Agent dashboard showing department-specific ticket queue.
    - Filters tickets by department and status
    - Shows summary statistics (total, submitted, in progress, resolved)
    - Prioritizes tickets by predicted priority (Critical > High > Medium > Low)
    """
    agent_dept = g.user['department']
    status_filter = request.args.get('status', 'all')

    # Build dynamic SQL query with optional status filter
    sql = """
        SELECT t.*, u.full_name as customer_name, u.email as customer_email,
               a.full_name as agent_name
        FROM tickets t
        JOIN users u ON t.customer_id = u.user_id
        LEFT JOIN users a ON t.assigned_agent_id = a.user_id
        WHERE t.assigned_department = ?
    """
    params = [agent_dept]

    if status_filter != 'all':
        sql += " AND t.status = ?"
        params.append(status_filter)

    # Order by priority (Critical first) then by creation date
    sql += " ORDER BY CASE t.predicted_priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 ELSE 5 END, t.created_at DESC"

    tickets = query_db(sql, tuple(params))
    
    # Fetch summary statistics for dashboard counters
    counts = query_db(
        """SELECT
            COUNT(*) as total,
            SUM(status = 'Submitted') as count_submitted,
            SUM(status = 'Under Review') as count_under_review,
            SUM(status = 'In Progress') as count_in_progress,
            SUM(status = 'Resolved') as count_resolved
           FROM tickets
           WHERE assigned_department = ?""",
        (agent_dept,),
        one=True
    )

    return render_template(
        'department_dashboard.html',
        tickets=tickets,
        counts=counts or {},
        current_status=status_filter,
        department=agent_dept
    )


@app.route('/agent/tickets/<ticket_id>/details')
@agent_required
def agent_ticket_details(ticket_id):
    """
    Agent ticket details endpoint (AJAX).
    Returns ticket information, conversation history, and AI predictions.
    Used for populating agent workspace modal.
    """
    agent_dept = g.user['department']
    
    # Step 1: Fetch ticket with department verification
    ticket = query_db(
        """SELECT t.*, u.full_name as customer_name, u.email as customer_email,
                  u.bill_no_product_id as customer_product_id,
                  a.full_name as agent_name
           FROM tickets t
           JOIN users u ON t.customer_id = u.user_id
           LEFT JOIN users a ON t.assigned_agent_id = a.user_id
           WHERE t.ticket_id = ? AND (t.assigned_department = ? OR ? = 'Admin')""",
        (ticket_id, agent_dept, g.user['role']),
        one=True
    )
    if not ticket:
        return jsonify({'status': 'error', 'message': 'Ticket not found or unauthorized.'}), 404

    # Step 2: Fetch conversation replies
    replies = query_db(
        """SELECT r.*, u.full_name as sender_name, u.role as sender_role
           FROM ticket_replies r
           JOIN users u ON r.sender_id = u.user_id
           WHERE r.ticket_id = ?
           ORDER BY r.created_at ASC""",
        (ticket_id,)
    )

    return jsonify({
        'status': 'success',
        'ticket': ticket,
        'replies': replies,
        'similar_matches': []  # Empty array for API compatibility
    })


@app.route('/agent/tickets/<ticket_id>/reply', methods=['POST'])
@agent_required
def agent_ticket_reply(ticket_id):
    """
    Agent ticket update endpoint.
    - Step 1: Read reply message, status update, and resolution notes
    - Step 2: Verify ticket belongs to agent's department
    - Step 3: Insert reply if provided
    - Step 4: Update ticket status, assign agent, add resolution notes
    """
    # Step 1: Read form data
    agent_dept = g.user['department']
    message = request.form.get('message', '').strip()
    new_status = request.form.get('status', '').strip()
    resolution_notes = request.form.get('resolution_notes', '').strip()

    if not message and not new_status and not resolution_notes:
        flash("No update provided.", "warning")
        return redirect(url_for('agent_dashboard'))

    # Step 2: Verify ticket scope
    ticket = query_db(
        "SELECT * FROM tickets WHERE ticket_id = ? AND assigned_department = ?",
        (ticket_id, agent_dept),
        one=True
    )
    if not ticket:
        flash("Ticket not found in your department scope.", "danger")
        return redirect(url_for('agent_dashboard'))

    # Step 3: Insert reply if provided
    if message:
        modify_db(
            "INSERT INTO ticket_replies (ticket_id, sender_id, message) VALUES (?, ?, ?)",
            (ticket_id, g.user['user_id'], message)
        )

    # Step 4: Update ticket status and metadata
    update_fields = ["assigned_agent_id = ?"]
    params = [g.user['user_id']]

    if new_status and new_status in ['Submitted', 'Under Review', 'In Progress', 'Resolved', 'Closed']:
        update_fields.append("status = ?")
        params.append(new_status)
        if new_status == 'Resolved':
            update_fields.append("resolved_at = CURRENT_TIMESTAMP")

    if resolution_notes:
        update_fields.append("resolution_notes = ?")
        params.append(resolution_notes)

    params.append(ticket_id)
    modify_db(
        f"UPDATE tickets SET {', '.join(update_fields)} WHERE ticket_id = ?",
        tuple(params)
    )

    flash(f"Ticket {ticket_id} updated successfully.", "success")
    return redirect(url_for('agent_dashboard'))


# ============================================================================
# FLOW 5: ADMIN PORTAL (System Metrics, Category Distribution Analytics)
# ============================================================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """
    Admin dashboard with system metrics and category distribution analytics.
    - Step 1: Calculate core metrics (Total Tickets, Open Tickets, Resolved Tickets)
    - Step 2: Fetch category distribution data for Chart.js visualization
    - Returns simplified 3-card metrics + 1 category chart
    """
    # Step 1: Calculate core metrics
    total_tickets = query_db("SELECT COUNT(*) as count FROM tickets", one=True)['count']
    resolved_tickets = query_db("SELECT COUNT(*) as count FROM tickets WHERE status IN ('Resolved', 'Closed')", one=True)['count']

    # Step 2: Fetch category distribution for analytics
    dept_stats = query_db(
        """SELECT predicted_category as assigned_department, COUNT(*) as count
           FROM tickets
           GROUP BY predicted_category"""
    )

    # Convert chart data for JSON rendering in Chart.js
    dept_labels = [row['assigned_department'] for row in dept_stats]
    dept_data = [row['count'] for row in dept_stats]

    return render_template(
        'admin_dashboard.html',
        metrics={
            'total_tickets': total_tickets,
            'resolved_tickets': resolved_tickets
        },
        dept_labels=dept_labels,
        dept_data=dept_data
    )


# Legacy admin routes (kept for API compatibility but not used in simplified UI)
@app.route('/admin/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    """Legacy user approval route (not used with auto-approval)."""
    user = query_db("SELECT role, department FROM users WHERE user_id = ?", (user_id,), one=True)
    
    if user and user['role'] == 'agent' and (not user['department'] or user['department'] == 'None'):
        default_dept = request.form.get('department', 'Technical')
        modify_db("UPDATE users SET account_status = 'APPROVED', department = ? WHERE user_id = ?", (default_dept, user_id))
        flash(f"User ID #{user_id} approved successfully and assigned to {default_dept} department.", "success")
    else:
        modify_db("UPDATE users SET account_status = 'APPROVED' WHERE user_id = ?", (user_id,))
        flash(f"User ID #{user_id} approved successfully.", "success")
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/<int:user_id>/reject', methods=['POST'])
@admin_required
def reject_user(user_id):
    """Legacy user rejection route (not used with auto-approval)."""
    modify_db("UPDATE users SET account_status = 'REJECTED' WHERE user_id = ?", (user_id,))
    flash(f"User ID #{user_id} registration rejected.", "warning")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/<int:user_id>/ban', methods=['POST'])
@admin_required
def ban_user(user_id):
    """Legacy user ban route (not used in simplified UI)."""
    modify_db("UPDATE users SET account_status = 'BANNED' WHERE user_id = ?", (user_id,))
    flash(f"User ID #{user_id} has been banned from the system.", "danger")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/tickets/<ticket_id>/close', methods=['POST'])
@admin_required
def admin_close_ticket(ticket_id):
    """Legacy admin ticket closure route (not used in simplified UI)."""
    modify_db(
        "UPDATE tickets SET status = 'Closed', resolved_at = CURRENT_TIMESTAMP, resolution_notes = 'Closed by Administrator security audit.' WHERE ticket_id = ?",
        (ticket_id,)
    )
    flash(f"Ticket {ticket_id} closed by Admin.", "info")
    return redirect(url_for('admin_dashboard'))


# ============================================================================
# CLI COMMANDS
# ============================================================================

@app.cli.command("init-db")
def init_db_command():
    """
    CLI command to initialize database schema.
    Usage: flask init-db
    """
    try:
        init_db_schema()
        print("CompassIQ database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")


# ============================================================================
# APPLICATION STARTUP
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print(" COMPASSIQ — AI-POWERED SUPPORT INTELLIGENCE PLATFORM")
    print("=" * 70)

    # Step 1: Initialize database schema
    try:
        init_db_schema()
    except Exception as e:
        print(f"[CompassIQ DB Warning] Database initialization error: {e}")

    # Step 2: Verify ML model artifacts (3 models for fast startup)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(base_dir, 'models')
    os.makedirs(models_dir, exist_ok=True)

    required_models = [
        'tfidf_vectorizer.joblib',
        'category_model.joblib',
        'priority_model.joblib'
    ]

    missing_models = [m for m in required_models if not os.path.exists(os.path.join(models_dir, m))]

    if missing_models:
        print(f"[CompassIQ ML] Missing model artifacts: {missing_models}")
        print("[CompassIQ ML] Launching training pipeline via train_model.py...")
        train_script = os.path.join(base_dir, 'train_model.py')

        try:
            result = subprocess.run([sys.executable, train_script], check=True)
            print("[CompassIQ ML] Model training completed successfully.")
        except Exception as e:
            print(f"[CompassIQ ML Error] Training pipeline failed: {e}")
    else:
        print("[CompassIQ ML] All 3 serialized model artifacts verified.")

    # Step 3: Load AI engine models
    try:
        load_ai_engine()
    except Exception as e:
        print(f"[AI Engine Startup] Warning: {e}")

    # Step 4: Start Flask server with optimized settings
    print("\n[CompassIQ] Booting server on http://127.0.0.1:5000 (debug=True, use_reloader=False)...")
    print("[CompassIQ] File watcher disabled to prevent OneDrive sync conflicts.")
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)
