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
app.config['SECRET_KEY'] = 'compassiq-mca-secret-key'

# Disable CSRF protection for viva demo reliability
app.config['WTF_CSRF_ENABLED'] = False
app.config['WTF_CSRF_CHECK_DEFAULT'] = False

# CSRF protection disabled for demo purposes
# csrf = CSRFProtect(app)

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
    Checks both customers and department_agents tables.
    Returns user dictionary or None if not logged in.
    """
    # Support both old and new session keys for backward compatibility
    user_id = session.get('user_id') or session.get('custid') or session.get('agent_id')
    if not user_id:
        return None
    
    try:
        # First check customers table
        user = query_db(
            "SELECT custid, custname, email, account_status FROM customers WHERE custid = ?",
            (user_id,),
            one=True
        )
        if user:
            # Add role for customers
            user['role'] = 'customer'
            user['deptid'] = None
            return user
        
        # Then check department_agents table
        agent = query_db(
            "SELECT agent_id, agent_name, email, deptid, role, account_status FROM department_agents WHERE agent_id = ?",
            (user_id,),
            one=True
        )
        if agent:
            # Map agent fields to consistent names for template compatibility
            agent['custid'] = agent['agent_id']
            agent['custname'] = agent['agent_name']
            return agent
        
        return None
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


@app.after_request
def add_header(response):
    """
    Add cache-control headers to prevent browser caching of authenticated pages.
    This prevents users from navigating back to cached dashboard pages after logout.
    Ensures landing page reflects live session data when using browser back button.
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


