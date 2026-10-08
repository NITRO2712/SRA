import sys
import os

# Ensure site-packages path if present
if os.path.exists(r'D:\Lib\site-packages'):
    sys.path.insert(0, r'D:\Lib\site-packages')
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from werkzeug.security import generate_password_hash

# Support custom environment variable for database path (e.g., Render persistent disks)
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(__file__), 'student_results.db'))

def get_db_connection():
    # Ensure directory exists if custom path provided
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student'))
        )
    ''')
    
    # 2. Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            branch TEXT NOT NULL,
            semester INTEGER NOT NULL
        )
    ''')
    
    # 3. Subjects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            subject_code TEXT PRIMARY KEY,
            subject_name TEXT NOT NULL,
            max_marks INTEGER NOT NULL DEFAULT 100,
            internal_max INTEGER NOT NULL DEFAULT 30,
            external_max INTEGER NOT NULL DEFAULT 70,
            credits INTEGER NOT NULL DEFAULT 4
        )
    ''')
    
    # 4. Marks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marks (
            mark_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_code TEXT NOT NULL,
            internal_marks INTEGER NOT NULL,
            external_marks INTEGER NOT NULL,
            total INTEGER NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (subject_code) REFERENCES subjects(subject_code) ON DELETE CASCADE,
            UNIQUE(student_id, subject_code)
        )
    ''')
    
    conn.commit()
    conn.close()
    
def seed_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Seed default Admin / Teacher account
    cursor.execute("SELECT * FROM users WHERE username = ?", ('admin',))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ('admin', generate_password_hash('admin123'), 'admin')
        )
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ('teacher', generate_password_hash('teacher123'), 'teacher')
        )

    # Seed AKTU CSE 2nd/3rd Year Subjects
    sample_subjects = [
        ('KCS-401', 'Operating Systems', 100, 30, 70, 4),
        ('KCS-402', 'Theory of Automata', 100, 30, 70, 4),
        ('KCS-403', 'Microprocessor & Interfacing', 100, 30, 70, 3),
        ('KCS-404', 'Database Management Systems', 100, 30, 70, 4),
        ('KCS-405', 'Python Programming', 100, 30, 70, 3),
    ]
    for sub in sample_subjects:
        cursor.execute("SELECT * FROM subjects WHERE subject_code = ?", (sub[0],))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO subjects (subject_code, subject_name, max_marks, internal_max, external_max, credits) VALUES (?, ?, ?, ?, ?, ?)",
                sub
            )
            
    # Seed Sample Students & Marks if none exist
    cursor.execute("SELECT COUNT(*) as cnt FROM students")
    if cursor.fetchone()['cnt'] == 0:
        sample_students = [
            ('2500270120126', 'Rana Aman Singh', 'CSE', 4),
            ('2500270120101', 'Aarav Sharma', 'CSE', 4),
            ('2500270120102', 'Ananya Gupta', 'CSE', 4),
            ('2500270120103', 'Rohan Verma', 'CSE', 4),
            ('2500270120104', 'Priya Patel', 'CSE', 4),
            ('2500270120105', 'Vikram Malhotra', 'CSE', 4),
            ('2500270120106', 'Sneha Kapoor', 'CSE', 4),
            ('2500270120107', 'Aditya Singh', 'CSE', 4),
        ]
        
        student_ids = []
        for roll, name, branch, sem in sample_students:
            cursor.execute(
                "INSERT INTO students (roll_no, name, branch, semester) VALUES (?, ?, ?, ?)",
                (roll, name, branch, sem)
            )
            student_id = cursor.lastrowid
            student_ids.append(student_id)
            # Create student user account
            cursor.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (roll, generate_password_hash('student123'), 'student')
            )
            
        # Sample Marks data
        marks_data = [
            [ (student_ids[0], 'KCS-401', 28, 65), (student_ids[0], 'KCS-402', 29, 66), (student_ids[0], 'KCS-403', 27, 64), (student_ids[0], 'KCS-404', 30, 68), (student_ids[0], 'KCS-405', 29, 67) ],
            [ (student_ids[1], 'KCS-401', 25, 58), (student_ids[1], 'KCS-402', 26, 60), (student_ids[1], 'KCS-403', 24, 55), (student_ids[1], 'KCS-404', 27, 62), (student_ids[1], 'KCS-405', 28, 63) ],
            [ (student_ids[2], 'KCS-401', 26, 62), (student_ids[2], 'KCS-402', 28, 64), (student_ids[2], 'KCS-403', 25, 59), (student_ids[2], 'KCS-404', 28, 65), (student_ids[2], 'KCS-405', 29, 66) ],
            [ (student_ids[3], 'KCS-401', 20, 42), (student_ids[3], 'KCS-402', 22, 45), (student_ids[3], 'KCS-403', 18, 38), (student_ids[3], 'KCS-404', 21, 48), (student_ids[3], 'KCS-405', 23, 50) ],
            [ (student_ids[4], 'KCS-401', 10, 20), (student_ids[4], 'KCS-402', 18, 35), (student_ids[4], 'KCS-403', 16, 30), (student_ids[4], 'KCS-404', 20, 42), (student_ids[4], 'KCS-405', 21, 45) ],
            [ (student_ids[5], 'KCS-401', 22, 50), (student_ids[5], 'KCS-402', 24, 53), (student_ids[5], 'KCS-403', 21, 49), (student_ids[5], 'KCS-404', 23, 54), (student_ids[5], 'KCS-405', 25, 56) ],
            [ (student_ids[6], 'KCS-401', 27, 63), (student_ids[6], 'KCS-402', 28, 65), (student_ids[6], 'KCS-403', 26, 61), (student_ids[6], 'KCS-404', 29, 66), (student_ids[6], 'KCS-405', 28, 64) ],
            [ (student_ids[7], 'KCS-401', 18, 40), (student_ids[7], 'KCS-402', 19, 42), (student_ids[7], 'KCS-403', 17, 39), (student_ids[7], 'KCS-404', 22, 49), (student_ids[7], 'KCS-405', 20, 46) ],
        ]
        
        for student_marks in marks_data:
            for sid, code, internal, external in student_marks:
                cursor.execute(
                    "INSERT INTO marks (student_id, subject_code, internal_marks, external_marks, total) VALUES (?, ?, ?, ?, ?)",
                    (sid, code, internal, external, internal + external)
                )

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    seed_data()
    print("Database initialized and seeded successfully!")
