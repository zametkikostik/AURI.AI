"""Plan limits enforcement for Free vs Enterprise."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting, Recording
from app.models.user import Organization


@dataclass
class PlanLimits:
    name: str
    max_meetings: int | None
    max_hours_per_month: float | None
    team_features: bool
    sso: bool
    max_members: int | None


PLANS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        name="free",
        max_meetings=5,
        max_hours_per_month=5.0,
        team_features=False,
        sso=False,
        max_members=3,
    ),
    "enterprise": PlanLimits(
        name="enterprise",
        max_meetings=None,
        max_hours_per_month=None,
        team_features=True,
        sso=True,
        max_members=None,
    ),
}


def get_plan(plan_name: str) -> PlanLimits:
    return PLANS.get(plan_name, PLANS["free"])


class LimitExceeded(Exception):
    def __init__(self, message: str, code: str = "limit_exceeded"):
        self.message = message
        self.code = code
        super().__init__(message)


async def assert_can_create_meeting(db: AsyncSession, organization_id: UUID) -> None:
    org = await db.get(Organization, organization_id)
    if not org:
        raise LimitExceeded("Organization not found", "org_not_found")
    plan = get_plan(org.plan)

    if plan.max_meetings is not None:
        count = (
            await db.execute(
                select(func.count())
                .select_from(Meeting)
                .where(Meeting.organization_id == organization_id)
            )
        ).scalar() or 0
        if count >= plan.max_meetings:
            raise LimitExceeded(
                f"Free plan limit: max {plan.max_meetings} meetings. Upgrade to Enterprise.",
                "max_meetings",
            )


async def assert_can_upload_hours(
    db: AsyncSession, organization_id: UUID, additional_seconds: float = 0
) -> None:
    org = await db.get(Organization, organization_id)
    if not org:
        raise LimitExceeded("Organization not found", "org_not_found")
    plan = get_plan(org.plan)
    if plan.max_hours_per_month is None:
        return

    total_sec = (
        await db.execute(
            select(func.coalesce(func.sum(Recording.duration_seconds), 0))
            .select_from(Recording)
            .join(Meeting, Meeting.id == Recording.meeting_id)
            .where(Meeting.organization_id == organization_id)
        )
    ).scalar() or 0
    hours = (float(total_sec) + additional_seconds) / 3600.0
    if hours > plan.max_hours_per_month:
        raise LimitExceeded(
            f"Free plan limit: {plan.max_hours_per_month}h transcription. Upgrade to Enterprise.",
            "max_hours",
        )


async def assert_can_add_member(db: AsyncSession, organization_id: UUID) -> None:
    org = await db.get(Organization, organization_id)
    if not org:
        raise LimitExceeded("Organization not found", "org_not_found")
    plan = get_plan(org.plan)
    if plan.max_members is None:
        return
    from app.models.user import User

    count = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.organization_id == organization_id, User.is_active.is_(True))
        )
    ).scalar() or 0
    if count >= plan.max_members:
        raise LimitExceeded(
            f"Free plan limit: max {plan.max_members} members.",
            "max_members",
        )


async def usage_snapshot(db: AsyncSession, organization_id: UUID) -> dict:
    org = await db.get(Organization, organization_id)
    plan = get_plan(org.plan if org else "free")
    meetings = (
        await db.execute(
            select(func.count())
            .select_from(Meeting)
            .where(Meeting.organization_id == organization_id)
        )
    ).scalar() or 0
    total_sec = (
        await db.execute(
            select(func.coalesce(func.sum(Recording.duration_seconds), 0))
            .select_from(Recording)
            .join(Meeting, Meeting.id == Recording.meeting_id)
            .where(Meeting.organization_id == organization_id)
        )
    ).scalar() or 0
    from app.models.user import User

    members = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.organization_id == organization_id, User.is_active.is_(True))
        )
    ).scalar() or 0
    return {
        "plan": plan.name,
        "meetings": {"used": meetings, "limit": plan.max_meetings},
        "hours": {
            "used": round(float(total_sec) / 3600.0, 2),
            "limit": plan.max_hours_per_month,
        },
        "members": {"used": members, "limit": plan.max_members},
        "features": {"team": plan.team_features, "sso": plan.sso},
    }
