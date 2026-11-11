from app.agents.student_agent import analyze_student_performance


sample_data = {
    "course": "Machine Learning Algorithms",
    "course_code": "22UAI608C",
    "semester": "VI",
    "academic_year": "2025-26",

    "students": [
        {
            "student_id": "S001",
            "CIE-I": 16,
            "CIE-II": 14,
            "Micro Project": 8
        },
        {
            "student_id": "S002",
            "CIE-I": 12,
            "CIE-II": 17,
            "Micro Project": 9
        },
        {
            "student_id": "S003",
            "CIE-I": 18,
            "CIE-II": 16,
            "Micro Project": 7
        }
    ]
}


result = analyze_student_performance(sample_data)


print("\n===== STUDENT AGENT RESULT =====\n")
print(result)