import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user
from app.database import get_db
from app.models.centre import DiagnosticCentre
from app.models.test import DiagnosticTest
from app.schemas.centre import CentreCreate, CentreOut
from app.schemas.test import TestCreate, TestOut

router = APIRouter(prefix="/centres", tags=["centres"])


@router.post("/", response_model=CentreOut, status_code=status.HTTP_201_CREATED)
def create_centre(
    payload: CentreCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    """Admin-only: onboard a new diagnostic centre."""
    centre = DiagnosticCentre(name=payload.name, location=payload.location)
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@router.get("/", response_model=list[CentreOut])
def list_centres(
    location: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Public: browse diagnostic centres, optionally filtered by location."""
    query = db.query(DiagnosticCentre)
    if location:
        query = query.filter(DiagnosticCentre.location.ilike(f"%{location}%"))
    return query.offset(skip).limit(min(limit, 100)).all()


@router.get("/{centre_id}", response_model=CentreOut)
def get_centre(centre_id: uuid.UUID, db: Session = Depends(get_db)):
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diagnostic centre not found.")
    return centre


@router.post(
    "/{centre_id}/tests", response_model=TestOut, status_code=status.HTTP_201_CREATED
)
def add_test_to_centre(
    centre_id: uuid.UUID,
    payload: TestCreate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    """Admin-only: add a test (with its price) to a centre's offerings."""
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diagnostic centre not found.")

    test = DiagnosticTest(centre_id=centre.id, name=payload.name, price=payload.price)
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.get("/{centre_id}/tests", response_model=list[TestOut])
def list_tests_for_centre(centre_id: uuid.UUID, db: Session = Depends(get_db)):
    """Public: see the tests (and prices) a given centre offers."""
    centre = db.get(DiagnosticCentre, centre_id)
    if centre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diagnostic centre not found.")
    return centre.tests
