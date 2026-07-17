"""
Access Requests API — public endpoint for landing page form submissions,
plus admin endpoints for reviewing and managing requests.
"""

import re
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db, AccessRequest, User
from auth import get_current_user

logger = logging.getLogger("access_requests")
router = APIRouter(tags=["access-requests"])

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class AccessRequestCreate(BaseModel):
    name: str
    email: str
    trading_experience: Optional[str] = ""
    message: Optional[str] = ""


@router.post("/access-requests")
async def submit_access_request(
    body: AccessRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Public endpoint — anyone can submit a request from the landing page."""
    name = (body.name or "").strip()
    email = (body.email or "").strip().lower()

    # Basic validation
    if not name or len(name) < 2 or len(name) > 100:
        raise HTTPException(status_code=400, detail="Please provide a valid name.")
    if not email or not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")

    # Length limits to prevent abuse
    trading_experience = (body.trading_experience or "")[:255]
    message = (body.message or "")[:2000]

    ip = request.client.host if request.client else "unknown"

    new_req = AccessRequest(
        name=name,
        email=email,
        trading_experience=trading_experience,
        message=message,
        status="pending",
        ip_address=ip,
        created_at=datetime.utcnow(),
    )
    db.add(new_req)
    db.commit()
    db.refresh(new_req)

    logger.info(f"New access request from {email} (id={new_req.id})")

    return {
        "status": "success",
        "message": "We'll review your request and get back to you within 24-48 hours.",
        "id": new_req.id,
    }


# ── Admin endpoints (require admin auth) ──────────────

def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/admin/access-requests")
async def list_access_requests(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=200),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all access requests with optional status filter."""
    query = db.query(AccessRequest).order_by(AccessRequest.created_at.desc())
    if status:
        query = query.filter(AccessRequest.status == status)

    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "requests": [
            {
                "id": r.id,
                "name": r.name,
                "email": r.email,
                "trading_experience": r.trading_experience,
                "message": r.message,
                "status": r.status,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            }
            for r in items
        ],
        "total": total,
        "page": page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.post("/admin/access-requests/{request_id}/reject")
async def reject_access_request(
    request_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Mark an access request as rejected."""
    from audit import log_event

    req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req.status = "rejected"
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = admin.id
    db.commit()

    ip = request.client.host if request.client else "unknown"
    log_event(db, admin.id, "ACCESS_REQUEST_REJECTED", f"Rejected access request from {req.email}", ip)

    return {"status": "success"}


class ApproveRequest(BaseModel):
    password: str


@router.post("/admin/access-requests/{request_id}/approve")
async def approve_access_request(
    request_id: int,
    body: ApproveRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Approve an access request — creates a new user with the provided password
    and marks the request as approved.
    """
    from audit import log_event
    from auth import pwd_context, validate_password_strength

    req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Check if a user with this email already exists
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"A user with email {req.email} already exists")

    # Enforce the SAME complexity bar as the self-serve reset path (auth.validate_password_strength):
    # 12+ chars, 3-of-4 character classes, breach/blocklist check. Previously this admin-facing intake
    # path only required len >= 6, making the route that creates real subscribers weaker than reset.
    if not body.password:
        raise HTTPException(status_code=400, detail="Password is required.")
    validate_password_strength(body.password, email=req.email)

    # Create the user
    new_user = User(
        email=req.email,
        password_hash=pwd_context.hash(body.password),
        name=req.name,
        is_admin=False,
        is_active=True,
    )
    db.add(new_user)

    # Update the request
    req.status = "approved"
    req.reviewed_at = datetime.utcnow()
    req.reviewed_by = admin.id

    db.commit()
    db.refresh(new_user)

    ip = request.client.host if request.client else "unknown"
    log_event(db, admin.id, "ACCESS_REQUEST_APPROVED", f"Approved {req.email} (user_id={new_user.id})", ip)

    return {
        "status": "success",
        "user_id": new_user.id,
        "email": new_user.email,
        "message": f"User {new_user.email} created. Share these credentials securely.",
    }


@router.delete("/admin/access-requests/{request_id}")
async def delete_access_request(
    request_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Permanently delete an access request."""
    from audit import log_event

    req = db.query(AccessRequest).filter(AccessRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    email = req.email
    db.delete(req)
    db.commit()

    ip = request.client.host if request.client else "unknown"
    log_event(db, admin.id, "ACCESS_REQUEST_DELETED", f"Deleted access request from {email}", ip)

    return {"status": "success"}
