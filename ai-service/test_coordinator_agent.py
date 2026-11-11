from app.agents.assessment_agent import analyze_assessment
from app.agents.student_agent import analyze_student_performance
from app.agents.coordinator_agent import coordinate_criterion3


print("=" * 70)
print("STEP 1: RUNNING ASSESSMENT AGENT")
print("=" * 70)

assessment_result = analyze_assessment()

print("\nAssessment Agent completed.")


print("\n" + "=" * 70)
print("STEP 2: RUNNING STUDENT AGENT")
print("=" * 70)

student_result = analyze_student_performance()

print("\nStudent Agent completed.")


print("\n" + "=" * 70)
print("STEP 3: RUNNING COORDINATOR AGENT")
print("=" * 70)

final_result = coordinate_criterion3(
    assessment_analysis=assessment_result,
    student_analysis=student_result
)

print("\nCoordinator Agent completed.")


print("\n" + "=" * 70)
print("FINAL CRITERION 3 ANALYSIS")
print("=" * 70)

print(final_result)