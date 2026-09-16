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


def normalize_department(dept_name: str):
    """
    Standardizes department names across the system to:
    'Technical', 'Billing', 'Account', 'General Inquiry', 'Fraud & Security', or None.
    """
    if not dept_name:
        return None
    cleaned = str(dept_name).strip()
    lower = cleaned.lower()
    if 'fraud' in lower or 'security' in lower:
        return 'Fraud & Security'
    elif 'tech' in lower:
        return 'Technical'
    elif 'bill' in lower:
        return 'Billing'
    elif 'account' in lower:
        return 'Account'
    elif 'general' in lower or 'inquiry' in lower:
        return 'General Inquiry'
    return cleaned


def verify_password(stored_password: str, provided_password: str) -> bool:
    """
    Verifies user password against stored password hash.
    Falls back to safe plain-text comparison if dummy/seed accounts were created without proper hashing.
    Also recognizes standard demo passwords ('Admin@123', 'Agent@123', 'User@123', 'password123', 'agent123').
    """
    if not stored_password or not provided_password:
        return False
    
    # 1. Standard hash verification
    try:
        if check_password_hash(stored_password, provided_password):
            return True
    except Exception:
        pass
    
    # 2. Plain-text comparison fallback (unhashed seed accounts)
    if stored_password == provided_password:
        return True
        
    # 3. Inter-compatible demo password fallback across standardized demo suites
    demo_passwords = ['Admin@123', 'Agent@123', 'User@123', 'password123', 'agent123']
    if provided_password in demo_passwords:
        for dp in demo_passwords:
            try:
                if check_password_hash(stored_password, dp):
                    return True
            except Exception:
                pass
            
    return False


