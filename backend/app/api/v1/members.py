"""Organization members and invitations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequireAdmin, RequireViewer
from app.core.security import get_password_hash
from app.models.invite import Invite
from app.models.user import User, Organization
from app.schemas.auth import UserOut
from app.services.audit import write_audit
from app.services.billing import LimitExceeded, assert_can_add_member
from app.services.email import send_invite_email

router = APIRouter()


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = Field("member", pattern="^(admin|editor|viewer|member)$")


class InviteOut(BaseModel):
    id: UUID
    email: str
    role: str
    status: str
    token: str
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class AcceptInviteBody(BaseModel):
    token: str
    password: str = Field(..., min_length=8)
    full_name: str | None = None


@router.get("", response_model=list[UserOut])
async def list_members(db: Annotated[AsyncSession, Depends(get_db)], ctx: RequireViewer):
    result = await db.execute(
        select(User).where(User.organization_id == ctx.org_id).order_by(User.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: InviteCreate,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireAdmin,
):
    email = body.email.lower()
    existing_user = await db.execute(
        select(User).where(User.organization_id == ctx.org_id, User.email == email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already in organization")

    existing_inv = await db.execute(
        select(Invite).where(
            Invite.organization_id == ctx.org_id,
            Invite.email == email,
            Invite.status == "pending",
        )
    )
    inv = existing_inv.scalar_one_or_none()
    if inv:
        return inv

    try:
        await assert_can_add_member(db, ctx.org_id)
    except LimitExceeded as e:
        raise HTTPException(status_code=402, detail=e.message)

    inv = Invite(
        organization_id=ctx.org_id,
        email=email,
        role=body.role,
        invited_by_id=ctx.user_id,
    )
    db.add(inv)
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="invite.create",
        resource_type="invite",
        ip_address=request.client.host if request.client else None,
        meta={"email": email, "role": body.role},
    )
    await db.commit()
    await db.refresh(inv)

    org = await db.get(Organization, ctx.org_id)
    await send_invite_email(
        to=email,
        org_name=org.name if org else "AURI.AI",
        role=body.role,
        token=inv.token,
        inviter_name=ctx.user.full_name or ctx.user.email,
    )
    return inv


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(db: Annotated[AsyncSession, Depends(get_db)], ctx: RequireAdmin):
    result = await db.execute(
        select(Invite)
        .where(Invite.organization_id == ctx.org_id)
        .order_by(Invite.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/invites/accept", status_code=status.HTTP_201_CREATED)
async def accept_invite(
    body: AcceptInviteBody,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Invite).where(Invite.token == body.token))
    inv = result.scalar_one_or_none()
    if not inv or inv.status != "pending":
        raise HTTPException(status_code=400, detail="Invalid invite")
    if inv.expires_at < datetime.now(timezone.utc):
        inv.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Invite expired")

    existing = await db.execute(select(User).where(User.email == inv.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=inv.email,
        hashed_password=get_password_hash(body.password),
        full_name=body.full_name,
        role=inv.role,
        organization_id=inv.organization_id,
    )
    db.add(user)
    inv.status = "accepted"
    inv.accepted_at = datetime.now(timezone.utc)
    await write_audit(
        db,
        organization_id=inv.organization_id,
        actor_id=None,
        action="invite.accept",
        resource_type="invite",
        resource_id=inv.id,
        meta={"email": inv.email},
    )
    await db.commit()
    await db.refresh(user)
    return {"ok": True, "user_id": str(user.id), "organization_id": str(inv.organization_id)}


@router.delete("/invites/{invite_id}")
async def revoke_invite(
    invite_id: UUID,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireAdmin,
):
    result = await db.execute(
        select(Invite).where(Invite.id == invite_id, Invite.organization_id == ctx.org_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invite not found")
    inv.status = "revoked"
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="invite.revoke",
        resource_type="invite",
        resource_id=invite_id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True}


@router.patch("/{user_id}/role")
async def update_member_role(
    user_id: UUID,
    role: str,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    ctx: RequireAdmin,
):
    if role not in ("admin", "editor", "viewer", "member"):
        raise HTTPException(status_code=400, detail="Invalid role")
    result = await db.execute(
        select(User).where(User.id == user_id, User.organization_id == ctx.org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == ctx.user_id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    user.role = role
    await write_audit(
        db,
        organization_id=ctx.org_id,
        actor_id=ctx.user_id,
        action="member.role_update",
        resource_type="user",
        resource_id=user_id,
        ip_address=request.client.host if request.client else None,
        meta={"role": role},
    )
    await db.commit()
    return {"ok": True, "user_id": str(user_id), "role": role}
