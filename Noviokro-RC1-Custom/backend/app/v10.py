"""Additive, project-scoped read-only monitoring overview for local v1.0 GUI."""
from fastapi import APIRouter, Header
from .v08 import authz, Evidence
from .sandbox_bots import Session
from .v06 import Record
from sqlalchemy import func

router=APIRouter(prefix='/api/v1/v10',tags=['v1.0 read-only management'])

@router.get('/monitoring/{project}')
def monitoring(project:str,authorization:str|None=Header(default=None)):
    authz(authorization,project,'read')
    with Session() as db:
        evidence=db.query(func.count(Evidence.id)).filter(Evidence.project==project).scalar()
        # Legacy QA and bot runs are not project scoped. Never expose their details
        # or counts to NOVEAM or Noveomediater project memberships.
        qa_count=db.query(func.count(Record.id)).filter(Record.kind.in_(['qa','v07_qa'])).scalar() if project=='standalone' else None
    return {'project':project,'press_evidence_count':evidence,'legacy_qa_count':qa_count,'legacy_qa_scope':'standalone-only','staging_checks':'disabled','production_connections':'not_connected'}