def get_current_user():
    """
    Retrieves current logged in user from database using session.
    Checks session['role'] and session['agent_id'] to query the correct table,
    preventing ID collision between customers and department_agents tables.
    Returns normalized user dictionary or None if not logged in.
    """
    user_id = session.get('user_id') or session.get('agent_id') or session.get('custid')
    if not user_id:
        return None

    role = str(session.get('role', '')).lower().strip()

    try:
        # Priority 1: If session indicates agent or admin role (or has agent_id)
        if role in ['agent', 'admin'] or session.get('agent_id'):
            target_id = session.get('agent_id') or user_id
            agent = query_db(
                """SELECT a.agent_id, a.agent_name, a.email, a.deptid, a.role, a.account_status,
                          COALESCE(d.deptname, 'General Inquiry') as department
                   FROM department_agents a
                   LEFT JOIN departments d ON a.deptid = d.deptid
                   WHERE a.agent_id = ?""",
                (target_id,),
                one=True
            )
            if agent:
                agent['custid'] = agent['agent_id']
                agent['custname'] = agent['agent_name']
                agent['user_id'] = agent['agent_id']
                agent['full_name'] = agent['agent_name']
                agent['role'] = str(agent['role'] or 'agent').lower().strip()
                agent['department'] = normalize_department(agent.get('department'))
                return agent

        # Priority 2: If session indicates customer role (or has custid)
        if role == 'customer' or session.get('custid'):
            target_id = session.get('custid') or user_id
            customer = query_db(
                "SELECT custid, custname, email, account_status FROM customers WHERE custid = ?",
                (target_id,),
                one=True
            )
            if customer:
                customer['role'] = 'customer'
                customer['deptid'] = None
                customer['department'] = None
                customer['user_id'] = customer['custid']
                customer['full_name'] = customer['custname']
                return customer

        # Priority 3: Fallback check in department_agents first, then customers
        agent = query_db(
            """SELECT a.agent_id, a.agent_name, a.email, a.deptid, a.role, a.account_status,
                      COALESCE(d.deptname, 'General Inquiry') as department
               FROM department_agents a
               LEFT JOIN departments d ON a.deptid = d.deptid
               WHERE a.agent_id = ?""",
            (user_id,),
            one=True
        )
        if agent:
            agent['custid'] = agent['agent_id']
            agent['custname'] = agent['agent_name']
            agent['user_id'] = agent['agent_id']
            agent['full_name'] = agent['agent_name']
            agent['role'] = str(agent['role'] or 'agent').lower().strip()
            agent['department'] = normalize_department(agent.get('department'))
            return agent

        customer = query_db(
            "SELECT custid, custname, email, account_status FROM customers WHERE custid = ?",
            (user_id,),
            one=True
        )
        if customer:
            customer['role'] = 'customer'
            customer['deptid'] = None
            customer['department'] = None
            customer['user_id'] = customer['custid']
            customer['full_name'] = customer['custname']
            return customer

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
    Supports both 'APPROVED' and 'ACTIVE' account status (case-insensitive).
    Returns JSON 401/403 for AJAX/API requests.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        path = request.path.lower()
        is_api = (
            request.is_json or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            path.startswith('/api/') or
            path.startswith('/customer/ticket') or
            path.startswith('/customer/tickets') or
            request.args.get('format') == 'json' or
            ('application/json' in request.headers.get('Accept', '') and 'text/html' not in request.headers.get('Accept', ''))
        )
        if g.user is None:
            if is_api:
                return jsonify({'success': False, 'status': 'error', 'error': 'Unauthorized', 'message': 'Authentication required. Please log in.'}), 401
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login'))
        
        status = str(g.user.get('account_status', '')).strip().upper()
        if status not in ['APPROVED', 'ACTIVE']:
            session.clear()
            if is_api:
                return jsonify({'success': False, 'status': 'error', 'error': 'Unauthorized', 'message': 'Your account is not authorized or has been suspended.'}), 403
            flash("Your account is not authorized to access this resource.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorator to restrict route access to specific user roles.
    Used for RBAC (Role-Based Access Control) implementation.
    Case-insensitive role verification. Returns JSON 403 for AJAX/API requests.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            path = request.path.lower()
            is_api = (
                request.is_json or
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                path.startswith('/api/') or
                path.startswith('/customer/ticket') or
                path.startswith('/customer/tickets') or
                request.args.get('format') == 'json' or
                ('application/json' in request.headers.get('Accept', '') and 'text/html' not in request.headers.get('Accept', ''))
            )
            if g.user is None:
                if is_api:
                    return jsonify({'success': False, 'status': 'error', 'error': 'Unauthorized', 'message': 'Authentication required. Please log in.'}), 401
                flash("Please sign in first.", "warning")
                return redirect(url_for('login'))
            
            normalized_roles = [str(r).lower().strip() for r in roles]
            user_role = str(g.user.get('role', '')).lower().strip()
            
            if user_role not in normalized_roles:
                if is_api:
                    return jsonify({'success': False, 'status': 'error', 'error': 'Unauthorized', 'message': 'Access denied: You do not have permission to view this resource.'}), 403
                flash("Access denied: You do not have permission to view this portal.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def customer_required(f):
    """Decorator requiring customer role."""
    return role_required('customer')(login_required(f))


def agent_required(f):
    """Decorator requiring agent (or admin) role."""
    return role_required('agent', 'admin')(login_required(f))


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
    - GET: Renders login form (or redirects if already logged in)
    - POST: Validates credentials dynamically against department_agents and customers tables
    - Explicitly sets dynamic session attributes (user_id, role, department, user_name)
    - Redirects based on role (admin -> /admin/dashboard, agent -> /agent/dashboard, customer -> /customer/dashboard)
    - Blocks BANNED/SUSPENDED accounts
    """
    # Only redirect GET requests if user is already authenticated
    if request.method == 'GET' and g.user:
        user_role = str(g.user.get('role', '')).lower().strip()
        if user_role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user_role == 'agent':
            return redirect(url_for('agent_dashboard'))
        else:
            return redirect(url_for('customer_dashboard'))

    if request.method == 'POST':
        # Clear any prior session state before authenticating new user
        session.clear()

        # Step 1: Read and validate credentials
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both email and password.", "warning")
            return render_template('login.html')

        # Step 2: Check department_agents table FIRST (staff & admin accounts)
        agent = query_db(
            """SELECT a.agent_id, a.agent_name, a.email, a.password, a.deptid, a.role, a.account_status,
                      d.deptname as department
               FROM department_agents a
               LEFT JOIN departments d ON a.deptid = d.deptid
               WHERE LOWER(TRIM(a.email)) = ?""",
            (email,),
            one=True
        )

        if agent and verify_password(agent['password'], password):
            agent_status = str(agent['account_status'] or '').upper().strip()
            if agent_status in ['BANNED', 'SUSPENDED', 'REJECTED']:
                flash("Your account has been suspended by administration. Please contact support.", "danger")
                return render_template('login.html')

            # Populate dynamic session attributes
            role = str(agent['role'] or 'agent').lower().strip()
            session['user_id'] = agent['agent_id']
            session['role'] = role
            session['department'] = normalize_department(agent['department'])
            session['user_name'] = agent['agent_name']

            # Backward compatibility session keys
            session['agent_id'] = agent['agent_id']
            session['full_name'] = agent['agent_name']
            session['custname'] = agent['agent_name']
            session['email'] = agent['email']
            session['deptid'] = agent['deptid']

            flash(f"Welcome back, {agent['agent_name']}!", "success")

            # Role-based redirect
            if role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif role == 'agent':
                return redirect(url_for('agent_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))

        # Step 3: Check customers table
        customer = query_db(
            """SELECT custid, custname, email, password, account_status
               FROM customers
               WHERE LOWER(TRIM(email)) = ?""",
            (email,),
            one=True
        )

        if customer and verify_password(customer['password'], password):
            cust_status = str(customer['account_status'] or '').upper().strip()
            if cust_status in ['BANNED', 'SUSPENDED', 'REJECTED']:
                flash("Your account has been suspended by administration. Please contact support.", "danger")
                return render_template('login.html')

            # Populate dynamic session attributes
            session['user_id'] = customer['custid']
            session['role'] = 'customer'
            session['department'] = None
            session['user_name'] = customer['custname']

            # Backward compatibility session keys
            session['custid'] = customer['custid']
            session['full_name'] = customer['custname']
            session['custname'] = customer['custname']
            session['email'] = customer['email']
            session['deptid'] = None

            flash(f"Welcome back, {customer['custname']}!", "success")
            return redirect(url_for('customer_dashboard'))

        # Step 4: Invalid credentials
        flash("Invalid email or password. Please verify your credentials.", "danger")
        return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    User logout route.
    Clears session and authentication cookies, redirects to public landing page.
    """
    session.clear()
    g.user = None
    response = redirect(url_for('index'))
    response.delete_cookie(app.config.get('SESSION_COOKIE_NAME', 'session'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


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
        'General Inquiry': 4,
        'Fraud': 5,
        'Fraud & Security': 5
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

        # Step 6: Persist AI similar historical matches
        for sim in ai_result.get('similar_tickets', []):
            try:
                modify_db(
                    """INSERT INTO ticket_similar_matches (
                           ticketno, similar_ticket_ref_id, similarity_score,
                           similar_subject, similar_description, historical_resolution_hours
                       ) VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        ticket_id,
                        sim.get('ticket_id', 'HIST-000'),
                        float(sim.get('similarity_score', 0.85)),
                        sim.get('subject', 'Similar Incident'),
                        sim.get('description', 'Historical resolution details...'),
                        int(sim.get('resolution_hours', 12) or 12)
                    )
                )
            except Exception as sim_err:
                print(f"[CompassIQ AI] Notice: similar match insert: {sim_err}")

        # Get department name for flash message
        dept = query_db("SELECT deptname FROM departments WHERE deptid = ?", (deptid,), one=True)
        dept_name = dept['deptname'] if dept else 'General Inquiry'

        flash(f"Ticket {ticket_id} created successfully! Routed to {dept_name} team.", "success")

    except Exception as e:
        flash(f"Failed to submit ticket: {e}", "danger")

    return redirect(url_for('customer_dashboard'))


@app.route('/customer/tickets/<string:ticket_id>')
@app.route('/customer/ticket/<string:ticket_id>')
@app.route('/api/customer/tickets/<string:ticket_id>')
@app.route('/api/customer/ticket/<string:ticket_id>')
@login_required
def view_customer_ticket(ticket_id):
    """
    DEPRECATED: Customer ticket details endpoint.
    Redirects to unified /api/ticket/<ticket_id> endpoint for consistency.
    """
    return get_ticket_details(ticket_id)
    """
    Customer ticket details endpoint (AJAX & API).
    Returns ticket information and conversation history in JSON format.
    Used for populating ticket detail modals.
    """
    user_id = g.user.get('custid') or g.user.get('user_id')
    user_role = str(g.user.get('role', '')).lower().strip()

    clean_id = str(ticket_id).strip()
    numeric_id = clean_id.upper().replace('TKT-', '').strip()
    alt_id = f"TKT-{numeric_id}"

    # Step 1: Check ticket existence and ownership
    if user_role not in ['admin', 'agent']:
        existing_any = query_db(
            """SELECT ticketno, custid FROM complaints 
               WHERE (ticketno = ? OR ticketno = ? OR LOWER(ticketno) = LOWER(?) OR LOWER(ticketno) = LOWER(?))""",
            (clean_id, alt_id, clean_id, alt_id),
            one=True
        )
        if existing_any and str(existing_any.get('custid')) != str(user_id):
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'Unauthorized',
                'message': 'Access denied: You are not authorized to view tickets belonging to other customer accounts.'
            }), 403

    # Step 2: Fetch ticket with safe LEFT JOINs on dual-table schema
    if user_role in ['admin', 'agent']:
        ticket = query_db(
            """SELECT c.*, c.ticketno as ticket_id, c.custid as customer_id,
                      COALESCE(cust.custname, 'Customer Client') as customer_name,
                      COALESCE(cust.email, 'customer@compassiq.com') as customer_email,
                      COALESCE(d.deptname, 'General Inquiry') as department_name,
                      COALESCE(c.predicted_category, COALESCE(d.deptname, 'General Inquiry')) as predicted_category,
                      COALESCE(c.predicted_priority, 'Medium') as predicted_priority,
                      COALESCE(c.status, 'Submitted') as status,
                      COALESCE(a.agent_name, 'Unassigned') as assigned_agent_name
               FROM complaints c
               LEFT JOIN customers cust ON c.custid = cust.custid
               LEFT JOIN departments d ON c.deptid = d.deptid
               LEFT JOIN department_agents a ON c.assigned_agent_id = a.agent_id
               WHERE (c.ticketno = ? OR c.ticketno = ? OR LOWER(c.ticketno) = LOWER(?) OR LOWER(c.ticketno) = LOWER(?))""",
            (clean_id, alt_id, clean_id, alt_id),
            one=True
        )
    else:
        ticket = query_db(
            """SELECT c.*, c.ticketno as ticket_id, c.custid as customer_id,
                      COALESCE(cust.custname, 'Customer Client') as customer_name,
                      COALESCE(cust.email, 'customer@compassiq.com') as customer_email,
                      COALESCE(d.deptname, 'General Inquiry') as department_name,
                      COALESCE(c.predicted_category, COALESCE(d.deptname, 'General Inquiry')) as predicted_category,
                      COALESCE(c.predicted_priority, 'Medium') as predicted_priority,
                      COALESCE(c.status, 'Submitted') as status,
                      COALESCE(a.agent_name, 'Unassigned') as assigned_agent_name
               FROM complaints c
               LEFT JOIN customers cust ON c.custid = cust.custid
               LEFT JOIN departments d ON c.deptid = d.deptid
               LEFT JOIN department_agents a ON c.assigned_agent_id = a.agent_id
               WHERE (c.ticketno = ? OR c.ticketno = ? OR LOWER(c.ticketno) = LOWER(?) OR LOWER(c.ticketno) = LOWER(?)) AND c.custid = ?""",
            (clean_id, alt_id, clean_id, alt_id, user_id),
            one=True
        )

    if not ticket:
        return jsonify({
            'success': False,
            'status': 'error',
            'error': 'Not Found',
            'message': f"Ticket '{ticket_id}' not found in system."
        }), 404

    # Ensure consistent keys and safe fallbacks
    ticket['ticketno'] = ticket.get('ticketno') or clean_id
    ticket['ticket_id'] = ticket['ticketno']
    ticket['customer_id'] = ticket.get('customer_id') or ticket.get('custid')
    ticket['customer_name'] = ticket.get('customer_name') or 'Customer Client'
    ticket['customer_email'] = ticket.get('customer_email') or 'customer@compassiq.com'
    ticket['customer'] = {
        'name': ticket['customer_name'],
        'email': ticket['customer_email']
    }
    ticket['department_name'] = ticket.get('department_name') or 'General Inquiry'
    ticket['assigned_department'] = ticket['department_name']
    ticket['predicted_category'] = ticket.get('predicted_category') or ticket['department_name']
    ticket['predicted_priority'] = ticket.get('predicted_priority') or 'Medium'
    ticket['status'] = ticket.get('status') or 'Submitted'

    # Step 3: Fetch conversation replies (from both customers and department_agents)
    replies = query_db(
        """SELECT r.*, r.ticketno as ticket_id,
                  COALESCE(cust.custname, a.agent_name, 'Support User') as sender_name,
                  CASE
                    WHEN cust.custid IS NOT NULL THEN 'customer'
                    WHEN a.agent_id IS NOT NULL THEN COALESCE(a.role, 'agent')
                    ELSE 'agent'
                  END as sender_role
           FROM ticket_replies r
           LEFT JOIN customers cust ON r.sender_id = cust.custid
           LEFT JOIN department_agents a ON r.sender_id = a.agent_id
           WHERE (r.ticketno = ? OR r.ticketno = ? OR LOWER(r.ticketno) = LOWER(?) OR LOWER(r.ticketno) = LOWER(?))
           ORDER BY r.created_at ASC""",
        (clean_id, alt_id, clean_id, alt_id)
    ) or []

    # Step 4: Fetch similar matches if any exist
    similar_matches = query_db(
        """SELECT match_id, ticketno, ticketno as ticket_id,
                  similar_ticket_ref_id, similarity_score, similar_subject, 
                  similar_description, historical_resolution_hours
           FROM ticket_similar_matches
           WHERE (ticketno = ? OR ticketno = ? OR LOWER(ticketno) = LOWER(?) OR LOWER(ticketno) = LOWER(?))
           ORDER BY similarity_score DESC
           LIMIT 3""",
        (clean_id, alt_id, clean_id, alt_id)
    ) or []

    return jsonify({
        'success': True,
        'status': 'success',
        'ticket': ticket,
        'customer': ticket['customer'],
        'replies': replies,
        'similar_matches': similar_matches
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
                  COALESCE(u.full_name, 'Support User') as sender_name,
                  COALESCE(u.role, 'customer') as sender_role
           FROM ticket_replies r
           LEFT JOIN (
               SELECT user_id, full_name, role FROM users GROUP BY user_id
           ) u ON r.sender_id = u.user_id
           WHERE (r.ticketno = ? OR r.ticketno = 'TKT-' || ?) 
           ORDER BY r.created_at DESC LIMIT 1""",
        (ticket_id, ticket_id),
        one=True
    )
    
    return jsonify({
        'success': True,
        'message': 'Reply sent successfully.',
        'reply': new_reply
    })


@app.route('/tickets/<ticket_id>/rate', methods=['POST'])
@app.route('/api/tickets/<ticket_id>/rate', methods=['POST'])
@app.route('/customer/tickets/<ticket_id>/rate', methods=['POST'])
@app.route('/customer/tickets/<ticket_id>/feedback', methods=['POST'])
@customer_required
def submit_feedback(ticket_id):
    """
    Customer satisfaction feedback submission (CSAT rating).
    - Validates rating (1-5 stars)
    - Verifies ticket belongs to customer and is in Resolved or Closed state
    - Updates complaints table: satisfaction_score, customer_feedback, status = 'Closed'
    - Supports both JSON (AJAX) and form submissions
    """
    json_data = request.get_json(silent=True) or {}
    
    score = (
        request.form.get('satisfaction_score', type=int) or
        json_data.get('satisfaction_score') or
        json_data.get('score')
    )
    if score is not None:
        try:
            score = int(score)
        except (ValueError, TypeError):
            score = None

    feedback = (
        request.form.get('customer_feedback') or
        json_data.get('customer_feedback') or
        json_data.get('feedback') or ''
    ).strip()

    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not score or score < 1 or score > 5:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Please provide a rating between 1 and 5 stars.'}), 400
        flash("Please provide a rating between 1 and 5 stars.", "warning")
        return redirect(url_for('customer_dashboard'))

    # Verify ticket ownership and status
    user_id = g.user.get('custid') or g.user.get('user_id')
    ticket = query_db(
        "SELECT status FROM complaints WHERE (ticketno = ? OR ticketno = 'TKT-' || ?) AND custid = ?",
        (ticket_id, ticket_id, user_id),
        one=True
    )
    if not ticket:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Unauthorized or invalid ticket.'}), 403
        flash("Unauthorized or invalid ticket.", "danger")
        return redirect(url_for('customer_dashboard'))

    if ticket['status'] not in ['Resolved', 'Closed']:
        if is_ajax:
            return jsonify({'success': False, 'message': 'Feedback can only be submitted for resolved tickets.'}), 400
        flash("Feedback can only be submitted for resolved tickets.", "danger")
        return redirect(url_for('customer_dashboard'))

    # Update complaint with satisfaction score and customer feedback (preserving resolution_notes!)
    modify_db(
        """UPDATE complaints
           SET satisfaction_score = ?, customer_feedback = ?, status = 'Closed'
           WHERE (ticketno = ? OR ticketno = 'TKT-' || ?) AND custid = ?""",
        (score, feedback, ticket_id, ticket_id, user_id)
    )

    if is_ajax:
        return jsonify({
            'success': True,
            'status': 'success',
            'message': 'Thank you! Your satisfaction feedback has been recorded.',
            'satisfaction_score': score,
            'customer_feedback': feedback
        })

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
    agent_deptid = g.user.get('deptid') or session.get('deptid')
    status_filter = request.args.get('status', 'all')
    agent_dept = str(g.user.get('department') or session.get('department') or '').strip()

    # Resolve deptid from department name if needed
    if not agent_deptid and agent_dept:
        dept = query_db(
            """SELECT deptid, deptname FROM departments 
               WHERE LOWER(TRIM(deptname)) = LOWER(TRIM(?))
                  OR LOWER(TRIM(deptname)) LIKE LOWER(TRIM(?)) || '%'""",
            (agent_dept, agent_dept),
            one=True
        )
        if dept:
            agent_deptid = dept['deptid']
            agent_dept = dept['deptname']

    # If deptid is known, get department name
    if agent_deptid and not agent_dept:
        dept = query_db("SELECT deptname FROM departments WHERE deptid = ?", (agent_deptid,), one=True)
        agent_dept = dept['deptname'] if dept else 'General Inquiry'

    if not agent_dept:
        agent_dept = 'General Inquiry'

    # Build dynamic SQL query with optional status filter
    sql = """
        SELECT c.*, u.custname as customer_name, u.email as customer_email,
               d.deptname as department_name
        FROM complaints c
        JOIN customers u ON c.custid = u.custid
        LEFT JOIN departments d ON c.deptid = d.deptid
    """
    params = []

    # Only filter by department if agent has a deptid and is not an admin
    user_role = str(g.user.get('role', '')).lower().strip()
    if agent_deptid and user_role != 'admin':
        sql += " WHERE c.deptid = ?"
        params.append(agent_deptid)

    if status_filter != 'all':
        sql += " AND c.status = ?" if (agent_deptid and user_role != 'admin') else " WHERE c.status = ?"
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
                SUM(status = 'Resolved') as count_resolved,
                ROUND(AVG(satisfaction_score), 1) as avg_csat
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
                SUM(status = 'Resolved') as count_resolved,
                ROUND(AVG(satisfaction_score), 1) as avg_csat
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


@app.route('/api/ticket/<string:ticket_id>')
@app.route('/api/tickets/<string:ticket_id>', endpoint='get_ticket_details_plural')
@login_required
def get_ticket_details(ticket_id):
    """
    Unified ticket details endpoint for all roles (Customer, Agent, Admin).
    - Returns JSON with complete ticket information, replies, and similar matches.
    - Accepts ticket_id as string (e.g. 'TKT-313681' or '313681').
    - Dual-table schema: uses customers and department_agents tables.
    - Permission checks: admin, ticket owner, assigned agent, or department agent.
    - Null-safe queries: handles missing agents, customers, or resolved status gracefully.
    """
    user_role = str(g.user.get('role', '')).lower().strip()
    agent_id = g.user.get('agent_id') or g.user.get('user_id')
    cust_id = g.user.get('custid') or g.user.get('user_id')
    agent_deptid = g.user.get('deptid')

    clean_id = str(ticket_id).strip()
    numeric_id = clean_id.upper().replace('TKT-', '').strip()
    alt_id = f"TKT-{numeric_id}"

    # Step 1: Fetch ticket with safe LEFT JOINs on dual-table schema
    ticket = query_db(
        """SELECT t.*, t.ticketno AS ticket_id, t.custid AS customer_id,
                  COALESCE(cust.custname, 'Customer Client') AS customer_name,
                  COALESCE(cust.email, 'customer@compassiq.com') AS customer_email,
                  COALESCE(d.deptname, 'General Inquiry') AS department_name,
                  COALESCE(t.predicted_category, COALESCE(d.deptname, 'General Inquiry')) AS predicted_category,
                  COALESCE(t.predicted_priority, 'Medium') AS predicted_priority,
                  COALESCE(t.status, 'Submitted') AS status,
                  COALESCE(a.agent_name, 'Unassigned') AS assigned_agent_name
           FROM complaints t
           LEFT JOIN customers cust ON t.custid = cust.custid
           LEFT JOIN departments d ON t.deptid = d.deptid
           LEFT JOIN department_agents a ON t.assigned_agent_id = a.agent_id
           WHERE (t.ticketno = ? OR t.ticketno = ? OR LOWER(t.ticketno) = LOWER(?) OR LOWER(t.ticketno) = LOWER(?))""",
        (clean_id, alt_id, clean_id, alt_id),
        one=True
    )

    if not ticket:
        return jsonify({
            'success': False,
            'status': 'error',
            'error': 'Not Found',
            'message': f"Ticket '{ticket_id}' not found in database."
        }), 404

    # Step 2: Permission verification
    ticket_deptid = ticket.get('deptid')
    assigned_agent = ticket.get('assigned_agent_id')
    ticket_custid = ticket.get('custid')

    has_permission = (
        user_role == 'admin' or
        (user_role == 'customer' and str(ticket_custid) == str(cust_id)) or
        (assigned_agent and str(assigned_agent) == str(agent_id)) or
        (agent_deptid and ticket_deptid and str(agent_deptid).strip() == str(ticket_deptid).strip())
    )

    if not has_permission:
        return jsonify({
            'success': False,
            'status': 'error',
            'error': 'Unauthorized',
            'message': 'Access denied: You do not have permission to view this ticket.'
        }), 403

    # Step 3: Fetch conversation replies (from both customers and department_agents)
    replies = query_db(
        """SELECT r.*, r.ticketno AS ticket_id,
                  COALESCE(cust.custname, a.agent_name, 'Support User') AS sender_name,
                  CASE
                    WHEN cust.custid IS NOT NULL THEN 'customer'
                    WHEN a.agent_id IS NOT NULL THEN COALESCE(a.role, 'agent')
                    ELSE 'agent'
                  END AS sender_role
           FROM ticket_replies r
           LEFT JOIN customers cust ON r.sender_id = cust.custid
           LEFT JOIN department_agents a ON r.sender_id = a.agent_id
           WHERE (r.ticketno = ? OR r.ticketno = ? OR LOWER(r.ticketno) = LOWER(?) OR LOWER(r.ticketno) = LOWER(?))
           ORDER BY r.created_at ASC""",
        (clean_id, alt_id, clean_id, alt_id)
    ) or []

    # Step 4: Fetch similar historical tickets (top 3)
    similar_matches = query_db(
        """SELECT match_id, ticketno, ticketno AS ticket_id,
                  similar_ticket_ref_id, similarity_score, similar_subject,
                  similar_description, historical_resolution_hours
           FROM ticket_similar_matches
           WHERE (ticketno = ? OR ticketno = ? OR LOWER(ticketno) = LOWER(?) OR LOWER(ticketno) = LOWER(?))
           ORDER BY similarity_score DESC
           LIMIT 3""",
        (clean_id, alt_id, clean_id, alt_id)
    ) or []

    # If no similarity matches were previously stored, dynamically retrieve them using AI engine
    if not similar_matches:
        try:
            ai_retrieval = predict_and_retrieve(
                ticket.get('subject', '') or '',
                ticket.get('description', '') or '',
                top_k=3
            )
            for sim in ai_retrieval.get('similar_tickets', []):
                similar_matches.append({
                    'ticketno': ticket.get('ticketno') or clean_id,
                    'ticket_id': ticket.get('ticketno') or clean_id,
                    'similar_ticket_ref_id': sim.get('ticket_id', 'HIST-REF'),
                    'similarity_score': float(sim.get('similarity_score', 0.85)),
                    'similar_subject': sim.get('subject', 'Historical Incident'),
                    'similar_description': sim.get('description', ''),
                    'historical_resolution_hours': int(sim.get('resolution_hours', 12) or 12)
                })
        except Exception as sim_err:
            similar_matches = []

    # Step 5: Ensure consistent, fully populated keys and defaults on ticket
    ticket['ticketno'] = ticket.get('ticketno') or clean_id
    ticket['ticket_id'] = ticket['ticketno']
    ticket['customer_id'] = ticket.get('customer_id') or ticket.get('custid')
    ticket['customer_name'] = ticket.get('customer_name') or 'Customer Client'
    ticket['customer_email'] = ticket.get('customer_email') or 'customer@compassiq.com'
    ticket['customer'] = {
        'name': ticket['customer_name'],
        'email': ticket['customer_email']
    }
    ticket['department_name'] = ticket.get('department_name') or 'General Inquiry'
    ticket['assigned_department'] = ticket['department_name']
    ticket['assigned_agent_id'] = ticket.get('assigned_agent_id') or None
    ticket['assigned_agent_name'] = ticket.get('assigned_agent_name') or 'Unassigned'
    ticket['predicted_category'] = ticket.get('predicted_category') or ticket['department_name']
    ticket['predicted_priority'] = ticket.get('predicted_priority') or 'Medium'
    ticket['status'] = ticket.get('status') or 'Submitted'
    ticket['subject'] = ticket.get('subject') or 'No Subject'
    ticket['description'] = ticket.get('description') or ''
    ticket['submitdate'] = ticket.get('submitdate') or 'N/A'
    ticket['created_at'] = ticket.get('created_at') or ticket['submitdate']
    ticket['resolution_notes'] = ticket.get('resolution_notes') or ''
    ticket['satisfaction_score'] = ticket.get('satisfaction_score') or None
    ticket['customer_feedback'] = ticket.get('customer_feedback') or ''

    return jsonify({
        'success': True,
        'status': 'success',
        'user_role': user_role,
        'ticket': ticket,
        'customer': ticket['customer'],
        'replies': replies,
        'similar_matches': similar_matches
    })


@app.route('/agent/tickets/<string:ticket_id>/details', endpoint='agent_ticket_details')
@login_required
def agent_ticket_details(ticket_id):
    """
    Agent ticket details HTML endpoint.
    - Renders the dedicated full-page agent ticket interface.
    - Accepts ticket_id as string (e.g. 'TKT-313681' or '313681').
    - Department guard: allows admin, assigned agent, or agents belonging to ticket department.
    - Safe queries: handles missing/null customer, replies, or AI matches gracefully.
    """
    agent_deptid = g.user.get('deptid') or None
    user_role = str(g.user.get('role', '')).lower().strip()
    agent_id = g.user.get('agent_id') or g.user.get('user_id') or g.user.get('custid')
    agent_dept = str(g.user.get('department') or '').lower().strip()

    clean_id = str(ticket_id).strip()
    numeric_id = clean_id.upper().replace('TKT-', '').strip()
    alt_id = f"TKT-{numeric_id}"

    # Resolve agent_deptid from department name if missing
    if not agent_deptid and agent_dept:
        d_row = query_db(
            """SELECT deptid FROM departments 
               WHERE LOWER(TRIM(deptname)) = LOWER(TRIM(?))
                  OR LOWER(TRIM(deptname)) LIKE LOWER(TRIM(?)) || '%'""",
            (agent_dept, agent_dept),
            one=True
        )
        if d_row:
            agent_deptid = d_row['deptid']

    # Step 1: Fetch ticket with safe LEFT JOINs on customers, department_agents, and departments
    ticket = query_db(
        """SELECT t.*, t.ticketno AS ticket_id, t.custid AS customer_id,
                  COALESCE(c.custname, 'Customer Client') AS customer_name,
                  COALESCE(c.email, 'customer@compassiq.com') AS customer_email,
                  COALESCE(d.deptname, 'General Inquiry') AS department_name,
                  COALESCE(t.predicted_category, COALESCE(d.deptname, 'General Inquiry')) AS predicted_category,
                  COALESCE(t.predicted_priority, 'Medium') AS predicted_priority,
                  COALESCE(t.status, 'Submitted') AS status,
                  COALESCE(a.agent_name, 'Unassigned') AS assigned_agent_name
           FROM complaints t
           LEFT JOIN customers c ON t.custid = c.custid
           LEFT JOIN departments d ON t.deptid = d.deptid
           LEFT JOIN department_agents a ON t.assigned_agent_id = a.agent_id
           WHERE (t.ticketno = ? OR t.ticketno = ? OR LOWER(t.ticketno) = LOWER(?) OR LOWER(t.ticketno) = LOWER(?))""",
        (clean_id, alt_id, clean_id, alt_id),
        one=True
    )

    if not ticket:
        flash(f"Ticket '{ticket_id}' not found.", "warning")
        return redirect(url_for('agent_dashboard'))

    # Step 2: Department Guard / Permission Verification
    ticket_deptid = ticket.get('deptid')
    assigned_agent = ticket.get('assigned_agent_id')
    ticket_deptname = str(ticket.get('department_name') or '').lower().strip()
    ticket_custid = ticket.get('custid')

    has_permission = (
        user_role == 'admin' or
        (user_role == 'customer' and str(ticket_custid) == str(agent_id)) or
        (assigned_agent and str(assigned_agent) == str(agent_id)) or
        (agent_deptid and ticket_deptid and str(agent_deptid).strip() == str(ticket_deptid).strip())
    )

    if not has_permission:
        flash("Access denied: You do not have permission to view tickets outside your department queue.", "danger")
        return redirect(url_for('agent_dashboard'))

    # Step 3: Fetch conversation replies (from both customers and department_agents)
    replies = query_db(
        """SELECT r.*, r.ticketno AS ticket_id,
                  COALESCE(c.custname, a.agent_name, 'Support User') AS sender_name,
                  CASE 
                    WHEN c.custid IS NOT NULL THEN 'customer'
                    WHEN a.agent_id IS NOT NULL THEN COALESCE(a.role, 'agent')
                    ELSE 'agent'
                  END AS sender_role
           FROM ticket_replies r
           LEFT JOIN customers c ON r.sender_id = c.custid
           LEFT JOIN department_agents a ON r.sender_id = a.agent_id
           WHERE (r.ticketno = ? OR r.ticketno = ? OR LOWER(r.ticketno) = LOWER(?) OR LOWER(r.ticketno) = LOWER(?))
           ORDER BY r.created_at ASC""",
        (clean_id, alt_id, clean_id, alt_id)
    ) or []

    # Step 4: Fetch similar historical tickets (top 3)
    similar_matches = query_db(
        """SELECT match_id, ticketno, ticketno AS ticket_id,
                  similar_ticket_ref_id, similarity_score, similar_subject, 
                  similar_description, historical_resolution_hours
           FROM ticket_similar_matches
           WHERE (ticketno = ? OR ticketno = ? OR LOWER(ticketno) = LOWER(?) OR LOWER(ticketno) = LOWER(?))
           ORDER BY similarity_score DESC
           LIMIT 3""",
        (clean_id, alt_id, clean_id, alt_id)
    ) or []

    # If no similarity matches were previously stored, dynamically retrieve them using AI engine
    if not similar_matches:
        try:
            ai_retrieval = predict_and_retrieve(
                ticket.get('subject', '') or '', 
                ticket.get('description', '') or '', 
                top_k=3
            )
            for sim in ai_retrieval.get('similar_tickets', []):
                similar_matches.append({
                    'ticketno': ticket.get('ticketno') or clean_id,
                    'ticket_id': ticket.get('ticketno') or clean_id,
                    'similar_ticket_ref_id': sim.get('ticket_id', 'HIST-REF'),
                    'similarity_score': float(sim.get('similarity_score', 0.85)),
                    'similar_subject': sim.get('subject', 'Historical Incident'),
                    'similar_description': sim.get('description', ''),
                    'historical_resolution_hours': int(sim.get('resolution_hours', 12) or 12)
                })
        except Exception as sim_err:
            similar_matches = []

    # Step 5: Ensure consistent, fully populated keys and defaults on ticket
    ticket['ticketno'] = ticket.get('ticketno') or clean_id
    ticket['ticket_id'] = ticket['ticketno']
    ticket['customer_id'] = ticket.get('customer_id') or ticket.get('custid')
    ticket['customer_name'] = ticket.get('customer_name') or 'Customer Client'
    ticket['customer_email'] = ticket.get('customer_email') or 'customer@compassiq.com'
    ticket['customer'] = {
        'name': ticket['customer_name'],
        'email': ticket['customer_email']
    }
    ticket['department_name'] = ticket.get('department_name') or 'General Inquiry'
    ticket['assigned_department'] = ticket['department_name']
    ticket['assigned_agent_id'] = ticket.get('assigned_agent_id') or None
    ticket['assigned_agent_name'] = ticket.get('assigned_agent_name') or 'Unassigned'
    ticket['predicted_category'] = ticket.get('predicted_category') or ticket['department_name']
    ticket['predicted_priority'] = ticket.get('predicted_priority') or 'Medium'
    ticket['status'] = ticket.get('status') or 'Submitted'
    ticket['subject'] = ticket.get('subject') or 'No Subject'
    ticket['description'] = ticket.get('description') or ''
    ticket['submitdate'] = ticket.get('submitdate') or 'N/A'
    ticket['created_at'] = ticket.get('created_at') or ticket['submitdate']
    ticket['resolution_notes'] = ticket.get('resolution_notes') or ''
    ticket['satisfaction_score'] = ticket.get('satisfaction_score') or None
    ticket['customer_feedback'] = ticket.get('customer_feedback') or ''

    return render_template(
        'agent/ticket_details.html',
        ticket=ticket,
        customer=ticket['customer'],
        replies=replies,
        similar_matches=similar_matches
    )


@app.route('/agent/tickets/<ticket_id>/reply', methods=['POST'])
@app.route('/agent/ticket/<ticket_id>/reply', methods=['POST'])
@app.route('/agent/tickets/<ticket_id>/update', methods=['POST'])
@app.route('/agent/ticket/<ticket_id>/update', methods=['POST'])
@app.route('/agent/tickets/<string:ticket_id>/resolve', methods=['POST'], endpoint='agent_ticket_resolve')
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
    user_id = g.user.get('agent_id') or g.user.get('user_id')
    user_role = str(g.user.get('role', '')).lower().strip()
    agent_dept = str(g.user.get('department') or '').lower().strip()
    resolution_notes = request.form.get('resolution_notes', '').strip()
    message = request.form.get('message', '').strip() or resolution_notes
    new_status = request.form.get('status', '').strip()

    if not resolution_notes or new_status not in ['In Progress', 'Resolved']:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'warning', 'message': 'Resolution notes and a valid status are required.'}), 400
        flash("Resolution notes and a valid status are required.", "warning")
        return redirect(url_for('agent_ticket_details', ticket_id=ticket_id))

    # Step 2: Verify ticket scope
    ticket = query_db(
        """SELECT c.*, d.deptname as department_name 
           FROM complaints c
           LEFT JOIN departments d ON c.deptid = d.deptid
           WHERE (c.ticketno = ? OR c.ticketno = 'TKT-' || ?)""",
        (ticket_id, ticket_id),
        one=True
    )
    if not ticket:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Ticket not found.'}), 404
        flash("Ticket not found in system.", "danger")
        return redirect(url_for('agent_dashboard'))

    ticket_deptid = ticket.get('deptid')
    assigned_agent = ticket.get('assigned_agent_id')
    ticket_deptname = str(ticket.get('department_name') or '').lower().strip()

    has_permission = (
        user_role == 'admin' or
        (assigned_agent and assigned_agent == user_id) or
        (agent_deptid and ticket_deptid and int(agent_deptid) == int(ticket_deptid)) or
        (agent_dept and (agent_dept in ticket_deptname or ticket_deptname in agent_dept))
    )

    if not has_permission:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'status': 'error', 'message': 'Access denied: Outside assigned department.'}), 403
        flash("Access denied: You do not have permission to update tickets outside your department queue.", "danger")
        return redirect(url_for('agent_dashboard'))

    # Step 3: Insert reply if provided
    if message:
        modify_db(
            "INSERT INTO ticket_replies (ticketno, sender_id, message, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (ticket['ticketno'], user_id, message)
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

    if new_status == 'In Progress':
        update_fields.append("resolved_at = NULL")

    if update_fields:
        update_fields.append("assigned_agent_id = ?")
        params.append(user_id)
        params.append(ticket['ticketno'])
        modify_db(
            f"UPDATE complaints SET {', '.join(update_fields)} WHERE ticketno = ?",
            tuple(params)
        )

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'message': f"Ticket {ticket['ticketno']} updated successfully."})

    flash("Ticket has been updated/resolved successfully.", "success")
    if request.endpoint == 'agent_ticket_resolve':
        return redirect(url_for('agent_ticket_details', ticket_id=ticket['ticketno']))
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

    # Step 2: Fetch category distribution for analytics (all departments)
    dept_stats = query_db(
        """SELECT d.deptname as assigned_department, COUNT(c.ticketno) as count
           FROM departments d
           LEFT JOIN complaints c ON d.deptid = c.deptid
           GROUP BY d.deptid, d.deptname
           ORDER BY d.deptid ASC"""
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
           """SELECT ticketno, subject, d.deptname as category, predicted_priority,
                   CASE WHEN c.status IN ('Resolved', 'Closed')
                       THEN 'Solved' ELSE 'Pending' END as admin_status,
                   submitdate
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


@app.route('/admin/users')
@admin_required
def admin_users_page():
    """Admin User Management page view."""
    return redirect(url_for('admin_dashboard') + '#staff-management-card')


@app.route('/admin/users/<int:user_id>/delete', methods=['POST', 'DELETE'])
@app.route('/admin/user/<int:user_id>/delete', methods=['POST', 'DELETE'])
@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_delete_user(user_id):
    """
    Admin user deletion endpoint.
    - Safety Check: Prevents active logged-in admin from deleting their own account.
    - Database Constraints: Safely reassigns or cascades tickets and replies without foreign key crashes.
    - Supports deleting customers or department agents.
    """
    user_type = (request.form.get('user_type') or request.args.get('user_type') or '').strip().lower()
    current_admin_id = g.user.get('agent_id') or g.user.get('user_id')
    current_admin_email = str(g.user.get('email', '')).lower().strip()

    target_agent = None
    target_customer = None

    if user_type in ['agent', 'admin']:
        target_agent = query_db("SELECT * FROM department_agents WHERE agent_id = ?", (user_id,), one=True)
    elif user_type == 'customer':
        target_customer = query_db("SELECT * FROM customers WHERE custid = ?", (user_id,), one=True)
    else:
        # Auto-detect from department_agents first, then customers
        target_agent = query_db("SELECT * FROM department_agents WHERE agent_id = ?", (user_id,), one=True)
        if not target_agent:
            target_customer = query_db("SELECT * FROM customers WHERE custid = ?", (user_id,), one=True)

    if not target_agent and not target_customer:
        if request.is_json or request.method == 'DELETE':
            return jsonify({'status': 'error', 'message': f'User #{user_id} not found.'}), 404
        flash(f"User #{user_id} not found in database.", "warning")
        return redirect(url_for('admin_dashboard'))

    # Safety Check: Cannot delete self
    if target_agent:
        target_email = str(target_agent.get('email', '')).lower().strip()
        if target_agent['agent_id'] == current_admin_id or target_email == current_admin_email:
            if request.is_json or request.method == 'DELETE':
                return jsonify({'status': 'error', 'message': 'Security Alert: You cannot delete your own active administrator account.'}), 400
            flash("Security Alert: You cannot delete your own active administrator account.", "danger")
            return redirect(url_for('admin_dashboard'))

        agent_name = target_agent['agent_name']
        
        # Handle constraints: Reassign open complaints assigned to this agent to NULL
        modify_db("UPDATE complaints SET assigned_agent_id = NULL WHERE assigned_agent_id = ?", (user_id,))
        
        # Reassign replies sent by this agent to active admin
        modify_db("UPDATE ticket_replies SET sender_id = ? WHERE sender_id = ?", (current_admin_id, user_id))
        
        # Delete agent
        modify_db("DELETE FROM department_agents WHERE agent_id = ?", (user_id,))
        
        if request.is_json or request.method == 'DELETE':
            return jsonify({'status': 'success', 'message': f"Staff member '{agent_name}' deleted successfully."})
        flash(f"Staff member '{agent_name}' (ID #{user_id}) deleted successfully.", "success")

    elif target_customer:
        customer_name = target_customer['custname']
        
        # Handle constraints: Find fallback customer for ticket remapping or cascade clean
        fallback_cust = query_db("SELECT custid FROM customers WHERE custid != ? LIMIT 1", (user_id,), one=True)
        if fallback_cust:
            modify_db("UPDATE complaints SET custid = ? WHERE custid = ?", (fallback_cust['custid'], user_id))
            modify_db("UPDATE ticket_replies SET sender_id = ? WHERE sender_id = ?", (fallback_cust['custid'], user_id))
        else:
            modify_db("DELETE FROM ticket_similar_matches WHERE ticketno IN (SELECT ticketno FROM complaints WHERE custid = ?)", (user_id,))
            modify_db("DELETE FROM ticket_replies WHERE ticketno IN (SELECT ticketno FROM complaints WHERE custid = ?)", (user_id,))
            modify_db("DELETE FROM complaints WHERE custid = ?", (user_id,))

        modify_db("DELETE FROM customers WHERE custid = ?", (user_id,))
        
        if request.is_json or request.method == 'DELETE':
            return jsonify({'status': 'success', 'message': f"Customer '{customer_name}' deleted successfully."})
        flash(f"Customer '{customer_name}' (ID #{user_id}) deleted successfully.", "success")

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
