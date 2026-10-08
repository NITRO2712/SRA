import sys
import os

# Ensure D:\Lib\site-packages is in sys.path
sys.path.insert(0, r'D:\Lib\site-packages')
sys.path.insert(0, os.path.dirname(__file__))

import io
import csv
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db_connection, init_db, seed_data
from calc import calculate_student_result, calculate_ranks
from analysis import (
    get_class_full_results,
    get_subject_analysis,
    get_grade_distribution,
    get_class_dashboard_summary
)

app = Flask(__name__)
app.secret_key = 'student_result_analyzer_secret_key_aktu'

# Ensure DB initialized on start
with app.app_context():
    init_db()
    seed_data()

# Helper function to check login
def is_logged_in():
    return 'username' in session

def is_admin_or_teacher():
    return session.get('role') in ['admin', 'teacher']

# Context processor for common template variables
@app.context_processor
def inject_user():
    return dict(
        current_user=session.get('username'),
        user_role=session.get('role'),
        user_roll=session.get('student_roll')
    )

@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    if is_admin_or_teacher():
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('student_result', roll_no=session.get('student_roll')))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        login_type = request.form.get('login_type', 'staff') # 'staff' or 'student'
        
        conn = get_db_connection()
        
        if login_type == 'student':
            # Student can log in with Roll Number directly or password
            student = conn.execute("SELECT * FROM students WHERE roll_no = ?", (username,)).fetchone()
            conn.close()
            if student:
                session['user_id'] = student['student_id']
                session['username'] = student['name']
                session['role'] = 'student'
                session['student_roll'] = student['roll_no']
                flash(f'Welcome {student["name"]}!', 'success')
                return redirect(url_for('student_result', roll_no=student['roll_no']))
            else:
                flash('Student with this Roll Number was not found!', 'danger')
        else:
            # Staff (Admin / Teacher) login
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            conn.close()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash(f'Logged in successfully as {user["username"].capitalize()} ({user["role"].capitalize()})', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid Username or Password for Staff login!', 'danger')
                
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not is_logged_in() or not is_admin_or_teacher():
        flash('Access restricted to teachers and administrators.', 'warning')
        return redirect(url_for('login'))
        
    summary = get_class_dashboard_summary()
    results = get_class_full_results()
    top_5 = results[:5] if results else []
    
    return render_template('dashboard.html', summary=summary, top_5=top_5)

@app.route('/students')
def manage_students():
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()
    if search_query:
        students = conn.execute(
            "SELECT * FROM students WHERE name LIKE ? OR roll_no LIKE ? OR branch LIKE ?",
            (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%')
        ).fetchall()
    else:
        students = conn.execute("SELECT * FROM students ORDER BY roll_no ASC").fetchall()
    conn.close()
    
    return render_template('students.html', students=students, search_query=search_query)

@app.route('/students/add', methods=['POST'])
def add_student():
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    roll_no = request.form.get('roll_no', '').strip()
    name = request.form.get('name', '').strip()
    branch = request.form.get('branch', 'CSE').strip()
    semester = request.form.get('semester', 4, type=int)
    
    if not roll_no or not name:
        flash('Roll Number and Name are required fields!', 'danger')
        return redirect(url_for('manage_students'))
        
    conn = get_db_connection()
    # Check duplicate
    existing = conn.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,)).fetchone()
    if existing:
        flash(f'Error: Roll number {roll_no} already exists in database!', 'danger')
        conn.close()
        return redirect(url_for('manage_students'))
        
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO students (roll_no, name, branch, semester) VALUES (?, ?, ?, ?)",
        (roll_no, name, branch, semester)
    )
    # Also add user account for student
    cursor.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (roll_no, generate_password_hash('student123'), 'student')
    )
    conn.commit()
    conn.close()
    
    flash(f'Student {name} ({roll_no}) added successfully!', 'success')
    return redirect(url_for('manage_students'))

@app.route('/students/edit/<int:student_id>', methods=['POST'])
def edit_student(student_id):
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    name = request.form.get('name', '').strip()
    branch = request.form.get('branch', '').strip()
    semester = request.form.get('semester', type=int)
    
    conn = get_db_connection()
    conn.execute(
        "UPDATE students SET name = ?, branch = ?, semester = ? WHERE student_id = ?",
        (name, branch, semester, student_id)
    )
    conn.commit()
    conn.close()
    
    flash('Student details updated successfully.', 'success')
    return redirect(url_for('manage_students'))

