from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os
from datetime import datetime

if not os.path.exists('database.db'):
    from init_db import init_db
    init_db()

app = Flask(__name__)
app.secret_key = 'secretkey'

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return redirect('/notice_board')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']  # 'student' or 'faculty'

        conn = get_db()

        # 🔎 Check if email already exists
        existing_user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if existing_user:
            return render_template('register.html', error="Email is already registered.")

        # ✅ If new email, insert
        conn.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                     (name, email, password, role))
        conn.commit()
        return redirect(f'/login/{role}')

    return render_template('register.html')


@app.route('/login/<role>', methods=['GET', 'POST'])
def login_role(role):
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()

        # Fetch user by email only
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

        if not user:
            return render_template('login.html', error='Email not found')

        if user['password'] != password:
            return render_template('login.html', error='Incorrect password')

        if user['role'] != role:
            return render_template('login.html', error=f"You are not authorized to log in as a {role}.")

        # Valid login
        session['user_id'] = user['id']
        session['role'] = role
        return redirect(f'/dashboard/{role}')

    return render_template('login.html')




@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect('/dashboard/admin')
    return render_template('admin_login.html')

@app.route('/dashboard/faculty')
def dashboard_faculty():
    if session.get('role') != 'faculty':
        return redirect('/login/faculty')
    conn = get_db()
    notices = conn.execute("SELECT * FROM notices WHERE user_id=?", (session['user_id'],)).fetchall()
    return render_template('dashboard.html', notices=notices, role='faculty')

@app.route('/dashboard/student')
def dashboard_student():
    if session.get('role') != 'student':
        return redirect('/login/student')
    conn = get_db()
    notices = conn.execute("""
        SELECT notices.*, users.name FROM notices 
        JOIN users ON notices.user_id = users.id 
        WHERE status = 'approved'
    """).fetchall()
    return render_template('dashboard.html', notices=notices, role='student')

@app.route('/submit_notice', methods=['POST'])
def submit_notice():
    if 'user_id' in session and session.get('role') == 'faculty':
        title = request.form['title']
        content = request.form['content']
        post_date = datetime.now().strftime("%Y-%m-%d")
        conn = get_db()
        conn.execute(
            "INSERT INTO notices (title, content, user_id, status, post_date) VALUES (?, ?, ?, 'pending', ?)",
            (title, content, session['user_id'], post_date)
        )
        conn.commit()
    return redirect('/dashboard/faculty')

@app.route('/dashboard/admin')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/login/admin')
    conn = get_db()
    notices = conn.execute("""
        SELECT notices.*, users.name 
        FROM notices 
        JOIN users ON notices.user_id = users.id
    """).fetchall()
    return render_template('admin_dashboard.html', notices=notices)

@app.route('/approve/<int:notice_id>')
def approve_notice(notice_id):
    if 'admin' in session:
        conn = get_db()
        conn.execute("UPDATE notices SET status='approved' WHERE id=?", (notice_id,))
        conn.commit()
    return redirect('/dashboard/admin')

@app.route('/reject/<int:notice_id>')
def reject_notice(notice_id):
    if 'admin' in session:
        conn = get_db()
        conn.execute("UPDATE notices SET status='rejected' WHERE id=?", (notice_id,))
        conn.commit()
    return redirect('/dashboard/admin')

@app.route('/delete/<int:notice_id>')
def delete_notice(notice_id):
    if 'admin' in session:
        conn = get_db()
        conn.execute("DELETE FROM notices WHERE id=?", (notice_id,))
        conn.commit()
    return redirect('/dashboard/admin')

@app.route('/notice_board')
def notice_board():
    conn = get_db()
    notices = conn.execute("""
        SELECT notices.*, users.name 
        FROM notices 
        JOIN users ON notices.user_id = users.id 
        WHERE status = 'approved'
    """).fetchall()
    return render_template('notice_board.html', notices=notices)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/add_notice', methods=['GET', 'POST'])
def add_notice():
    if 'user_id' not in session or session.get('role') != 'faculty':
        return redirect('/login/faculty')

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        post_date = datetime.now().strftime("%Y-%m-%d")
        conn = get_db()
        conn.execute(
            "INSERT INTO notices (title, content, user_id, status, post_date) VALUES (?, ?, ?, 'pending', ?)",
            (title, content, session['user_id'], post_date)
        )
        conn.commit()
        return redirect('/dashboard/faculty')

    return render_template('add_notice.html')

if __name__ == '__main__':
    app.run(debug=True)

