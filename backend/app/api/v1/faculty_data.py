"""
AI-NBA Readiness System — Backend
app/api/v1/faculty_data.py

CRUD and Versioning endpoints for faculty achievements:
- Qualifications
- Experience
- Certificates (with versioning & replacement)
- Publications
- Patents
- Trainings (FDPs, Workshops, STTPs)
- Projects (Research Grants)
- Consultancies
- Contributions (Departmental & Professional)

Soft deletion is enforced across all records.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    verify_faculty_owner_or_admin,
)
from app.models.faculty_data import (
    FacultyCertificate,
    FacultyConsultancy,
    FacultyContribution,
    FacultyExperience,
    FacultyPatent,
    FacultyProject,
    FacultyPublication,
    FacultyQualification,
    FacultyTraining,
)
from app.models.user import User
from app.schemas.faculty_data import (
    FacultyCertificateCreate,
    FacultyCertificateReplace,
    FacultyCertificateResponse,
    FacultyConsultancyCreate,
    FacultyConsultancyResponse,
    FacultyContributionCreate,
    FacultyContributionResponse,
    FacultyExperienceCreate,
    FacultyExperienceResponse,
    FacultyPatentCreate,
    FacultyPatentResponse,
    FacultyProjectCreate,
    FacultyProjectResponse,
    FacultyPublicationCreate,
    FacultyPublicationResponse,
    FacultyQualificationCreate,
    FacultyQualificationResponse,
    FacultyTrainingCreate,
    FacultyTrainingResponse,
)

router = APIRouter(prefix="/faculty", tags=["Faculty Data Layer"])


# =============================================================================
# Qualifications
# =============================================================================

@router.get(
    "/{faculty_id}/qualifications",
    response_model=List[FacultyQualificationResponse],
    summary="List faculty qualifications",
)
def list_qualifications(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyQualificationResponse]:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    records = (
        db.query(FacultyQualification)
        .filter(
            FacultyQualification.faculty_profile_id == faculty.id,
            FacultyQualification.is_deleted.is_(False),
        )
        .order_by(FacultyQualification.year_of_passing.desc())
        .all()
    )
    return [FacultyQualificationResponse.model_validate(r) for r in records]


@router.post(
    "/{faculty_id}/qualifications",
    response_model=FacultyQualificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add faculty qualification",
)
def add_qualification(
    faculty_id: str,
    payload: FacultyQualificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyQualificationResponse:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    record = FacultyQualification(
        faculty_profile_id=faculty.id,
        degree=payload.degree.strip(),
        field_of_study=payload.field_of_study.strip(),
        institution=payload.institution.strip(),
        university=payload.university.strip(),
        year_of_passing=payload.year_of_passing,
        grade_or_percentage=payload.grade_or_percentage.strip() if payload.grade_or_percentage else None,
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
        updated_by=str(current_user.id),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FacultyQualificationResponse.model_validate(record)


@router.delete(
    "/qualifications/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete faculty qualification",
)
def delete_qualification(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = db.query(FacultyQualification).filter(FacultyQualification.id == id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    verify_faculty_owner_or_admin(str(record.faculty_profile_id), current_user, db)

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = str(current_user.id)
    db.commit()


# =============================================================================
# Experience
# =============================================================================

@router.get(
    "/{faculty_id}/experiences",
    response_model=List[FacultyExperienceResponse],
    summary="List faculty experience records",
)
def list_experiences(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyExperienceResponse]:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    records = (
        db.query(FacultyExperience)
        .filter(
            FacultyExperience.faculty_profile_id == faculty.id,
            FacultyExperience.is_deleted.is_(False),
        )
        .order_by(FacultyExperience.start_date.desc())
        .all()
    )
    return [FacultyExperienceResponse.model_validate(r) for r in records]


@router.post(
    "/{faculty_id}/experiences",
    response_model=FacultyExperienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add faculty experience record",
)
def add_experience(
    faculty_id: str,
    payload: FacultyExperienceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyExperienceResponse:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    record = FacultyExperience(
        faculty_profile_id=faculty.id,
        designation=payload.designation.strip(),
        organization=payload.organization.strip(),
        experience_type=payload.experience_type.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_current=payload.is_current,
        roles_and_responsibilities=payload.roles_and_responsibilities,
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
        updated_by=str(current_user.id),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FacultyExperienceResponse.model_validate(record)


@router.delete(
    "/experiences/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete faculty experience record",
)
def delete_experience(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = db.query(FacultyExperience).filter(FacultyExperience.id == id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    verify_faculty_owner_or_admin(str(record.faculty_profile_id), current_user, db)

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = str(current_user.id)
    db.commit()


# =============================================================================
# Certificates (with Versioning)
# =============================================================================

@router.get(
    "/{faculty_id}/certificates",
    response_model=List[FacultyCertificateResponse],
    summary="List active current certificates",
)
def list_certificates(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyCertificateResponse]:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    # Ordinary query returns current, non-deleted certificates
    records = (
        db.query(FacultyCertificate)
        .filter(
            FacultyCertificate.faculty_profile_id == faculty.id,
            FacultyCertificate.is_current.is_(True),
            FacultyCertificate.is_deleted.is_(False),
        )
        .order_by(FacultyCertificate.issue_date.desc())
        .all()
    )
    return [FacultyCertificateResponse.model_validate(r) for r in records]


@router.post(
    "/{faculty_id}/certificates",
    response_model=FacultyCertificateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add initial certificate (v1)",
)
def add_certificate(
    faculty_id: str,
    payload: FacultyCertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyCertificateResponse:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    record = FacultyCertificate(
        faculty_profile_id=faculty.id,
        title=payload.title.strip(),
        issuing_organization=payload.issuing_organization.strip(),
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
        credential_id=payload.credential_id.strip() if payload.credential_id else None,
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
        version=1,
        is_current=True,
        updated_by=str(current_user.id),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FacultyCertificateResponse.model_validate(record)


@router.post(
    "/certificates/{id}/replace",
    response_model=FacultyCertificateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Replace certificate with new version (retains history)",
)
def replace_certificate(
    id: uuid.UUID,
    payload: FacultyCertificateReplace,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyCertificateResponse:
    old_cert = db.query(FacultyCertificate).filter(FacultyCertificate.id == id).first()
    if not old_cert or old_cert.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found.")
    verify_faculty_owner_or_admin(str(old_cert.faculty_profile_id), current_user, db)

    # Determine root lineage id
    root_id = old_cert.parent_certificate_id or old_cert.id

    # Mark old certificate as no longer current
    old_cert.is_current = False

    new_cert = FacultyCertificate(
        faculty_profile_id=old_cert.faculty_profile_id,
        title=payload.title.strip() if payload.title else old_cert.title,
        issuing_organization=payload.issuing_organization.strip() if payload.issuing_organization else old_cert.issuing_organization,
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
        credential_id=payload.credential_id.strip() if payload.credential_id else old_cert.credential_id,
        document_reference=payload.document_reference.strip() if payload.document_reference else old_cert.document_reference,
        version=old_cert.version + 1,
        is_current=True,
        parent_certificate_id=root_id,
        updated_by=str(current_user.id),
    )
    db.add(new_cert)
    db.commit()
    db.refresh(new_cert)
    return FacultyCertificateResponse.model_validate(new_cert)


@router.get(
    "/certificates/{id}/history",
    response_model=List[FacultyCertificateResponse],
    summary="Retrieve certificate version history",
)
def get_certificate_history(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyCertificateResponse]:
    cert = db.query(FacultyCertificate).filter(FacultyCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found.")
    verify_faculty_owner_or_admin(str(cert.faculty_profile_id), current_user, db)

    root_id = cert.parent_certificate_id or cert.id
    history = (
        db.query(FacultyCertificate)
        .filter(
            (FacultyCertificate.id == root_id) | (FacultyCertificate.parent_certificate_id == root_id),
            FacultyCertificate.is_deleted.is_(False),
        )
        .order_by(FacultyCertificate.version.asc())
        .all()
    )
    return [FacultyCertificateResponse.model_validate(c) for c in history]


@router.delete(
    "/certificates/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete certificate",
)
def delete_certificate(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = db.query(FacultyCertificate).filter(FacultyCertificate.id == id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    verify_faculty_owner_or_admin(str(record.faculty_profile_id), current_user, db)

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = str(current_user.id)
    db.commit()


# =============================================================================
# Publications
# =============================================================================

@router.get(
    "/{faculty_id}/publications",
    response_model=List[FacultyPublicationResponse],
    summary="List faculty publications",
)
def list_publications(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyPublicationResponse]:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    records = (
        db.query(FacultyPublication)
        .filter(
            FacultyPublication.faculty_profile_id == faculty.id,
            FacultyPublication.is_deleted.is_(False),
        )
        .order_by(FacultyPublication.created_at.desc())
        .all()
    )
    return [FacultyPublicationResponse.model_validate(r) for r in records]


@router.post(
    "/{faculty_id}/publications",
    response_model=FacultyPublicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add faculty publication",
)
def add_publication(
    faculty_id: str,
    payload: FacultyPublicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyPublicationResponse:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    record = FacultyPublication(
        faculty_profile_id=faculty.id,
        title=payload.title.strip(),
        publication_type=payload.publication_type.strip(),
        journal_or_conference_name=payload.journal_or_conference_name.strip(),
        academic_year_id=payload.academic_year_id,
        issn_or_isbn=payload.issn_or_isbn.strip() if payload.issn_or_isbn else None,
        publication_date=payload.publication_date,
        volume_issue_pages=payload.volume_issue_pages.strip() if payload.volume_issue_pages else None,
        doi_or_url=payload.doi_or_url.strip() if payload.doi_or_url else None,
        indexing=payload.indexing.strip() if payload.indexing else None,
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
        updated_by=str(current_user.id),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FacultyPublicationResponse.model_validate(record)


@router.delete(
    "/publications/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete faculty publication",
)
def delete_publication(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = db.query(FacultyPublication).filter(FacultyPublication.id == id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    verify_faculty_owner_or_admin(str(record.faculty_profile_id), current_user, db)

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = str(current_user.id)
    db.commit()


# =============================================================================
# Patents
# =============================================================================

@router.get(
    "/{faculty_id}/patents",
    response_model=List[FacultyPatentResponse],
    summary="List faculty patents",
)
def list_patents(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyPatentResponse]:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    records = (
        db.query(FacultyPatent)
        .filter(
            FacultyPatent.faculty_profile_id == faculty.id,
            FacultyPatent.is_deleted.is_(False),
        )
        .order_by(FacultyPatent.filing_date.desc())
        .all()
    )
    return [FacultyPatentResponse.model_validate(r) for r in records]


@router.post(
    "/{faculty_id}/patents",
    response_model=FacultyPatentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add faculty patent",
)
def add_patent(
    faculty_id: str,
    payload: FacultyPatentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyPatentResponse:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    record = FacultyPatent(
        faculty_profile_id=faculty.id,
        title=payload.title.strip(),
        application_number=payload.application_number.strip(),
        patent_number=payload.patent_number.strip() if payload.patent_number else None,
        filing_date=payload.filing_date,
        grant_date=payload.grant_date,
        status=payload.status.strip(),
        inventors=payload.inventors.strip() if payload.inventors else None,
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
        updated_by=str(current_user.id),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FacultyPatentResponse.model_validate(record)


@router.delete(
    "/patents/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete faculty patent",
)
def delete_patent(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = db.query(FacultyPatent).filter(FacultyPatent.id == id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    verify_faculty_owner_or_admin(str(record.faculty_profile_id), current_user, db)

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = str(current_user.id)
    db.commit()


# =============================================================================
# Trainings (FDPs, Workshops, STTPs)
# =============================================================================

@router.get(
    "/{faculty_id}/trainings",
    response_model=List[FacultyTrainingResponse],
    summary="List faculty training records",
)
def list_trainings(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyTrainingResponse]:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    records = (
        db.query(FacultyTraining)
        .filter(
            FacultyTraining.faculty_profile_id == faculty.id,
            FacultyTraining.is_deleted.is_(False),
        )
        .order_by(FacultyTraining.start_date.desc())
        .all()
    )
    return [FacultyTrainingResponse.model_validate(r) for r in records]


@router.post(
    "/{faculty_id}/trainings",
    response_model=FacultyTrainingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add faculty training record",
)
def add_training(
    faculty_id: str,
    payload: FacultyTrainingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyTrainingResponse:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    record = FacultyTraining(
        faculty_profile_id=faculty.id,
        title=payload.title.strip(),
        program_type=payload.program_type.strip(),
        organization=payload.organization.strip(),
        location=payload.location.strip() if payload.location else None,
        start_date=payload.start_date,
        end_date=payload.end_date,
        duration_days=payload.duration_days,
        role=payload.role.strip(),
        academic_year_id=payload.academic_year_id,
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
        updated_by=str(current_user.id),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FacultyTrainingResponse.model_validate(record)


@router.delete(
    "/trainings/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete faculty training record",
)
def delete_training(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = db.query(FacultyTraining).filter(FacultyTraining.id == id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    verify_faculty_owner_or_admin(str(record.faculty_profile_id), current_user, db)

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = str(current_user.id)
    db.commit()


# =============================================================================
# Research Projects
# =============================================================================

@router.get(
    "/{faculty_id}/projects",
    response_model=List[FacultyProjectResponse],
    summary="List faculty research projects",
)
def list_projects(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyProjectResponse]:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    records = (
        db.query(FacultyProject)
        .filter(
            FacultyProject.faculty_profile_id == faculty.id,
            FacultyProject.is_deleted.is_(False),
        )
        .order_by(FacultyProject.start_date.desc())
        .all()
    )
    return [FacultyProjectResponse.model_validate(r) for r in records]


@router.post(
    "/{faculty_id}/projects",
    response_model=FacultyProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add faculty research project",
)
def add_project(
    faculty_id: str,
    payload: FacultyProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyProjectResponse:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    record = FacultyProject(
        faculty_profile_id=faculty.id,
        title=payload.title.strip(),
        funding_agency=payload.funding_agency.strip(),
        grant_amount=payload.grant_amount,
        sanction_date=payload.sanction_date,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status.strip(),
        role=payload.role.strip(),
        academic_year_id=payload.academic_year_id,
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
        updated_by=str(current_user.id),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FacultyProjectResponse.model_validate(record)


@router.delete(
    "/projects/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete faculty project",
)
def delete_project(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = db.query(FacultyProject).filter(FacultyProject.id == id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    verify_faculty_owner_or_admin(str(record.faculty_profile_id), current_user, db)

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = str(current_user.id)
    db.commit()


# =============================================================================
# Consultancies
# =============================================================================

@router.get(
    "/{faculty_id}/consultancies",
    response_model=List[FacultyConsultancyResponse],
    summary="List faculty consultancies",
)
def list_consultancies(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyConsultancyResponse]:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    records = (
        db.query(FacultyConsultancy)
        .filter(
            FacultyConsultancy.faculty_profile_id == faculty.id,
            FacultyConsultancy.is_deleted.is_(False),
        )
        .order_by(FacultyConsultancy.start_date.desc())
        .all()
    )
    return [FacultyConsultancyResponse.model_validate(r) for r in records]


@router.post(
    "/{faculty_id}/consultancies",
    response_model=FacultyConsultancyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add faculty consultancy project",
)
def add_consultancy(
    faculty_id: str,
    payload: FacultyConsultancyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyConsultancyResponse:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    record = FacultyConsultancy(
        faculty_profile_id=faculty.id,
        project_title=payload.project_title.strip(),
        client_organization=payload.client_organization.strip(),
        financial_outlay=payload.financial_outlay,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status.strip(),
        academic_year_id=payload.academic_year_id,
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
        updated_by=str(current_user.id),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FacultyConsultancyResponse.model_validate(record)


@router.delete(
    "/consultancies/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete faculty consultancy",
)
def delete_consultancy(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = db.query(FacultyConsultancy).filter(FacultyConsultancy.id == id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    verify_faculty_owner_or_admin(str(record.faculty_profile_id), current_user, db)

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = str(current_user.id)
    db.commit()


# =============================================================================
# Contributions
# =============================================================================

@router.get(
    "/{faculty_id}/contributions",
    response_model=List[FacultyContributionResponse],
    summary="List faculty professional/departmental contributions",
)
def list_contributions(
    faculty_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyContributionResponse]:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    records = (
        db.query(FacultyContribution)
        .filter(
            FacultyContribution.faculty_profile_id == faculty.id,
            FacultyContribution.is_deleted.is_(False),
        )
        .order_by(FacultyContribution.created_at.desc())
        .all()
    )
    return [FacultyContributionResponse.model_validate(r) for r in records]


@router.post(
    "/{faculty_id}/contributions",
    response_model=FacultyContributionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add faculty contribution",
)
def add_contribution(
    faculty_id: str,
    payload: FacultyContributionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FacultyContributionResponse:
    faculty = verify_faculty_owner_or_admin(faculty_id, current_user, db)
    record = FacultyContribution(
        faculty_profile_id=faculty.id,
        title=payload.title.strip(),
        category=payload.category.strip(),
        description=payload.description.strip() if payload.description else None,
        start_date=payload.start_date,
        end_date=payload.end_date,
        academic_year_id=payload.academic_year_id,
        document_reference=payload.document_reference.strip() if payload.document_reference else None,
        updated_by=str(current_user.id),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FacultyContributionResponse.model_validate(record)


@router.delete(
    "/contributions/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete faculty contribution",
)
def delete_contribution(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    record = db.query(FacultyContribution).filter(FacultyContribution.id == id).first()
    if not record or record.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    verify_faculty_owner_or_admin(str(record.faculty_profile_id), current_user, db)

    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    record.updated_by = str(current_user.id)
    db.commit()
