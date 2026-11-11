from app.agents.assessment_agent import analyze_assessment


sample_data = {
    "course": "Machine Learning Algorithms",
    "course_code": "22UAI608C",
    "semester": "VI",
    "academic_year": "2025-26",
    "assessments": {
        "CIE-I": 20,
        "CIE-II": 20,
        "Micro Project": 10,
        "SEE": 50,
        "Total": 100
    }
}


result = analyze_assessment(sample_data)


print("\n===== ASSESSMENT AGENT RESULT =====\n")
print(result)