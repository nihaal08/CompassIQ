"""
CompassIQ — AI-Powered Customer Support Ticket Management System
================================================================
Flask Web Application Backend providing Role-Based Access Control,
Customer Ticket Lifecycle Management, Department Agent Workspace with
AI recommendations, and Administrator Fraud & Analytics Controls.
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
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from db import query_db, modify_db, init_db_schema
from ai_engine import predict_and_retrieve, load_ai_engine

app = Flask(__name__)
app.config.from_object(Config)

# Initialize AI engine on startup (if models are already present)
try:
    load_ai_engine()
except Exception as e:
    print(f"[AI Engine Startup] Warning: {e}")


# ============================================================================
# HELPER FUNCTIONS & DECORATORS
# ============================================================================

def generate_ticket_id():
    """Generates unique alphanumeric ticket ID (e.g. TKT-748921)."""
    random_num = ''.join(random.choices(string.digits, k=6))
    return f"TKT-{random_num}"


def get_current_user():
    """Retrieves current logged in user from database using session user_id."""
    if 'user_id' not in session:
        return None
    try:
        user = query_db(
            "SELECT user_id, full_name, email, role, department, bill_no_product_id, account_status FROM users WHERE user_id = %s",
            (session['user_id'],),
            one=True
        )
        return user
    except Exception as e:
        print(f"[Auth Helper Error] {e}")
        return None


@app.before_request
def load_logged_in_user():
    g.user = get_current_user()


def login_required(f):
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
    return login_required(role_required('customer')(f))


def agent_required(f):
    return login_required(role_required('agent')(f))


def admin_required(f):
    return login_required(role_required('admin')(f))


# ============================================================================
# PUBLIC & AUTHENTICATION ROUTES
# ============================================================================

@app.route('/')
def index():
    if g.user:
        if g.user['role'] == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif g.user['role'] == 'agent':
            return redirect(url_for('agent_dashboard'))
        elif g.user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        bill_no_product_id = request.form.get('bill_no_product_id', '').strip()

        if not full_name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return render_template('register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html')

        # Check existing user
        existing_user = query_db("SELECT user_id FROM users WHERE email = %s", (email,), one=True)
        if existing_user:
            flash("An account with this email address already exists.", "danger")
            return render_template('register.html')

        hashed_password = generate_password_hash(password)

        try:
            # Customers are created with account_status = 'PENDING'
            modify_db(
                """INSERT INTO users (full_name, email, password_hash, role, department, bill_no_product_id, account_status)
                   VALUES (%s, %s, %s, 'customer', 'None', %s, 'PENDING')""",
                (full_name, email, hashed_password, bill_no_product_id)
            )
            flash(
                "Registration submitted successfully! Your account is pending admin approval. Please wait for verification.",
                "pending_approval"
            )
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Registration failed: {e}", "danger")
            return render_template('register.html')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both email and password.", "warning")
            return render_template('login.html')

        user = query_db("SELECT * FROM users WHERE email = %s", (email,), one=True)

        if not user or not check_password_hash(user['password_hash'], password):
            flash("Invalid email or password. Please verify your credentials.", "danger")
            return render_template('login.html')

        # Account Status Check Guard
        if user['account_status'] == 'PENDING':
            flash("Your account is pending admin approval. Please wait for verification.", "pending_approval")
            return render_template('login.html')

        if user['account_status'] == 'BANNED':
            flash("Your account has been suspended by administration. Please contact support.", "danger")
            return render_template('login.html')

        if user['account_status'] == 'REJECTED':
            flash("Your account registration was declined by administration.", "danger")
            return render_template('login.html')

        # Login Approved User
        session.clear()
        session['user_id'] = user['user_id']
        session['role'] = user['role']
        session['full_name'] = user['full_name']

        flash(f"Welcome back, {user['full_name']}!", "success")

        if user['role'] == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif user['role'] == 'agent':
            return redirect(url_for('agent_dashboard'))
        elif user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('login'))


# ============================================================================
# CUSTOMER PORTAL
# ============================================================================

@app.route('/customer/dashboard')
@customer_required
def customer_dashboard():
    # Fetch all tickets created by customer
    tickets = query_db(
        """SELECT t.*, u.full_name as agent_name
           FROM tickets t
           LEFT JOIN users u ON t.assigned_agent_id = u.user_id
           WHERE t.customer_id = %s
           ORDER BY t.created_at DESC""",
        (g.user['user_id'],)
    )
    return render_template('customer_dashboard.html', tickets=tickets)


@app.route('/customer/tickets/create', methods=['POST'])
@customer_required
def create_ticket():
    subject = request.form.get('subject', '').strip()
    description = request.form.get('description', '').strip()

    if not subject or not description:
        flash("Subject and Description cannot be empty.", "warning")
        return redirect(url_for('customer_dashboard'))

    # Run AI inference and cosine similarity retrieval
    ai_result = predict_and_retrieve(subject, description, top_k=3)
    
    predicted_category = ai_result['predicted_category']
    predicted_priority = ai_result['predicted_priority']
    assigned_dept = ai_result['assigned_department']
    similar_matches = ai_result.get('similar_tickets', [])

    ticket_id = generate_ticket_id()

    try:
        # 1. Insert ticket
        modify_db(
            """INSERT INTO tickets (ticket_id, customer_id, subject, description,
                                   predicted_category, predicted_priority,
                                   assigned_department, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Submitted')""",
            (ticket_id, g.user['user_id'], subject, description,
             predicted_category, predicted_priority, assigned_dept)
        )

        # 2. Insert initial ticket reply message
        modify_db(
            """INSERT INTO ticket_replies (ticket_id, sender_id, message)
               VALUES (%s, %s, %s)""",
            (ticket_id, g.user['user_id'], description)
        )

        # 3. Store Top-3 similar matches in DB (for agent recommendation workspace)
        for match in similar_matches:
            modify_db(
                """INSERT INTO ticket_similar_matches
                   (ticket_id, similar_ticket_ref_id, similarity_score, similar_subject, similar_description, historical_resolution_hours)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (ticket_id,
                 match['similar_ticket_ref_id'],
                 match['similarity_score'],
                 match['similar_subject'],
                 match['similar_description'],
                 match.get('historical_resolution_hours'))
            )

        if predicted_category == 'Fraud':
            flash("Your ticket has been submitted and escalated for administrative review.", "info")
        else:
            flash(f"Ticket {ticket_id} created successfully! Routed to {assigned_dept} team.", "success")

    except Exception as e:
        flash(f"Failed to submit ticket: {e}", "danger")

    return redirect(url_for('customer_dashboard'))


@app.route('/customer/tickets/<ticket_id>')
@customer_required
def view_customer_ticket(ticket_id):
    ticket = query_db(
        """SELECT t.*, u.full_name as agent_name
           FROM tickets t
           LEFT JOIN users u ON t.assigned_agent_id = u.user_id
           WHERE t.ticket_id = %s AND t.customer_id = %s""",
        (ticket_id, g.user['user_id']),
        one=True
    )
    if not ticket:
        flash("Ticket not found or unauthorized.", "danger")
        return redirect(url_for('customer_dashboard'))

    # Fetch conversation replies
    replies = query_db(
        """SELECT r.*, u.full_name as sender_name, u.role as sender_role
           FROM ticket_replies r
           JOIN users u ON r.sender_id = u.user_id
           WHERE r.ticket_id = %s
           ORDER BY r.created_at ASC""",
        (ticket_id,)
    )

    return jsonify({
        'status': 'success',
        'ticket': ticket,
        'replies': replies
    })


@app.route('/customer/tickets/<ticket_id>/reply', methods=['POST'])
@customer_required
def customer_ticket_reply(ticket_id):
    message = request.form.get('message', '').strip()
    if not message:
        flash("Reply message cannot be empty.", "warning")
        return redirect(url_for('customer_dashboard'))

    # Verify ownership
    ticket = query_db(
        "SELECT status FROM tickets WHERE ticket_id = %s AND customer_id = %s",
        (ticket_id, g.user['user_id']),
        one=True
    )
    if not ticket:
        flash("Unauthorized or invalid ticket.", "danger")
        return redirect(url_for('customer_dashboard'))

    if ticket['status'] in ['Resolved', 'Closed']:
        flash("This ticket is resolved or closed. Replies are locked.", "warning")
        return redirect(url_for('customer_dashboard'))

    modify_db(
        "INSERT INTO ticket_replies (ticket_id, sender_id, message) VALUES (%s, %s, %s)",
        (ticket_id, g.user['user_id'], message)
    )
    flash("Reply sent successfully.", "success")
    return redirect(url_for('customer_dashboard'))


@app.route('/customer/tickets/<ticket_id>/feedback', methods=['POST'])
@customer_required
def submit_feedback(ticket_id):
    score = request.form.get('satisfaction_score', type=int)
    feedback = request.form.get('customer_feedback', '').strip()

    if not score or score < 1 or score > 5:
        flash("Please provide a rating between 1 and 5 stars.", "warning")
        return redirect(url_for('customer_dashboard'))

    ticket = query_db(
        "SELECT status FROM tickets WHERE ticket_id = %s AND customer_id = %s",
        (ticket_id, g.user['user_id']),
        one=True
    )
    if not ticket or ticket['status'] not in ['Resolved', 'Closed']:
        flash("Feedback can only be submitted for resolved tickets.", "danger")
        return redirect(url_for('customer_dashboard'))

    modify_db(
        """UPDATE tickets
           SET satisfaction_score = %s, customer_feedback = %s, status = 'Closed'
           WHERE ticket_id = %s AND customer_id = %s""",
        (score, feedback, ticket_id, g.user['user_id'])
    )
    flash("Thank you! Your satisfaction feedback has been recorded.", "success")
    return redirect(url_for('customer_dashboard'))


# ============================================================================
# DEPARTMENT AGENT PORTAL
# ============================================================================

@app.route('/agent/dashboard')
@agent_required
def agent_dashboard():
    agent_dept = g.user['department']
    status_filter = request.args.get('status', 'all')

    sql = """
        SELECT t.*, u.full_name as customer_name, u.email as customer_email,
               a.full_name as agent_name
        FROM tickets t
        JOIN users u ON t.customer_id = u.user_id
        LEFT JOIN users a ON t.assigned_agent_id = a.user_id
        WHERE t.assigned_department = %s
    """
    params = [agent_dept]

    if status_filter != 'all':
        sql += " AND t.status = %s"
        params.append(status_filter)

    sql += " ORDER BY FIELD(t.predicted_priority, 'Critical', 'High', 'Medium', 'Low'), t.created_at DESC"

    tickets = query_db(sql, tuple(params))
    
    # Summary stats for agent badge counters
    counts = query_db(
        """SELECT
            COUNT(*) as total,
            SUM(status = 'Submitted') as count_submitted,
            SUM(status = 'Under Review') as count_under_review,
            SUM(status = 'In Progress') as count_in_progress,
            SUM(status = 'Resolved') as count_resolved
           FROM tickets
           WHERE assigned_department = %s""",
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
    agent_dept = g.user['department']
    
    ticket = query_db(
        """SELECT t.*, u.full_name as customer_name, u.email as customer_email,
                  u.bill_no_product_id as customer_product_id,
                  a.full_name as agent_name
           FROM tickets t
           JOIN users u ON t.customer_id = u.user_id
           LEFT JOIN users a ON t.assigned_agent_id = a.user_id
           WHERE t.ticket_id = %s AND (t.assigned_department = %s OR %s = 'Admin')""",
        (ticket_id, agent_dept, g.user['role']),
        one=True
    )
    if not ticket:
        return jsonify({'status': 'error', 'message': 'Ticket not found or unauthorized.'}), 404

    # Fetch conversation replies
    replies = query_db(
        """SELECT r.*, u.full_name as sender_name, u.role as sender_role
           FROM ticket_replies r
           JOIN users u ON r.sender_id = u.user_id
           WHERE r.ticket_id = %s
           ORDER BY r.created_at ASC""",
        (ticket_id,)
    )

    # Fetch AI Similar Matches
    similar_matches = query_db(
        """SELECT * FROM ticket_similar_matches
           WHERE ticket_id = %s
           ORDER BY similarity_score DESC LIMIT 3""",
        (ticket_id,)
    )

    return jsonify({
        'status': 'success',
        'ticket': ticket,
        'replies': replies,
        'similar_matches': similar_matches
    })


@app.route('/agent/tickets/<ticket_id>/reply', methods=['POST'])
@agent_required
def agent_ticket_reply(ticket_id):
    agent_dept = g.user['department']
    message = request.form.get('message', '').strip()
    new_status = request.form.get('status', '').strip()
    resolution_notes = request.form.get('resolution_notes', '').strip()

    if not message and not new_status and not resolution_notes:
        flash("No update provided.", "warning")
        return redirect(url_for('agent_dashboard'))

    # Verify ticket scope
    ticket = query_db(
        "SELECT * FROM tickets WHERE ticket_id = %s AND assigned_department = %s",
        (ticket_id, agent_dept),
        one=True
    )
    if not ticket:
        flash("Ticket not found in your department scope.", "danger")
        return redirect(url_for('agent_dashboard'))

    # Insert reply if given
    if message:
        modify_db(
            "INSERT INTO ticket_replies (ticket_id, sender_id, message) VALUES (%s, %s, %s)",
            (ticket_id, g.user['user_id'], message)
        )

    # Update ticket status and resolution notes
    update_fields = ["assigned_agent_id = %s"]
    params = [g.user['user_id']]

    if new_status and new_status in ['Submitted', 'Under Review', 'In Progress', 'Resolved', 'Closed']:
        update_fields.append("status = %s")
        params.append(new_status)
        if new_status == 'Resolved':
            update_fields.append("resolved_at = NOW()")

    if resolution_notes:
        update_fields.append("resolution_notes = %s")
        params.append(resolution_notes)

    params.append(ticket_id)
    modify_db(
        f"UPDATE tickets SET {', '.join(update_fields)} WHERE ticket_id = %s",
        tuple(params)
    )

    flash(f"Ticket {ticket_id} updated successfully.", "success")
    return redirect(url_for('agent_dashboard'))


# ============================================================================
# ADMINISTRATOR PORTAL
# ============================================================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # 1. Metric Cards
    total_tickets = query_db("SELECT COUNT(*) as count FROM tickets", one=True)['count']
    pending_users = query_db("SELECT COUNT(*) as count FROM users WHERE account_status = 'PENDING'", one=True)['count']
    resolved_tickets = query_db("SELECT COUNT(*) as count FROM tickets WHERE status IN ('Resolved', 'Closed')", one=True)['count']
    resolve_rate = round((resolved_tickets / total_tickets * 100), 1) if total_tickets > 0 else 0.0

    # Calculate average resolution time in hours
    avg_res_row = query_db(
        """SELECT AVG(TIMESTAMPDIFF(HOUR, created_at, resolved_at)) as avg_hrs
           FROM tickets
           WHERE status IN ('Resolved', 'Closed') AND resolved_at IS NOT NULL""",
        one=True
    )
    avg_resolution_hours = round(avg_res_row['avg_hrs'], 1) if avg_res_row and avg_res_row['avg_hrs'] else 18.5

    # 2. User Verification Queue
    pending_users_list = query_db(
        "SELECT * FROM users WHERE account_status = 'PENDING' ORDER BY created_at DESC"
    )

    # 3. Fraud Center Tickets
    fraud_tickets = query_db(
        """SELECT t.*, u.full_name as customer_name, u.email as customer_email,
                  u.bill_no_product_id, u.account_status as user_status
           FROM tickets t
           JOIN users u ON t.customer_id = u.user_id
           WHERE t.predicted_category = 'Fraud' OR t.assigned_department = 'Admin_Fraud'
           ORDER BY t.created_at DESC"""
    )

    # 4. Department Distribution Analytics
    dept_stats = query_db(
        """SELECT assigned_department, COUNT(*) as count
           FROM tickets
           GROUP BY assigned_department"""
    )

    # 5. Priority Distribution Analytics
    prio_stats = query_db(
        """SELECT predicted_priority, COUNT(*) as count
           FROM tickets
           GROUP BY predicted_priority"""
    )

    # 6. Satisfaction Distribution Analytics
    sat_stats = query_db(
        """SELECT satisfaction_score, COUNT(*) as count
           FROM tickets
           WHERE satisfaction_score IS NOT NULL
           GROUP BY satisfaction_score
           ORDER BY satisfaction_score ASC"""
    )

    # Convert chart data for JSON rendering in Chart.js
    dept_labels = [row['assigned_department'] for row in dept_stats]
    dept_data = [row['count'] for row in dept_stats]

    prio_labels = [row['predicted_priority'] for row in prio_stats]
    prio_data = [row['count'] for row in prio_stats]

    sat_dict = {row['satisfaction_score']: row['count'] for row in sat_stats}
    sat_labels = ['1 Star', '2 Stars', '3 Stars', '4 Stars', '5 Stars']
    sat_data = [sat_dict.get(i, 0) for i in range(1, 6)]

    return render_template(
        'admin_dashboard.html',
        metrics={
            'total_tickets': total_tickets,
            'pending_users': pending_users,
            'resolve_rate': resolve_rate,
            'avg_resolution_hours': avg_resolution_hours
        },
        pending_users=pending_users_list,
        fraud_tickets=fraud_tickets,
        dept_labels=dept_labels,
        dept_data=dept_data,
        prio_labels=prio_labels,
        prio_data=prio_data,
        sat_labels=sat_labels,
        sat_data=sat_data
    )


@app.route('/admin/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    modify_db("UPDATE users SET account_status = 'APPROVED' WHERE user_id = %s", (user_id,))
    flash(f"User ID #{user_id} approved successfully.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/<int:user_id>/reject', methods=['POST'])
@admin_required
def reject_user(user_id):
    modify_db("UPDATE users SET account_status = 'REJECTED' WHERE user_id = %s", (user_id,))
    flash(f"User ID #{user_id} registration rejected.", "warning")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/<int:user_id>/ban', methods=['POST'])
@admin_required
def ban_user(user_id):
    modify_db("UPDATE users SET account_status = 'BANNED' WHERE user_id = %s", (user_id,))
    flash(f"User ID #{user_id} has been banned from the system.", "danger")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/tickets/<ticket_id>/close', methods=['POST'])
@admin_required
def admin_close_ticket(ticket_id):
    modify_db(
        "UPDATE tickets SET status = 'Closed', resolved_at = NOW(), resolution_notes = 'Closed by Administrator security audit.' WHERE ticket_id = %s",
        (ticket_id,)
    )
    flash(f"Ticket {ticket_id} closed by Admin.", "info")
    return redirect(url_for('admin_dashboard'))


# ============================================================================
# CLI COMMAND FOR DATABASE INITIALIZATION
# ============================================================================

@app.cli.command("init-db")
def init_db_command():
    """Initializes MySQL schema and seed data."""
    try:
        init_db_schema()
        print("CompassIQ database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")


# ============================================================================
# AUTOMATED STARTUP HOOK & MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print(" COMPASSIQ — AI-POWERED SUPPORT INTELLIGENCE PLATFORM")
    print("=" * 70)

    # 1. Automatic Database & Schema Initialization Hook
    try:
        init_db_schema()
    except Exception as e:
        print(f"[CompassIQ DB Warning] Automated database check/initialization encountered error: {e}")
        print("Please ensure MySQL is running and credentials in .env or config.py are correct.")

    # 2. Check for the 4 Required Machine Learning Model Files
    base_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(base_dir, 'models')
    os.makedirs(models_dir, exist_ok=True)

    required_models = [
        'tfidf_vectorizer.joblib',
        'category_model.joblib',
        'priority_model.joblib',
        'historical_corpus.joblib'
    ]

    missing_models = [m for m in required_models if not os.path.exists(os.path.join(models_dir, m))]

    if missing_models:
        print(f"[CompassIQ ML] Missing model artifacts: {missing_models}")
        print("[CompassIQ ML] Automatically launching training pipeline via train_model.py...")
        train_script = os.path.join(base_dir, 'train_model.py')
        
        try:
            result = subprocess.run([sys.executable, train_script], check=True)
            print("[CompassIQ ML] Model training completed successfully.")
            # Reload freshly trained models into memory
            load_ai_engine(force_reload=True)
        except Exception as e:
            print(f"[CompassIQ ML Error] Failed to run automated training pipeline: {e}")
    else:
        print("[CompassIQ ML] All 4 serialized model artifacts verified in models/ directory.")

    # 3. Boot Flask Web Server
    print("\n[CompassIQ] Booting server on http://127.0.0.1:5000 (debug=True)...")
    app.run(host='127.0.0.1', port=5000, debug=True)