@app.route('/students/delete/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()
    
    flash('Student record deleted successfully.', 'info')
    return redirect(url_for('manage_students'))

@app.route('/subjects')
def manage_subjects():
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY subject_code ASC").fetchall()
    conn.close()
    
    return render_template('subjects.html', subjects=subjects)

@app.route('/subjects/add', methods=['POST'])
def add_subject():
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    code = request.form.get('subject_code', '').strip().upper()
    name = request.form.get('subject_name', '').strip()
    internal_max = request.form.get('internal_max', 30, type=int)
    external_max = request.form.get('external_max', 70, type=int)
    credits = request.form.get('credits', 4, type=int)
    max_marks = internal_max + external_max
    
    if not code or not name:
        flash('Subject Code and Name are required!', 'danger')
        return redirect(url_for('manage_subjects'))
        
    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM subjects WHERE subject_code = ?", (code,)).fetchone()
    if existing:
        flash(f'Subject code {code} already exists!', 'danger')
        conn.close()
        return redirect(url_for('manage_subjects'))
        
    conn.execute(
        "INSERT INTO subjects (subject_code, subject_name, max_marks, internal_max, external_max, credits) VALUES (?, ?, ?, ?, ?, ?)",
        (code, name, max_marks, internal_max, external_max, credits)
    )
    conn.commit()
    conn.close()
    
    flash(f'Subject {code} - {name} added successfully!', 'success')
    return redirect(url_for('manage_subjects'))

@app.route('/subjects/edit/<subject_code>', methods=['POST'])
def edit_subject(subject_code):
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    name = request.form.get('subject_name', '').strip()
    internal_max = request.form.get('internal_max', type=int)
    external_max = request.form.get('external_max', type=int)
    credits = request.form.get('credits', type=int)
    max_marks = internal_max + external_max
    
    conn = get_db_connection()
    conn.execute(
        "UPDATE subjects SET subject_name = ?, max_marks = ?, internal_max = ?, external_max = ?, credits = ? WHERE subject_code = ?",
        (name, max_marks, internal_max, external_max, credits, subject_code)
    )
    conn.commit()
    conn.close()
    
    flash('Subject updated successfully.', 'success')
    return redirect(url_for('manage_subjects'))

@app.route('/subjects/delete/<subject_code>', methods=['POST'])
def delete_subject(subject_code):
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conn.execute("DELETE FROM subjects WHERE subject_code = ?", (subject_code,))
    conn.commit()
    conn.close()
    
    flash('Subject deleted successfully.', 'info')
    return redirect(url_for('manage_subjects'))

@app.route('/marks')
def marks_entry():
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    student_id = request.args.get('student_id', type=int)
    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students ORDER BY roll_no ASC").fetchall()
    subjects = conn.execute("SELECT * FROM subjects ORDER BY subject_code ASC").fetchall()
    
    selected_student = None
    existing_marks = {}
    if student_id:
        selected_student = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
        m_rows = conn.execute("SELECT * FROM marks WHERE student_id = ?", (student_id,)).fetchall()
        existing_marks = {m['subject_code']: m for m in m_rows}
        
    conn.close()
    return render_template(
        'marks_entry.html',
        students=students,
        subjects=subjects,
        selected_student=selected_student,
        existing_marks=existing_marks
    )

@app.route('/marks/save', methods=['POST'])
def save_marks():
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    student_id = request.form.get('student_id', type=int)
    if not student_id:
        flash('Please select a student!', 'danger')
        return redirect(url_for('marks_entry'))
        
    conn = get_db_connection()
    subjects = conn.execute("SELECT * FROM subjects").fetchall()
    
    errors = []
    for sub in subjects:
        code = sub['subject_code']
        internal_key = f'internal_{code}'
        external_key = f'external_{code}'
        
        internal_val = request.form.get(internal_key, 0, type=int)
        external_val = request.form.get(external_key, 0, type=int)
        
        # Validation checks against maximum marks
        if internal_val < 0 or internal_val > sub['internal_max']:
            errors.append(f"Internal marks for {code} must be between 0 and {sub['internal_max']}")
        if external_val < 0 or external_val > sub['external_max']:
            errors.append(f"External marks for {code} must be between 0 and {sub['external_max']}")
            
        if not errors:
            total = internal_val + external_val
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO marks (student_id, subject_code, internal_marks, external_marks, total)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(student_id, subject_code) DO UPDATE SET
                    internal_marks = excluded.internal_marks,
                    external_marks = excluded.external_marks,
                    total = excluded.total
            ''', (student_id, code, internal_val, external_val, total))
            
    if errors:
        for err in errors:
            flash(err, 'danger')
        conn.close()
        return redirect(url_for('marks_entry', student_id=student_id))
        
    conn.commit()
    conn.close()
    
    flash('Marks updated and result recalculated successfully!', 'success')
    return redirect(url_for('marks_entry', student_id=student_id))

@app.route('/rank-list')
def rank_list():
    if not is_logged_in():
        return redirect(url_for('login'))
        
    results = get_class_full_results()
    filter_status = request.args.get('status', 'all')
    
    if filter_status == 'pass':
        filtered_results = [s for s in results if s['overall_status'] == 'Pass']
    elif filter_status == 'fail':
        filtered_results = [s for s in results if s['overall_status'] == 'Fail']
    else:
        filtered_results = results
        
    return render_template('rank_list.html', results=filtered_results, filter_status=filter_status)

@app.route('/analysis')
def analysis():
    if not is_logged_in():
        return redirect(url_for('login'))
        
    subject_stats = get_subject_analysis()
    grade_counts = get_grade_distribution()
    summary = get_class_dashboard_summary()
    
    return render_template(
        'analysis.html',
        subject_stats=subject_stats,
        grade_counts=grade_counts,
        summary=summary
    )

@app.route('/student-result')
@app.route('/student-result/<roll_no>')
def student_result(roll_no=None):
    if not roll_no:
        roll_no = request.args.get('roll_no', '').strip()
        
    if not roll_no:
        return render_template('student_result_search.html')
        
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE roll_no = ?", (roll_no,)).fetchone()
    
    if not student:
        flash(f'No student found with Roll Number: {roll_no}', 'danger')
        return render_template('student_result_search.html', searched_roll=roll_no)
        
    # Get all results to find rank
    all_results = get_class_full_results()
    target_result = next((s for s in all_results if s['roll_no'] == roll_no), None)
    
    conn.close()
    return render_template('grade_card.html', student=student, result=target_result)

@app.route('/api/analysis-data')
def api_analysis_data():
    subject_stats = get_subject_analysis()
    grade_counts = get_grade_distribution()
    
    labels = [s['subject_code'] for s in subject_stats]
    averages = [s['avg_marks'] for s in subject_stats]
    highest = [s['highest_marks'] for s in subject_stats]
    lowest = [s['lowest_marks'] for s in subject_stats]
    pass_pcts = [s['pass_percentage'] for s in subject_stats]
    
    return jsonify({
        'subjects': labels,
        'averages': averages,
        'highest': highest,
        'lowest': lowest,
        'pass_pcts': pass_pcts,
        'grades': grade_counts
    })

@app.route('/export-csv')
def export_csv():
    if not is_logged_in() or not is_admin_or_teacher():
        return redirect(url_for('login'))
        
    results = get_class_full_results()
    subject_stats = get_subject_analysis()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Title Header
    writer.writerow(['STUDENT RESULT ANALYZER - CLASS RESULT REPORT'])
    writer.writerow(['AJAY KUMAR GARG ENGINEERING COLLEGE, GHAZIABAD'])
    writer.writerow([])
    
    # Table 1: Student Rank List
    writer.writerow(['RANK', 'ROLL NO', 'STUDENT NAME', 'BRANCH', 'SEMESTER', 'TOTAL OBTAINED', 'MAX MARKS', 'PERCENTAGE (%)', 'SGPA', 'STATUS'])
    for s in results:
        writer.writerow([
            s['rank'],
            s['roll_no'],
            s['name'],
            s['branch'],
            s['semester'],
            s['total_obtained'],
            s['total_max'],
            s['overall_percentage'],
            s['sgpa'],
            s['overall_status']
        ])
        
    writer.writerow([])
    writer.writerow(['SUBJECT-WISE PERFORMANCE SUMMARY'])
    writer.writerow(['SUBJECT CODE', 'SUBJECT NAME', 'AVG MARKS', 'HIGHEST', 'LOWEST', 'PASS (%)'])
    for sub in subject_stats:
        writer.writerow([
            sub['subject_code'],
            sub['subject_name'],
            sub['avg_marks'],
            sub['highest_marks'],
            sub['lowest_marks'],
            sub['pass_percentage']
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=Student_Result_Analysis_Report.csv"}
    )

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
