import sys
import os
sys.path.insert(0, r'D:\Lib\site-packages')
sys.path.insert(0, os.path.dirname(__file__))

def get_grade_and_point(percentage):
    """
    Determines Letter Grade and Grade Point based on percentage obtained in a subject.
    Scale from Report:
    90+ : O (10)
    80-89: A+ (9)
    70-79: A (8)
    60-69: B+ (7)
    50-59: B (6)
    40-49: C (5)
    Below 40: F (0)
    """
    pct = round(percentage, 2)
    if pct >= 90:
        return 'O', 10
    elif pct >= 80:
        return 'A+', 9
    elif pct >= 70:
        return 'A', 8
    elif pct >= 60:
        return 'B+', 7
    elif pct >= 50:
        return 'B', 6
    elif pct >= 40:
        return 'C', 5
    else:
        return 'F', 0

def calculate_student_result(student_data, subjects_dict, marks_list):
    """
    Calculates detailed result for a single student.
    marks_list is a list of dicts/rows: [{subject_code, internal_marks, external_marks, total}, ...]
    subjects_dict is a dict mapping subject_code -> {subject_name, max_marks, internal_max, external_max, credits}
    """
    subject_results = []
    total_obtained = 0
    total_max = 0
    total_credits = 0
    total_weighted_points = 0
    has_failed_subject = False
    
    for mark in marks_list:
        code = mark['subject_code']
        sub_info = subjects_dict.get(code, {
            'subject_name': code,
            'max_marks': 100,
            'internal_max': 30,
            'external_max': 70,
            'credits': 4
        })
        
        internal = mark['internal_marks']
        external = mark['external_marks']
        total = internal + external
        max_m = sub_info['max_marks']
        credits = sub_info['credits']
        
        pct = (total / max_m * 100) if max_m > 0 else 0
        grade, point = get_grade_and_point(pct)
        
        is_pass = (grade != 'F')
        if not is_pass:
            has_failed_subject = True
            
        subject_results.append({
            'subject_code': code,
            'subject_name': sub_info['subject_name'],
            'internal_marks': internal,
            'external_marks': external,
            'total': total,
            'max_marks': max_m,
            'credits': credits,
            'percentage': round(pct, 2),
            'grade': grade,
            'grade_point': point,
            'status': 'Pass' if is_pass else 'Fail'
        })
        
        total_obtained += total
        total_max += max_m
        total_credits += credits
        total_weighted_points += (credits * point)
        
    overall_percentage = (total_obtained / total_max * 100) if total_max > 0 else 0
    sgpa = (total_weighted_points / total_credits) if total_credits > 0 else 0
    overall_status = 'Pass' if (not has_failed_subject and len(subject_results) > 0) else 'Fail'
    
    return {
        'student_id': student_data['student_id'],
        'roll_no': student_data['roll_no'],
        'name': student_data['name'],
        'branch': student_data['branch'],
        'semester': student_data['semester'],
        'subject_results': subject_results,
        'total_obtained': total_obtained,
        'total_max': total_max,
        'overall_percentage': round(overall_percentage, 2),
        'sgpa': round(sgpa, 2),
        'overall_status': overall_status,
        'total_subjects': len(subject_results)
    }

def calculate_ranks(all_student_results):
    """
    Ranks students based on total_obtained (descending) and sgpa (descending).
    Handles ties by assigning the same rank to equal scores.
    """
    if not all_student_results:
        return []
        
    # Sort students by total_obtained desc, sgpa desc
    sorted_students = sorted(
        all_student_results,
        key=lambda s: (s['total_obtained'], s['sgpa']),
        reverse=True
    )
    
    current_rank = 1
    for i, student in enumerate(sorted_students):
        if i > 0:
            prev = sorted_students[i - 1]
            if student['total_obtained'] == prev['total_obtained'] and student['sgpa'] == prev['sgpa']:
                student['rank'] = prev['rank']
            else:
                student['rank'] = i + 1
        else:
            student['rank'] = 1
            
    return sorted_students
