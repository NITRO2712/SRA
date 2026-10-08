import sys
import os
sys.path.insert(0, r'D:\Lib\site-packages')
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from db import get_db_connection
from calc import calculate_student_result, calculate_ranks

def get_class_full_results():
    """
    Fetches all students, subjects, and marks from DB and computes complete student result list with ranks.
    """
    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students").fetchall()
    subjects = conn.execute("SELECT * FROM subjects").fetchall()
    marks = conn.execute("SELECT * FROM marks").fetchall()
    conn.close()
    
    subjects_dict = {
        sub['subject_code']: {
            'subject_name': sub['subject_name'],
            'max_marks': sub['max_marks'],
            'internal_max': sub['internal_max'],
            'external_max': sub['external_max'],
            'credits': sub['credits']
        } for sub in subjects
    }
    
    # Group marks by student_id
    marks_by_student = {}
    for m in marks:
        sid = m['student_id']
        if sid not in marks_by_student:
            marks_by_student[sid] = []
        marks_by_student[sid].append(m)
        
    student_results = []
    for s in students:
        sid = s['student_id']
        s_marks = marks_by_student.get(sid, [])
        res = calculate_student_result(dict(s), subjects_dict, [dict(m) for m in s_marks])
        student_results.append(res)
        
    ranked_results = calculate_ranks(student_results)
    return ranked_results

def get_subject_analysis():
    """
    Uses Pandas to group marks by subject and calculate mean, max, min, pass % for each subject.
    """
    conn = get_db_connection()
    marks_df = pd.read_sql_query("SELECT m.student_id, m.subject_code, m.total, s.subject_name, s.max_marks FROM marks m JOIN subjects s ON m.subject_code = s.subject_code", conn)
    conn.close()
    
    if marks_df.empty:
        return []
        
    # Calculate subject-wise metrics using Pandas
    subject_stats = []
    for code, group in marks_df.groupby('subject_code'):
        sub_name = group['subject_name'].iloc[0]
        max_possible = group['max_marks'].iloc[0]
        
        avg_total = group['total'].mean()
        max_total = group['total'].max()
        min_total = group['total'].min()
        
        # Pass threshold: >= 40% of max_marks
        pass_cutoff = 0.40 * max_possible
        passed_count = (group['total'] >= pass_cutoff).sum()
        appeared_count = len(group)
        pass_pct = (passed_count / appeared_count * 100) if appeared_count > 0 else 0
        
        subject_stats.append({
            'subject_code': code,
            'subject_name': sub_name,
            'avg_marks': round(float(avg_total), 2),
            'highest_marks': int(max_total),
            'lowest_marks': int(min_total),
            'max_possible': int(max_possible),
            'appeared_count': int(appeared_count),
            'passed_count': int(passed_count),
            'pass_percentage': round(float(pass_pct), 2)
        })
        
    return subject_stats

def get_grade_distribution():
    """
    Computes overall grade counts (O, A+, A, B+, B, C, F) across all student subject scores.
    """
    results = get_class_full_results()
    grade_counts = {'O': 0, 'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C': 0, 'F': 0}
    
    for student in results:
        for sub in student['subject_results']:
            grade = sub['grade']
            if grade in grade_counts:
                grade_counts[grade] += 1
            else:
                grade_counts['F'] += 1
                
    return grade_counts

def get_class_dashboard_summary():
    """
    Generates high-level summary metrics for the Admin Dashboard.
    """
    results = get_class_full_results()
    conn = get_db_connection()
    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    total_subjects = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
    conn.close()
    
    if not results:
        return {
            'total_students': total_students,
            'total_subjects': total_subjects,
            'passed_students': 0,
            'failed_students': 0,
            'overall_pass_pct': 0,
            'avg_class_pct': 0,
            'topper': None
        }
        
    passed_students = sum(1 for s in results if s['overall_status'] == 'Pass')
    failed_students = len(results) - passed_students
    overall_pass_pct = (passed_students / len(results) * 100) if len(results) > 0 else 0
    
    avg_class_pct = sum(s['overall_percentage'] for s in results) / len(results) if results else 0
    topper = results[0] if results else None
    
    return {
        'total_students': total_students,
        'total_subjects': total_subjects,
        'passed_students': passed_students,
        'failed_students': failed_students,
        'overall_pass_pct': round(overall_pass_pct, 2),
        'avg_class_pct': round(avg_class_pct, 2),
        'topper': topper
    }
