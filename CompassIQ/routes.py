import csv
import io
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from werkzeug.security import generate_password_hash, check_password_hash

from .database import get_db_connection, init_db
from .ml_engine import DEPARTMENT_LABELS, get_ml_engine

app = Flask(__name__)
app.config.update(
    SECRET_KEY='compassiq_secret_key_prod_2026',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

# Ensure database schema is initialized on startup
init_db()

# Access pre-trained ML Engine singleton instance (loads pre-trained models immediately)
ml_engine = get_ml_engine()

NO_CACHE_HEADERS = {
    'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
    'Pragma': 'no-cache',
    'Expires': '0'
}

@app.after_request
def prevent_authenticated_page_caching(response):
    for header, value in NO_CACHE_HEADERS.items():
        response.headers[header] = value
    return response

def get_ticket_assignment(predicted_category, conn):
    """Map the ML category to an operational queue and its agent, if applicable."""
    assigned_department = DEPARTMENT_LABELS.get(predicted_category, 'General Inquiry')
    if assigned_department == 'Admin':
        return assigned_department, None, 'Administrator'

    agent = conn.execute(
        "SELECT id, name FROM users WHERE role = 'agent' AND department = ? ORDER BY id LIMIT 1",
        (predicted_category,)
    ).fetchone()
    if agent:
        return assigned_department, agent['id'], agent['name']
    return assigned_department, None, f'{assigned_department} Queue'

def agent_can_access_ticket(ticket):
    return (
        session.get('user_role') == 'admin'
        or ticket['assigned_department'] == DEPARTMENT_LABELS.get(session.get('user_department'), session.get('user_department'))
    )

def customer_can_access_ticket(ticket):
    return (
        ticket['customer_id'] == session.get('user_id')
        or ticket['customer_email'] == session.get('user_email')
    )

# Helper decorator for role checking
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if role and session.get('user_role') != role and session.get('user_role') != 'admin':
                flash('Unauthorized access privileges.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Root Route ---
@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif role == 'agent':
            return redirect(url_for('agent_dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

# --- Auth Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        dept_form = request.form.get('department', '').strip()

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']

            # Set user department classification for agents
            dept = user['department'] or dept_form or 'Technical'
            session['user_department'] = dept

            flash(f"Welcome back, {user['name']}!", 'success')

            if user['role'] == 'customer':
                return redirect(url_for('customer_dashboard'))
            elif user['role'] == 'agent':
                return redirect(url_for('agent_dashboard'))
            else:
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        role = request.form.get('role', 'customer')
        department = request.form.get('department', 'Technical') if role == 'agent' else None
        password = request.form.get('password', '').strip()

        if not name or not email or not password:
            flash('Please fill in all required fields.', 'warning')
            return redirect(url_for('register'))

        conn = get_db_connection()
        existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            conn.close()
            flash('Account with this email already exists.', 'warning')
            return redirect(url_for('login'))

        pwd_hash = generate_password_hash(password)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, department)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, pwd_hash, role, department))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        session['user_role'] = role
        session['user_department'] = department or 'Technical'

        flash('Account created successfully!', 'success')

        if role == 'customer':
            return redirect(url_for('customer_dashboard'))
        else:
            return redirect(url_for('agent_dashboard'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Customer Module Routes ---
@app.route('/customer/dashboard')
@login_required('customer')
def customer_dashboard():
    conn = get_db_connection()
    c_email = session.get('user_email')
    
    tickets = conn.execute('''
        SELECT * FROM tickets 
        WHERE customer_email = ? OR customer_id = ? 
        ORDER BY id DESC
    ''', (c_email, session.get('user_id'))).fetchall()

    stats = {
        'total': len(tickets),
        'open': sum(1 for t in tickets if t['status'] == 'Open'),
        'in_progress': sum(1 for t in tickets if t['status'] == 'In Progress'),
        'resolved': sum(1 for t in tickets if t['status'] in ['Resolved', 'Closed'])
    }
    conn.close()
    return render_template('customer_dashboard.html', tickets=tickets, stats=stats)

@app.route('/customer/tickets/new', methods=['GET', 'POST'])
@login_required('customer')
def create_ticket():
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        channel = request.form.get('channel', 'Web')

        if not subject or not description:
            flash('Subject and description are required.', 'warning')
            return redirect(url_for('create_ticket'))

        # Run Pre-Trained Machine Learning Inference
        pred = ml_engine.predict_ticket(subject, description)
        similar = ml_engine.find_similar_tickets(subject, description, top_n=3)

        conn = get_db_connection()
        cursor = conn.cursor()

        count = cursor.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
        ticket_code = f"TKT-{100000 + count + 1}"
        assigned_department, assigned_agent_id, assigned_agent_name = get_ticket_assignment(pred['category'], conn)

        cursor.execute('''
            INSERT INTO tickets (
                ticket_code, customer_id, customer_name, customer_email, subject, description,
                category, predicted_category, category_confidence,
                priority, predicted_priority, priority_confidence,
                channel, status, assigned_department, assigned_agent_id, assigned_agent_name, submission_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticket_code, session.get('user_id'), session.get('user_name'), session.get('user_email'),
            subject, description, pred['category'], pred['category'], pred['category_confidence'],
            pred['priority'], pred['priority'], pred['priority_confidence'],
            channel, 'Open', assigned_department, assigned_agent_id, assigned_agent_name,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        ticket_id = cursor.lastrowid

        sim_ids = ",".join([s['ticket_id'] for s in similar])
        cursor.execute('''
            INSERT INTO predictions_log (ticket_code, predicted_category, category_confidence, predicted_priority, priority_confidence, similar_ticket_ids)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ticket_code, pred['category'], pred['category_confidence'], pred['priority'], pred['priority_confidence'], sim_ids))

        conn.commit()
        conn.close()

        flash(f"Ticket {ticket_code} submitted! Automatically routed to {assigned_department}.", 'success')
        return redirect(url_for('customer_ticket_detail', ticket_id=ticket_id))

    return render_template('create_ticket.html')

@app.route('/customer/tickets/<int:ticket_id>')
@login_required('customer')
def customer_ticket_detail(ticket_id):
    conn = get_db_connection()
    ticket = conn.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    if not ticket or not customer_can_access_ticket(ticket):
        conn.close()
        flash('Ticket not found.', 'danger')
        return redirect(url_for('customer_dashboard'))

    comments = conn.execute('''
        SELECT * FROM ticket_comments 
        WHERE ticket_id = ? AND is_internal = 0 
        ORDER BY id ASC
    ''', (ticket_id,)).fetchall()

    conn.close()
    return render_template('customer_ticket_detail.html', ticket=ticket, comments=comments)

@app.route('/customer/tickets/<int:ticket_id>/close', methods=['POST'])
@login_required('customer')
def close_customer_ticket(ticket_id):
    rating = max(1, min(5, int(request.form.get('rating', 5))))
    feedback = request.form.get('feedback', '').strip()

    conn = get_db_connection()
    ticket = conn.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    if not ticket or not customer_can_access_ticket(ticket):
        conn.close()
        flash('Ticket not found.', 'danger')
        return redirect(url_for('customer_dashboard'))
    conn.execute('''
        UPDATE tickets 
        SET status = 'Closed', satisfaction_score = ?, feedback = ? 
        WHERE id = ?
    ''', (rating, feedback, ticket_id))
    conn.commit()
    conn.close()

    flash('Thank you for rating your support experience!', 'success')
    return redirect(url_for('customer_ticket_detail', ticket_id=ticket_id))

@app.route('/customer/tickets/<int:ticket_id>/comment', methods=['POST'])
@login_required()
def add_ticket_comment(ticket_id):
    comment_text = request.form.get('comment_text', '').strip()
    if comment_text:
        conn = get_db_connection()
        ticket = conn.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
        if not ticket or not customer_can_access_ticket(ticket):
            conn.close()
            flash('Ticket not found.', 'danger')
            return redirect(url_for('customer_dashboard'))
        conn.execute('''
            INSERT INTO ticket_comments (ticket_id, author_id, author_name, author_role, comment_text, is_internal)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', (ticket_id, session.get('user_id'), session.get('user_name'), session.get('user_role'), comment_text))
        conn.commit()
        conn.close()
        flash('Reply posted successfully.', 'success')
    return redirect(request.referrer or url_for('customer_dashboard'))

# --- Department Module Routes ---
@app.route('/agent/dashboard')
@login_required('agent')
def agent_dashboard():
    conn = get_db_connection()
    user_dept = session.get('user_department', 'Technical')
    department_label = DEPARTMENT_LABELS.get(user_dept, user_dept)

    # Strictly filter tickets matching agent's assigned department
    if session.get('user_role') == 'admin':
        tickets = conn.execute('SELECT * FROM tickets ORDER BY id DESC').fetchall()
    else:
        tickets = conn.execute('SELECT * FROM tickets WHERE assigned_department = ? ORDER BY id DESC', (department_label,)).fetchall()

    stats = {
        'total_assigned': len(tickets),
        'open': sum(1 for t in tickets if t['status'] == 'Open'),
        'in_progress': sum(1 for t in tickets if t['status'] == 'In Progress'),
        'resolved': sum(1 for t in tickets if t['status'] in ['Resolved', 'Closed'])
    }
    conn.close()
    return render_template('agent_dashboard.html', tickets=tickets, stats=stats, user_dept=user_dept, department_label=department_label)

@app.route('/agent/tickets/<int:ticket_id>')
@login_required('agent')
def agent_ticket_detail(ticket_id):
    conn = get_db_connection()
    ticket = conn.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    if not ticket:
        conn.close()
        flash('Ticket not found.', 'danger')
        return redirect(url_for('agent_dashboard'))
    if not agent_can_access_ticket(ticket):
        flash('This ticket is assigned to another department.', 'danger')
        return redirect(url_for('agent_dashboard'))

    comments = conn.execute('SELECT * FROM ticket_comments WHERE ticket_id = ? ORDER BY id ASC', (ticket_id,)).fetchall()
    conn.close()

    pred = ml_engine.predict_ticket(ticket['subject'], ticket['description'])
    similar = ml_engine.find_similar_tickets(ticket['subject'], ticket['description'], top_n=3)
    rec = ml_engine.generate_solution_recommendation(similar, ticket['category'])

    return render_template(
        'agent_ticket_detail.html',
        ticket=ticket,
        comments=comments,
        predictions=pred,
        similar_tickets=similar,
        recommendation=rec
    )

@app.route('/agent/tickets/<int:ticket_id>/respond', methods=['POST'])
@login_required('agent')
def agent_respond_ticket(ticket_id):
    response_text = request.form.get('response_text', '').strip()
    status = request.form.get('status', 'In Progress')
    is_internal = 1 if request.form.get('is_internal') == '1' else 0

    if response_text:
        conn = get_db_connection()
        ticket = conn.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
        if not ticket or not agent_can_access_ticket(ticket):
            conn.close()
            flash('This ticket is assigned to another department.', 'danger')
            return redirect(url_for('agent_dashboard'))
        conn.execute('''
            INSERT INTO ticket_comments (ticket_id, author_id, author_name, author_role, comment_text, is_internal)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ticket_id, session.get('user_id'), session.get('user_name'), 'agent', response_text, is_internal))

        conn.execute('UPDATE tickets SET status = ?, resolution_notes = ? WHERE id = ?', (status, response_text, ticket_id))
        conn.commit()
        conn.close()

        flash(f"Response saved and ticket status updated to '{status}'.", 'success')

    return redirect(url_for('agent_ticket_detail', ticket_id=ticket_id))

# --- Administrator Module Routes (Streamlined to Presentation Requirements) ---
@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    conn = get_db_connection()
    total_tickets = conn.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    open_tickets = conn.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Open'").fetchone()[0]
    in_progress = conn.execute("SELECT COUNT(*) FROM tickets WHERE status = 'In Progress'").fetchone()[0]
    resolved_tickets = conn.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Resolved', 'Closed')").fetchone()[0]
    total_agents = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'agent'").fetchone()[0]
    fraud_tickets = conn.execute("SELECT COUNT(*) FROM tickets WHERE assigned_department = 'Admin'").fetchone()[0]
    tickets = conn.execute('SELECT * FROM tickets ORDER BY id DESC').fetchall()

    # Department performance metrics
    agent_rows = conn.execute("SELECT id, name, email, department FROM users WHERE role = 'agent'").fetchall()
    dept_stats = []
    for agent in agent_rows:
        dept = agent['department'] or 'Technical'
        assigned_department = DEPARTMENT_LABELS.get(dept, dept)
        assigned = conn.execute('SELECT COUNT(*) FROM tickets WHERE assigned_department = ?', (assigned_department,)).fetchone()[0]
        resolved = conn.execute("SELECT COUNT(*) FROM tickets WHERE assigned_department = ? AND status IN ('Resolved', 'Closed')", (assigned_department,)).fetchone()[0]
        dept_stats.append({
            'department': assigned_department,
            'name': agent['name'],
            'email': agent['email'],
            'assigned': assigned,
            'resolved': resolved,
            'avg_res_time': 12.5,
            'satisfaction': 4.9
        })

    conn.close()

    stats = {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'in_progress': in_progress,
        'resolved_tickets': resolved_tickets,
        'total_agents': total_agents
    }
    return render_template('admin_dashboard.html', stats=stats, department_stats=dept_stats, tickets=tickets, fraud_tickets=fraud_tickets)

@app.route('/admin/ai-monitor')
@login_required('admin')
def admin_ai_monitor():
    metrics = ml_engine.metrics
    return render_template('admin_ai_monitor.html', metrics=metrics)

@app.route('/admin/users')
@login_required('admin')
def admin_users():
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required('admin')
def toggle_user_role(user_id):
    new_role = request.form.get('role', 'customer')
    new_dept = request.form.get('department', 'Technical') if new_role == 'agent' else None

    conn = get_db_connection()
    conn.execute('UPDATE users SET role = ?, department = ? WHERE id = ?', (new_role, new_dept, user_id))
    conn.commit()
    conn.close()

    flash(f"User role updated to '{new_role}'.", 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/create', methods=['POST'])
@login_required('admin')
def admin_create_user():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    role = request.form.get('role', 'agent')
    department = request.form.get('department', 'Technical') if role == 'agent' else None
    password = request.form.get('password', 'password123').strip()

    if name and email:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO users (name, email, password_hash, role, department)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, generate_password_hash(password), role, department))
        conn.commit()
        conn.close()

        flash(f"Account for {name} ({role} - {department or 'N/A'}) created successfully!", 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/export/tickets')
@login_required('admin')
def export_tickets_csv():
    conn = get_db_connection()
    tickets = conn.execute('SELECT * FROM tickets ORDER BY id DESC').fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Ticket_Code', 'Customer_Name', 'Customer_Email', 'Subject', 'Category', 
        'Category_Confidence', 'Priority', 'Priority_Confidence', 'Status', 
        'Assigned_Agent', 'Submission_Date', 'Satisfaction_Score'
    ])

    for t in tickets:
        writer.writerow([
            t['ticket_code'], t['customer_name'], t['customer_email'], t['subject'],
            t['category'], t['category_confidence'], t['priority'], t['priority_confidence'],
            t['status'], t['assigned_agent_name'], t['submission_date'], t['satisfaction_score']
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=CompassIQ_System_Report.csv"}
    )

# --- Knowledge Base Routes ---
@app.route('/kb')
def knowledge_base():
    conn = get_db_connection()
    articles = conn.execute('SELECT * FROM knowledge_base ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('knowledge_base.html', articles=articles)

@app.route('/kb/create', methods=['GET', 'POST'])
@login_required()
def create_kb_article_page():
    if request.method == 'POST':
        return create_kb_article()
    return redirect(url_for('knowledge_base'))

@app.route('/kb/create_submit', methods=['POST'])
@login_required()
def create_kb_article():
    title = request.form.get('title', '').strip()
    category = request.form.get('category', 'Technical')
    problem_desc = request.form.get('problem_description', '').strip()
    solution_steps = request.form.get('solution_steps', '').strip()
    tags = request.form.get('tags', '').strip()

    if title and solution_steps:
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO knowledge_base (title, category, problem_description, solution_steps, author_agent, tags)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, category, problem_desc, solution_steps, session.get('user_name'), tags))
        conn.commit()
        conn.close()

        flash('Knowledge base article published successfully!', 'success')
    return redirect(url_for('knowledge_base'))

# --- REST API Endpoints ---
@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.get_json() or {}
    subject = data.get('subject', '')
    description = data.get('description', '')

    pred = ml_engine.predict_ticket(subject, description)
    similar = ml_engine.find_similar_tickets(subject, description, top_n=3)
    rec = ml_engine.generate_solution_recommendation(similar, pred['category'])

    return jsonify({
        'status': 'success',
        'predictions': pred,
        'similar_tickets': similar,
        'recommendation': rec
    })

@app.route('/api/charts/category-distribution')
def api_category_chart():
    conn = get_db_connection()
    rows = conn.execute('SELECT category, COUNT(*) as cnt FROM tickets GROUP BY category').fetchall()
    conn.close()

    labels = [r['category'] for r in rows]
    counts = [r['cnt'] for r in rows]
    return jsonify({'labels': labels, 'counts': counts})

@app.route('/api/charts/priority-distribution')
def api_priority_chart():
    conn = get_db_connection()
    rows = conn.execute("SELECT priority, COUNT(*) as cnt FROM tickets GROUP BY priority ORDER BY CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END").fetchall()
    conn.close()

    labels = [r['priority'] for r in rows]
    counts = [r['cnt'] for r in rows]
    return jsonify({'labels': labels, 'counts': counts})

