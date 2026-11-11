criterion3_data = {

    # =========================================================
    # COURSE INFORMATION
    # Source: Guide PDF, pages 5 and 12
    # =========================================================

    "course": {
        "course_name": "Machine Learning Algorithms",
        "course_code": "22UAI608C",
        "semester": "VI",
        "credits": 3,
        "academic_year": "2025-26",
        "department": "Artificial Intelligence and Machine Learning",
        "faculty": "Dr. Bharati M. Reshmi"
    },


    # =========================================================
    # COURSE OUTCOMES
    # Source: Guide PDF, page 5
    # =========================================================

    "course_outcomes": {

        "CO1": (
            "Apply ensemble learning techniques, regularization methods, "
            "Support Vector Machines, and class imbalance handling to "
            "supervised learning problems."
        ),

        "CO2": (
            "Design and implement Artificial Neural Network models using "
            "perceptron and backpropagation, and evaluate model performance "
            "using appropriate metrics and statistical methods."
        ),

        "CO3": (
            "Apply Bayesian learning and instance-based learning techniques "
            "for classification and regression problems."
        ),

        "CO4": (
            "Use dimensionality reduction and clustering techniques to "
            "analyze and interpret high-dimensional datasets."
        )
    },


    # =========================================================
    # ASSESSMENT SCHEME
    # Source: Guide PDF, page 12
    # =========================================================

    "assessment_scheme": {

        "CIE-I": {
            "marks": 20,
            "weightage_percent": 20
        },

        "CIE-II": {
            "marks": 20,
            "weightage_percent": 20
        },

        "Micro Project": {
            "marks": 10,
            "weightage_percent": 10
        },

        "SEE": {
            "marks": 50,
            "weightage_percent": 50
        },

        "Total": {
            "marks": 100,
            "weightage_percent": 100
        }
    },


    # =========================================================
    # MICRO PROJECT
    # Source: Guide PDF, pages 12 and 58
    # =========================================================

    "micro_project": {

        "total_marks": 10,

        "rubric": {
            "Implementation": 6,
            "Report": 2,
            "Viva": 2
        },

        "associated_cos": [
            "CO1",
            "CO2",
            "CO3",
            "CO4"
        ]
    },


    # =========================================================
    # CO-PO-PSO ARTICULATION MATRIX
    # Source: Guide PDF, page 5
    #
    # None means no articulation is shown in the source.
    # =========================================================

    "co_po_pso_mapping": {

        "CO1": {
            "PO1": 3,
            "PO2": 3,
            "PO3": 3,
            "PO4": 2,
            "PO5": 3,
            "PO6": None,
            "PO7": None,
            "PO8": None,
            "PO9": None,
            "PO10": 2,
            "PO11": 1,
            "PSO1": 3,
            "PSO2": 3,
            "PSO3": 3
        },

        "CO2": {
            "PO1": 3,
            "PO2": 3,
            "PO3": 3,
            "PO4": 3,
            "PO5": 3,
            "PO6": None,
            "PO7": None,
            "PO8": None,
            "PO9": 1,
            "PO10": 2,
            "PO11": 2,
            "PSO1": 3,
            "PSO2": 3,
            "PSO3": 2
        },

        "CO3": {
            "PO1": 3,
            "PO2": 3,
            "PO3": 3,
            "PO4": 2,
            "PO5": 2,
            "PO6": None,
            "PO7": None,
            "PO8": None,
            "PO9": 1,
            "PO10": 2,
            "PO11": 2,
            "PSO1": 3,
            "PSO2": 2,
            "PSO3": 2
        },

        "CO4": {
            "PO1": 3,
            "PO2": 3,
            "PO3": 3,
            "PO4": 3,
            "PO5": 3,
            "PO6": None,
            "PO7": None,
            "PO8": None,
            "PO9": 2,
            "PO10": 2,
            "PO11": 2,
            "PSO1": 3,
            "PSO2": 3,
            "PSO3": 2
        }
    },


    # =========================================================
    # ASSESSMENT -> CO COVERAGE
    # Based on question papers in the guide.
    # =========================================================

    "assessment_co_mapping": {

        "CIE-I": [
            "CO1",
            "CO2"
        ],

        "CIE-II": [
            "CO3",
            "CO4"
        ],

        "Micro Project": [
            "CO1",
            "CO2",
            "CO3",
            "CO4"
        ],

        "SEE": [
            "CO1",
            "CO2",
            "CO3",
            "CO4"
        ]
    },


    # =========================================================
    # STUDENT PERFORMANCE
    #
    # Source: UG-CIE marks report, pages 16-17.
    #
    # Student identities are intentionally anonymized.
    # These are source rows, not invented test data.
    #
    # Columns:
    # CIE-I / CIE-II / Micro Project / Internal Total / Attendance
    # =========================================================

    "student_performance": [

        (14.0, 7.5, 10.0, 32.0, 86),
        (8.5, 3.0, 10.0, 22.0, 86),
        (10.0, 13.0, 10.0, 33.0, 86),
        (18.0, 15.0, 10.0, 43.0, 96),
        (20.0, 19.0, 10.0, 49.0, 91),
        (10.0, 16.5, 10.0, 37.0, 96),
        (15.5, 20.0, 10.0, 46.0, 96),
        (7.5, 8.5, 10.0, 26.0, 91),
        (10.0, 3.5, 10.0, 24.0, 86),
        (14.0, 12.5, 10.0, 37.0, 86),
        (14.5, 11.0, 10.0, 36.0, 86),
        (10.5, 5.0, 10.0, 26.0, 88),
        (4.5, 5.5, 10.0, 20.0, 91),
        (17.5, 10.5, 10.0, 38.0, 91),
        (16.5, 19.0, 10.0, 46.0, 96),
        (15.0, 15.0, 10.0, 40.0, 96),
        (20.0, 20.0, 10.0, 50.0, 96),
        (10.5, 11.5, 10.0, 32.0, 91),
        (9.0, 13.5, 10.0, 33.0, 86),
        (18.0, 15.0, 10.0, 43.0, 96),
        (15.0, 19.0, 10.0, 44.0, 86),
        (13.5, 11.0, 10.0, 35.0, 86),
        (8.5, 11.5, 10.0, 30.0, 86),
        (15.5, 10.5, 10.0, 36.0, 86),
        (13.5, 15.0, 10.0, 39.0, 91),
        (14.5, 10.5, 10.0, 35.0, 87),
        (14.0, 10.5, 10.0, 35.0, 87),
        (13.0, 19.5, 10.0, 43.0, 89),
        (16.5, 14.5, 10.0, 41.0, 91),
        (17.0, 14.0, 10.0, 41.0, 96),

        (14.0, 20.0, 10.0, 44.0, 89),
        (12.5, 11.0, 10.0, 34.0, 87),
        (15.5, 7.0, 10.0, 33.0, 91),
        (18.5, 14.0, 10.0, 43.0, 96),
        (17.0, 16.5, 10.0, 44.0, 96),
        (16.5, 13.5, 10.0, 40.0, 96),
        (17.5, 12.0, 10.0, 40.0, 96),
        (15.0, 19.5, 10.0, 45.0, 96),
        (16.0, 17.0, 10.0, 43.0, 91),
        (18.0, 19.5, 10.0, 48.0, 96),
        (18.5, 20.0, 10.0, 49.0, 96),
        (13.0, 10.5, 10.0, 34.0, 86),
        (19.0, 20.0, 10.0, 49.0, 96),
        (12.0, 10.5, 10.0, 33.0, 89),
        (19.0, 20.0, 10.0, 49.0, 91),
        (12.0, 10.5, 10.0, 33.0, 96),
        (14.0, 17.5, 10.0, 42.0, 96),
        (16.5, 17.5, 10.0, 44.0, 91),
        (8.5, 11.0, 10.0, 30.0, 91),
        (4.5, 8.0, 10.0, 23.0, 86),
        (18.0, 8.5, 10.0, 37.0, 96),
        (10.5, 7.5, 10.0, 28.0, 86),
        (12.0, 9.5, 10.0, 32.0, 86),
        (16.5, 15.0, 10.0, 42.0, 91),
        (12.0, 10.5, 10.0, 33.0, 86),
        (19.0, 20.0, 10.0, 49.0, 96)
    ],


    # =========================================================
    # COURSE-LEVEL GRADE DISTRIBUTION
    # Source: Guide PDF, page 15
    # =========================================================

    "grade_distribution": {

        "registered": 60,
        "appeared": 60,
        "passed": 49,
        "pass_percentage": 81.67,

        "grades": {
            "O": 1,
            "A+": 8,
            "A": 14,
            "B+": 14,
            "B": 6,
            "C": 3,
            "P": 3,
            "F": 11
        }
    },


    # =========================================================
    # DATA QUALITY / SOURCE LIMITATIONS
    # =========================================================

    "data_quality": {

        "cie_mark_records": 56,
        "students_listed": 60,
        "grade_distribution_registered": 60,

        "question_level_student_marks_available": False,

        "official_co_attainment_formula_available": False,

        "official_po_attainment_formula_available": False,

        "notes": [
            "The UG-CIE marks report contains 56 visible student records.",
            "The student list and course-level grade distribution indicate 60 students.",
            "SEE question-to-CO mappings are available, but student question-level SEE marks are not available.",
            "CO-PO-PSO articulation values are available.",
            "An official CO attainment calculation formula is not explicitly provided in the supplied guide data."
        ]
    }
}