def login_required(f):
    """
    Decorator to protect routes that require user authentication.
    Redirects to public landing page if user is not logged in or not approved.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('index'))
        if g.user['account_status'] != 'APPROVED':
            session.clear()
            flash("Your account is not authorized to access this resource.", "danger")
            return redirect(url_for('index'))
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
                return redirect(url_for('index'))
            if g.user['role'] not in roles:
                flash("Access denied: You do not have permission to view this portal.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def customer_required(f):
    """Decorator requiring customer role."""
    return role_required('customer')(login_required(f))


def agent_required(f):
    """Decorator requiring agent role."""
    return role_required('agent')(login_required(f))


def admin_required(f):
    """Decorator requiring admin role."""
    return role_required('admin')(login_required(f))


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
    Customer registration route with auto-approval for streamlined demo flow.
    - GET: Renders registration form
    - POST: Creates new customer with APPROVED status (no admin approval needed)
    - Validates input, checks for existing email in both customers and department_agents tables
    - Only creates customer accounts (staff accounts are created separately)
    """
    if g.user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Step 1: Read and validate form data
        custname = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone_no = request.form.get('phone_no', '').strip()

        # Form validation
        if not custname or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match. Please try again.", "danger")
            return render_template('register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html')

        # Step 2: Check for existing email in both tables
        existing_customer = query_db("SELECT custid FROM customers WHERE email = ?", (email,), one=True)
        existing_agent = query_db("SELECT agent_id FROM department_agents WHERE email = ?", (email,), one=True)
        
        if existing_customer or existing_agent:
            flash("An account with this email address already exists.", "danger")
            return render_template('register.html')

        # Step 3: Create customer with auto-approval
        hashed_password = generate_password_hash(password)

        try:
            modify_db(
                """INSERT INTO customers (custname, email, password, phone_no, account_status)
                   VALUES (?, ?, ?, ?, 'APPROVED')""",
                (custname, email, hashed_password, phone_no)
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
    - POST: Validates credentials against both customers and department_agents tables
    - Creates session, redirects to role-specific dashboard
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

        # Step 2: Check customers table first
        customer = query_db(
            "SELECT custid, custname, email, password, account_status FROM customers WHERE LOWER(email) = ?",
            (email,),
            one=True
        )

        if customer and check_password_hash(customer['password'], password):
            # Step 3: Check account status
            if customer['account_status'] == 'BANNED':
                flash("Your account has been suspended by administration. Please contact support.", "danger")
                return render_template('login.html')

            # Step 4: Create session for customer
            session.clear()
            session['custid'] = customer['custid']
            session['user_id'] = customer['custid']  # Backward compatibility
            session['custname'] = customer['custname']
            session['full_name'] = customer['custname']  # Backward compatibility
            session['email'] = customer['email']
            session['role'] = 'customer'
            session['deptid'] = None

            flash(f"Welcome back, {customer['custname']}!", "success")
            return redirect(url_for('customer_dashboard'))

        # Step 5: Check department_agents table
        agent = query_db(
            "SELECT agent_id, agent_name, email, password, deptid, role, account_status FROM department_agents WHERE LOWER(email) = ?",
            (email,),
            one=True
        )

        if agent and check_password_hash(agent['password'], password):
            # Step 6: Check account status
            if agent['account_status'] == 'BANNED':
                flash("Your account has been suspended by administration. Please contact support.", "danger")
                return render_template('login.html')

            # Step 7: Create session for agent/admin
            session.clear()
            session['agent_id'] = agent['agent_id']
            session['user_id'] = agent['agent_id']  # Backward compatibility
            session['custid'] = agent['agent_id']  # Backward compatibility
            session['custname'] = agent['agent_name']
            session['full_name'] = agent['agent_name']  # Backward compatibility
            session['email'] = agent['email']
            session['role'] = agent['role']
            session['deptid'] = agent['deptid']

            flash(f"Welcome back, {agent['agent_name']}!", "success")

            # Role-based redirect
            if agent['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('agent_dashboard'))

        # Step 8: Invalid credentials
        flash("Invalid email or password. Please verify your credentials.", "danger")
        return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    User logout route.
    Clears session and redirects to public landing page.
    """
    session.clear()
    return redirect(url_for('index'))


# ============================================================================
# FLOW 2: CUSTOMER PORTAL (Create Tickets, View History, Submit Feedback)
# ============================================================================

@app.route('/customer/dashboard')
@customer_required
def customer_dashboard():
    """
    Customer dashboard showing all tickets created by the current customer.
    Displays ticket list with department assignment and status information.
    """
    # Fetch all tickets created by customer with department details
    # Support both old and new session keys for backward compatibility
    user_id = g.user.get('custid') or g.user.get('user_id')
    tickets = query_db(
        """SELECT c.*, d.deptname as department_name
           FROM complaints c
           LEFT JOIN departments d ON c.deptid = d.deptid
           WHERE c.custid = ?
           ORDER BY c.submitdate DESC""",
        (user_id,)
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
    - Step 3: Map category to deptid (Technical→1, Billing→2, Account→3, General→4)
    - Step 4: Insert complaint with AI predictions into database
    - Step 5: Create initial reply message
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

    # Step 3: Map category to deptid
    category_to_deptid = {
        'Technical': 1,
        'Billing': 2,
        'Account': 3,
        'General Inquiry': 4
    }
    deptid = category_to_deptid.get(predicted_category, 4)  # Default to General Inquiry

    ticket_id = generate_ticket_id()

    # Support both old and new session keys for backward compatibility
    user_id = g.user.get('custid') or g.user.get('user_id')

    try:
        # Step 4: Insert complaint with AI predictions
        modify_db(
            """INSERT INTO complaints (ticketno, custid, deptid, subject, description,
                                   predicted_priority, status)
               VALUES (?, ?, ?, ?, ?, ?, 'Submitted')""",
            (ticket_id, user_id, deptid, subject, description, predicted_priority)
        )

        # Step 5: Insert initial ticket reply message
        modify_db(
            """INSERT INTO ticket_replies (ticketno, sender_id, message)
               VALUES (?, ?, ?)""",
            (ticket_id, user_id, description)
        )

        # Get department name for flash message
        dept = query_db("SELECT deptname FROM departments WHERE deptid = ?", (deptid,), one=True)
        dept_name = dept['deptname'] if dept else 'General Inquiry'

        flash(f"Ticket {ticket_id} created successfully! Routed to {dept_name} team.", "success")

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
    user_id = g.user.get('custid') or g.user.get('user_id')
    ticket = query_db(
        """SELECT c.*, d.deptname as department_name
           FROM complaints c
           LEFT JOIN departments d ON c.deptid = d.deptid
           WHERE c.ticketno = ? AND c.custid = ?""",
        (ticket_id, user_id),
        one=True
    )
    if not ticket:
        return jsonify({
            'success': False,
            'message': 'Ticket not found or unauthorized'
        }), 404

    # Step 2: Fetch conversation replies (from both customers and agents)
    replies = query_db(
        """SELECT r.*, 
                  COALESCE(c.custname, a.agent_name) as sender_name,
                  COALESCE(c.role, a.role) as sender_role
           FROM ticket_replies r
           LEFT JOIN customers c ON r.sender_id = c.custid
           LEFT JOIN department_agents a ON r.sender_id = a.agent_id
           WHERE r.ticketno = ?
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
    user_id = g.user.get('custid') or g.user.get('user_id')
    ticket = query_db(
        "SELECT status FROM complaints WHERE ticketno = ? AND custid = ?",
        (ticket_id, user_id),
        one=True
    )
    if not ticket:
        return jsonify({'success': False, 'message': 'Unauthorized or invalid ticket.'}), 403

    if ticket['status'] in ['Resolved', 'Closed']:
        return jsonify({'success': False, 'message': 'This ticket is resolved or closed. Replies are locked.'}), 403

    # Step 3: Insert reply
    user_id = g.user.get('custid') or g.user.get('user_id')
    modify_db(
        "INSERT INTO ticket_replies (ticketno, sender_id, message) VALUES (?, ?, ?)",
        (ticket_id, user_id, message)
    )
    
    # Step 4: Fetch new reply for UI update (from both customers and agents)
    new_reply = query_db(
        """SELECT r.*, 
                  COALESCE(c.custname, a.agent_name) as sender_name,
                  COALESCE(c.role, a.role) as sender_role
           FROM ticket_replies r
           LEFT JOIN customers c ON r.sender_id = c.custid
           LEFT JOIN department_agents a ON r.sender_id = a.agent_id
           WHERE r.ticketno = ? 
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
    - Step 3: Update complaint with satisfaction score and feedback
    """
    # Step 1: Read and validate rating
    score = request.form.get('satisfaction_score', type=int)
    feedback = request.form.get('customer_feedback', '').strip()

    if not score or score < 1 or score > 5:
        flash("Please provide a rating between 1 and 5 stars.", "warning")
        return redirect(url_for('customer_dashboard'))

    # Step 2: Verify ticket status
    user_id = g.user.get('custid') or g.user.get('user_id')
    ticket = query_db(
        "SELECT status FROM complaints WHERE ticketno = ? AND custid = ?",
        (ticket_id, user_id),
        one=True
    )
    if not ticket or ticket['status'] not in ['Resolved', 'Closed']:
        flash("Feedback can only be submitted for resolved tickets.", "danger")
        return redirect(url_for('customer_dashboard'))

    # Step 3: Update complaint with feedback
    user_id = g.user.get('custid') or g.user.get('user_id')
    modify_db(
        """UPDATE complaints
           SET satisfaction_score = ?, resolution_notes = ?, status = 'Closed'
           WHERE ticketno = ? AND custid = ?""",
        (score, feedback, ticket_id, user_id)
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
    # Support both old and new session keys for backward compatibility
    agent_deptid = g.user.get('deptid') or None
    status_filter = request.args.get('status', 'all')

    # Get department name
    agent_dept = 'General Inquiry'
    if agent_deptid:
        dept = query_db("SELECT deptname FROM departments WHERE deptid = ?", (agent_deptid,), one=True)
        agent_dept = dept['deptname'] if dept else 'General Inquiry'

    # Build dynamic SQL query with optional status filter
    sql = """
        SELECT c.*, u.custname as customer_name, u.email as customer_email,
               d.deptname as department_name
        FROM complaints c
        JOIN customers u ON c.custid = u.custid
        LEFT JOIN departments d ON c.deptid = d.deptid
    """
    params = []

    # Only filter by department if agent has a deptid
    if agent_deptid:
        sql += " WHERE c.deptid = ?"
        params.append(agent_deptid)

    if status_filter != 'all':
        sql += " AND c.status = ?" if agent_deptid else " WHERE c.status = ?"
        params.append(status_filter)

    # Order by priority (Critical first) then by creation date
    sql += " ORDER BY CASE c.predicted_priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 ELSE 5 END, c.submitdate DESC"

    tickets = query_db(sql, tuple(params))
    
    # Fetch summary statistics for dashboard counters
    if agent_deptid:
        counts = query_db(
            """SELECT
                COUNT(*) as total,
                SUM(status = 'Submitted') as count_submitted,
                SUM(status = 'Under Review') as count_under_review,
                SUM(status = 'In Progress') as count_in_progress,
                SUM(status = 'Resolved') as count_resolved
               FROM complaints
               WHERE deptid = ?""",
            (agent_deptid,),
            one=True
        )
    else:
        # Admin sees all tickets
        counts = query_db(
            """SELECT
                COUNT(*) as total,
                SUM(status = 'Submitted') as count_submitted,
                SUM(status = 'Under Review') as count_under_review,
                SUM(status = 'In Progress') as count_in_progress,
                SUM(status = 'Resolved') as count_resolved
               FROM complaints""",
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
    # Support both old and new session keys for backward compatibility
    agent_deptid = g.user.get('deptid') or None
    user_role = g.user.get('role', '')
    
    # Step 1: Fetch ticket with department verification
    ticket = query_db(
        """SELECT c.*, u.custname as customer_name, u.email as customer_email,
                  d.deptname as department_name
           FROM complaints c
           JOIN customers u ON c.custid = u.custid
           LEFT JOIN departments d ON c.deptid = d.deptid
           WHERE c.ticketno = ? AND (c.deptid = ? OR ? = 'admin')""",
        (ticket_id, agent_deptid, user_role),
        one=True
    )
    if not ticket:
        return jsonify({'status': 'error', 'message': 'Ticket not found or unauthorized.'}), 404

    # Step 2: Fetch conversation replies
    replies = query_db(
        """SELECT r.*, u.custname as sender_name, u.role as sender_role
           FROM ticket_replies r
           JOIN customers u ON r.sender_id = u.custid
           WHERE r.ticketno = ?
           ORDER BY r.created_at ASC""",
        (ticket_id,)
    )

    # Step 3: Fetch similar historical matches (top 3)
    similar_matches = query_db(
        """SELECT similar_ticket_ref_id, similarity_score, similar_subject, 
                  similar_description, historical_resolution_hours
           FROM ticket_similar_matches
           WHERE ticketno = ?
           ORDER BY similarity_score DESC
           LIMIT 3""",
        (ticket_id,)
    )

    return jsonify({
        'status': 'success',
        'ticket': ticket,
        'replies': replies,
        'similar_matches': similar_matches or []
    })


@app.route('/agent/tickets/<ticket_id>/reply', methods=['POST'])
@agent_required
def agent_ticket_reply(ticket_id):
    """
    Agent ticket update endpoint.
    - Step 1: Read reply message, status update, and resolution notes
    - Step 2: Verify ticket belongs to agent's department
    - Step 3: Insert reply if provided
    - Step 4: Update complaint status and add resolution notes
    """
    # Step 1: Read form data
    agent_deptid = g.user.get('deptid') or None
    user_id = g.user.get('custid') or g.user.get('user_id')
    message = request.form.get('message', '').strip()
    new_status = request.form.get('status', '').strip()
    resolution_notes = request.form.get('resolution_notes', '').strip()

    if not message and not new_status and not resolution_notes:
        flash("No update provided.", "warning")
        return redirect(url_for('agent_dashboard'))

    # Step 2: Verify ticket scope
    if agent_deptid:
        ticket = query_db(
            "SELECT * FROM complaints WHERE ticketno = ? AND deptid = ?",
            (ticket_id, agent_deptid),
            one=True
        )
    else:
        # Admin can access all tickets
        ticket = query_db(
            "SELECT * FROM complaints WHERE ticketno = ?",
            (ticket_id,),
            one=True
        )
    if not ticket:
        flash("Ticket not found in your department scope.", "danger")
        return redirect(url_for('agent_dashboard'))

    # Step 3: Insert reply if provided
    if message:
        modify_db(
            "INSERT INTO ticket_replies (ticketno, sender_id, message) VALUES (?, ?, ?)",
            (ticket_id, user_id, message)
        )

    # Step 4: Update complaint status and metadata
    update_fields = []
    params = []

    if new_status and new_status in ['Submitted', 'Under Review', 'In Progress', 'Resolved', 'Closed']:
        update_fields.append("status = ?")
        params.append(new_status)
        if new_status == 'Resolved':
            update_fields.append("resolved_at = CURRENT_TIMESTAMP")

    if resolution_notes:
        update_fields.append("resolution_notes = ?")
        params.append(resolution_notes)

    if update_fields:
        params.append(ticket_id)
        modify_db(
            f"UPDATE complaints SET {', '.join(update_fields)} WHERE ticketno = ?",
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
    - Step 3: Fetch all users for User Management
    - Step 4: Fetch all system tickets for Ticket Registry
    - Returns metrics, analytics data, user list, and ticket list
    """
    # Step 1: Calculate core metrics
    total_tickets = query_db("SELECT COUNT(*) as count FROM complaints", one=True)['count']
    resolved_tickets = query_db("SELECT COUNT(*) as count FROM complaints WHERE status IN ('Resolved', 'Closed')", one=True)['count']

    # Step 2: Fetch category distribution for analytics
    dept_stats = query_db(
        """SELECT d.deptname as assigned_department, COUNT(*) as count
           FROM complaints c
           JOIN departments d ON c.deptid = d.deptid
           GROUP BY d.deptname"""
    )

    # Convert chart data for JSON rendering in Chart.js
    dept_labels = [row['assigned_department'] for row in dept_stats]
    dept_data = [row['count'] for row in dept_stats]

    # Step 3: Fetch all users for User Management (from both tables)
    all_customers = query_db(
        """SELECT custid, custname, email, account_status, created_at
           FROM customers 
           ORDER BY created_at DESC"""
    )
    
    all_agents = query_db(
        """SELECT agent_id, agent_name, email, deptid, role, account_status, created_at
           FROM department_agents 
           ORDER BY created_at DESC"""
    )

    # Step 4: Fetch all system tickets for Ticket Registry
    all_tickets = query_db(
        """SELECT ticketno, subject, d.deptname as category, predicted_priority, status, submitdate
           FROM complaints c
           JOIN departments d ON c.deptid = d.deptid
           ORDER BY c.submitdate DESC"""
    )

    return render_template(
        'admin_dashboard.html',
        metrics={
            'total_tickets': total_tickets,
            'resolved_tickets': resolved_tickets
        },
        dept_labels=dept_labels,
        dept_data=dept_data,
        customers=all_customers,
        agents=all_agents,
        tickets=all_tickets
    )


# Legacy admin routes (kept for API compatibility but not used in simplified UI)
@app.route('/admin/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    """Legacy user approval route (not used with auto-approval)."""
    user = query_db("SELECT role, deptid FROM customers WHERE custid = ?", (user_id,), one=True)
    
    if user and user['role'] == 'agent' and not user['deptid']:
        default_deptid = request.form.get('deptid', 1)
        modify_db("UPDATE customers SET account_status = 'APPROVED', deptid = ? WHERE custid = ?", (default_deptid, user_id))
        flash(f"User ID #{user_id} approved successfully and assigned to department ID {default_deptid}.", "success")
    else:
        modify_db("UPDATE customers SET account_status = 'APPROVED' WHERE custid = ?", (user_id,))
        flash(f"User ID #{user_id} approved successfully.", "success")
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/<int:user_id>/reject', methods=['POST'])
@admin_required
def reject_user(user_id):
    """Legacy user rejection route (not used with auto-approval)."""
    modify_db("UPDATE customers SET account_status = 'REJECTED' WHERE custid = ?", (user_id,))
    flash(f"User ID #{user_id} registration rejected.", "warning")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/users/<int:user_id>/ban', methods=['POST'])
@admin_required
def ban_user(user_id):
    """Legacy user ban route (not used in simplified UI)."""
    modify_db("UPDATE customers SET account_status = 'BANNED' WHERE custid = ?", (user_id,))
    flash(f"User ID #{user_id} has been banned from the system.", "danger")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/tickets/<ticket_id>/close', methods=['POST'])
@admin_required
def admin_close_ticket(ticket_id):
    """Legacy admin ticket closure route (not used in simplified UI)."""
    modify_db(
        "UPDATE complaints SET status = 'Closed', resolved_at = CURRENT_TIMESTAMP, resolution_notes = 'Closed by Administrator security audit.' WHERE ticketno = ?",
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
