import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.test import DiagnosticTest
from app.schemas.test import TestOut

router = APIRouter(prefix="/tests", tags=["tests"])


@router.get("/", response_model=list[TestOut])
def list_all_tests(
    name: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Public: browse every test across every centre, optionally by name."""
    query = db.query(DiagnosticTest)
    if name:
        query = query.filter(DiagnosticTest.name.ilike(f"%{name}%"))
    return query.offset(skip).limit(min(limit, 100)).all()


@router.get("/{test_id}", response_model=TestOut)
def get_test(test_id: uuid.UUID, db: Session = Depends(get_db)):
    test = db.get(DiagnosticTest, test_id)
    if test is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diagnostic test not found.")
    return test