# Convert anonymized tuples into dictionaries for the Student Agent.

students = []

for index, record in enumerate(
    criterion3_data["student_performance"],
    start=1
):
    cie1, cie2, micro_project, total, attendance = record

    students.append({
        "student_id": f"S{index:03d}",
        "CIE-I": cie1,
        "CIE-II": cie2,
        "Micro Project": micro_project,
        "Internal Total": total,
        "Attendance": attendance
    })


criterion3_data["students"] = studentscriterion3_data = {

    # =========================================================
    # COURSE INFORMATION
    # Source: Guide PDF, pages 5 and 12
    # =========================================================

    "course": {
        "course_name": "Machine Learning Algorithms",
        "course_code": "22UAI608C",
        "semester": "VI",
        "credits": 3,
        "academic_year": "2025-26",
        "department": "Artificial Intelligence and Machine Learning",
        "faculty": "Dr. Bharati M. Reshmi"
    },


    # =========================================================
    # COURSE OUTCOMES
    # Source: Guide PDF, page 5
    # =========================================================

    "course_outcomes": {

        "CO1": (
            "Apply ensemble learning techniques, regularization methods, "
            "Support Vector Machines, and class imbalance handling to "
            "supervised learning problems."
        ),

        "CO2": (
            "Design and implement Artificial Neural Network models using "
            "perceptron and backpropagation, and evaluate model performance "
            "using appropriate metrics and statistical methods."
        ),

        "CO3": (
            "Apply Bayesian learning and instance-based learning techniques "
            "for classification and regression problems."
        ),

        "CO4": (
            "Use dimensionality reduction and clustering techniques to "
            "analyze and interpret high-dimensional datasets."
        )
    },


    # =========================================================
    # ASSESSMENT SCHEME
    # Source: Guide PDF, page 12
    # =========================================================

    "assessment_scheme": {

        "CIE-I": {
            "marks": 20,
            "weightage_percent": 20
        },

        "CIE-II": {
            "marks": 20,
            "weightage_percent": 20
        },

        "Micro Project": {
            "marks": 10,
            "weightage_percent": 10
        },

        "SEE": {
            "marks": 50,
            "weightage_percent": 50
        },

        "Total": {
            "marks": 100,
            "weightage_percent": 100
        }
    },


    # =========================================================
    # MICRO PROJECT
    # Source: Guide PDF, pages 12 and 58
    # =========================================================

    "micro_project": {

        "total_marks": 10,

        "rubric": {
            "Implementation": 6,
            "Report": 2,
            "Viva": 2
        },

        "associated_cos": [
            "CO1",
            "CO2",
            "CO3",
            "CO4"
        ]
    },


    # =========================================================
    # CO-PO-PSO ARTICULATION MATRIX
    # Source: Guide PDF, page 5
    #
    # None means no articulation is shown in the source.
    # =========================================================

    "co_po_pso_mapping": {

        "CO1": {
            "PO1": 3,
            "PO2": 3,
            "PO3": 3,
            "PO4": 2,
            "PO5": 3,
            "PO6": None,
            "PO7": None,
            "PO8": None,
            "PO9": None,
            "PO10": 2,
            "PO11": 1,
            "PSO1": 3,
            "PSO2": 3,
            "PSO3": 3
        },

        "CO2": {
            "PO1": 3,
            "PO2": 3,
            "PO3": 3,
            "PO4": 3,
            "PO5": 3,
            "PO6": None,
            "PO7": None,
            "PO8": None,
            "PO9": 1,
            "PO10": 2,
            "PO11": 2,
            "PSO1": 3,
            "PSO2": 3,
            "PSO3": 2
        },

        "CO3": {
            "PO1": 3,
            "PO2": 3,
            "PO3": 3,
            "PO4": 2,
            "PO5": 2,
            "PO6": None,
            "PO7": None,
            "PO8": None,
            "PO9": 1,
            "PO10": 2,
            "PO11": 2,
            "PSO1": 3,
            "PSO2": 2,
            "PSO3": 2
        },

        "CO4": {
            "PO1": 3,
            "PO2": 3,
            "PO3": 3,
            "PO4": 3,
            "PO5": 3,
            "PO6": None,
            "PO7": None,
            "PO8": None,
            "PO9": 2,
            "PO10": 2,
            "PO11": 2,
            "PSO1": 3,
            "PSO2": 3,
            "PSO3": 2
        }
    },


    # =========================================================
    # ASSESSMENT -> CO COVERAGE
    # Based on question papers in the guide.
    # =========================================================

    "assessment_co_mapping": {

        "CIE-I": [
            "CO1",
            "CO2"
        ],

        "CIE-II": [
            "CO3",
            "CO4"
        ],

        "Micro Project": [
            "CO1",
            "CO2",
            "CO3",
            "CO4"
        ],

        "SEE": [
            "CO1",
            "CO2",
            "CO3",
            "CO4"
        ]
    },


    # =========================================================
    # STUDENT PERFORMANCE
    #
    # Source: UG-CIE marks report, pages 16-17.
    #
    # Student identities are intentionally anonymized.
    # These are source rows, not invented test data.
    #
    # Columns:
    # CIE-I / CIE-II / Micro Project / Internal Total / Attendance
    # =========================================================

    "student_performance": [

        (14.0, 7.5, 10.0, 32.0, 86),
        (8.5, 3.0, 10.0, 22.0, 86),
        (10.0, 13.0, 10.0, 33.0, 86),
        (18.0, 15.0, 10.0, 43.0, 96),
        (20.0, 19.0, 10.0, 49.0, 91),
        (10.0, 16.5, 10.0, 37.0, 96),
        (15.5, 20.0, 10.0, 46.0, 96),
        (7.5, 8.5, 10.0, 26.0, 91),
        (10.0, 3.5, 10.0, 24.0, 86),
        (14.0, 12.5, 10.0, 37.0, 86),
        (14.5, 11.0, 10.0, 36.0, 86),
        (10.5, 5.0, 10.0, 26.0, 88),
        (4.5, 5.5, 10.0, 20.0, 91),
        (17.5, 10.5, 10.0, 38.0, 91),
        (16.5, 19.0, 10.0, 46.0, 96),
        (15.0, 15.0, 10.0, 40.0, 96),
        (20.0, 20.0, 10.0, 50.0, 96),
        (10.5, 11.5, 10.0, 32.0, 91),
        (9.0, 13.5, 10.0, 33.0, 86),
        (18.0, 15.0, 10.0, 43.0, 96),
        (15.0, 19.0, 10.0, 44.0, 86),
        (13.5, 11.0, 10.0, 35.0, 86),
        (8.5, 11.5, 10.0, 30.0, 86),
        (15.5, 10.5, 10.0, 36.0, 86),
        (13.5, 15.0, 10.0, 39.0, 91),
        (14.5, 10.5, 10.0, 35.0, 87),
        (14.0, 10.5, 10.0, 35.0, 87),
        (13.0, 19.5, 10.0, 43.0, 89),
        (16.5, 14.5, 10.0, 41.0, 91),
        (17.0, 14.0, 10.0, 41.0, 96),

        (14.0, 20.0, 10.0, 44.0, 89),
        (12.5, 11.0, 10.0, 34.0, 87),
        (15.5, 7.0, 10.0, 33.0, 91),
        (18.5, 14.0, 10.0, 43.0, 96),
        (17.0, 16.5, 10.0, 44.0, 96),
        (16.5, 13.5, 10.0, 40.0, 96),
        (17.5, 12.0, 10.0, 40.0, 96),
        (15.0, 19.5, 10.0, 45.0, 96),
        (16.0, 17.0, 10.0, 43.0, 91),
        (18.0, 19.5, 10.0, 48.0, 96),
        (18.5, 20.0, 10.0, 49.0, 96),
        (13.0, 10.5, 10.0, 34.0, 86),
        (19.0, 20.0, 10.0, 49.0, 96),
        (12.0, 10.5, 10.0, 33.0, 89),
        (19.0, 20.0, 10.0, 49.0, 91),
        (12.0, 10.5, 10.0, 33.0, 96),
        (14.0, 17.5, 10.0, 42.0, 96),
        (16.5, 17.5, 10.0, 44.0, 91),
        (8.5, 11.0, 10.0, 30.0, 91),
        (4.5, 8.0, 10.0, 23.0, 86),
        (18.0, 8.5, 10.0, 37.0, 96),
        (10.5, 7.5, 10.0, 28.0, 86),
        (12.0, 9.5, 10.0, 32.0, 86),
        (16.5, 15.0, 10.0, 42.0, 91),
        (12.0, 10.5, 10.0, 33.0, 86),
        (19.0, 20.0, 10.0, 49.0, 96)
    ],


    # =========================================================
    # COURSE-LEVEL GRADE DISTRIBUTION
    # Source: Guide PDF, page 15
    # =========================================================

    "grade_distribution": {

        "registered": 60,
        "appeared": 60,
        "passed": 49,
        "pass_percentage": 81.67,

        "grades": {
            "O": 1,
            "A+": 8,
            "A": 14,
            "B+": 14,
            "B": 6,
            "C": 3,
            "P": 3,
            "F": 11
        }
    },


    # =========================================================
    # DATA QUALITY / SOURCE LIMITATIONS
    # =========================================================

    "data_quality": {

        "cie_mark_records": 56,
        "students_listed": 60,
        "grade_distribution_registered": 60,

        "question_level_student_marks_available": False,

        "official_co_attainment_formula_available": False,

        "official_po_attainment_formula_available": False,

        "notes": [
            "The UG-CIE marks report contains 56 visible student records.",
            "The student list and course-level grade distribution indicate 60 students.",
            "SEE question-to-CO mappings are available, but student question-level SEE marks are not available.",
            "CO-PO-PSO articulation values are available.",
            "An official CO attainment calculation formula is not explicitly provided in the supplied guide data."
        ]
    }
}


# Convert anonymized tuples into dictionaries for the Student Agent.

students = []

for index, record in enumerate(
    criterion3_data["student_performance"],
    start=1
):
    cie1, cie2, micro_project, total, attendance = record

    students.append({
        "student_id": f"S{index:03d}",
        "CIE-I": cie1,
        "CIE-II": cie2,
        "Micro Project": micro_project,
        "Internal Total": total,
        "Attendance": attendance
    })


criterion3_data["students"] = students