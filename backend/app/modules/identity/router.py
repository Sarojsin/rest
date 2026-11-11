from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from uuid import UUID
from sqlalchemy.orm import Session

from app.api.deps import Actor, get_actor
from app.db.session import get_db
from app.modules.identity.schemas import LoginRequest, LoginResponse, MeOut, MFAChallengeResponse
from app.modules.identity.services import auth as auth_service
from app.modules.identity.services import mfa as mfa_service
from app.modules.tenancy.models import RestaurantMembership
from app.modules.platform.models import PlatformOneTimeToken
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_and_consume_refresh_token,
    decode_mfa_challenge_token,
    hash_password,
    hash_token,
)

router = APIRouter(tags=["auth"])


class SwitchMembershipRequest(BaseModel):
    membership_id: UUID
    branch_id: UUID | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class MFAEnrollResponse(BaseModel):
    provisioning_uri: str
    recovery_codes: list[str]
    enrollment_ticket: str


class MFAVerifyRequest(BaseModel):
    code: str
    enrollment_ticket: str


class MFADisableRequest(BaseModel):
    password: str


class MFAChallengeRequest(BaseModel):
    mfa_token: str
    mfa_code: str | None = None
    recovery_code: str | None = None


@router.post("/auth/login", response_model=LoginResponse | MFAChallengeResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse | MFAChallengeResponse:
    return await auth_service.login(db, payload.email, payload.password)


@router.post("/auth/mfa/challenge", response_model=LoginResponse)
async def mfa_challenge(payload: MFAChallengeRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Complete MFA challenge after initial login. Returns full token pair on success."""
    # Decode and validate MFA challenge token
    try:
        mfa_payload = decode_mfa_challenge_token(payload.mfa_token)
    except Exception:
        raise HTTPException(401, "Invalid or expired MFA challenge token")

    user_id = UUID(mfa_payload["sub"])
    membership_id = UUID(mfa_payload["mid"])
    restaurant_id = UUID(mfa_payload["rid"])
    token_version = mfa_payload["ver"]

    # Verify membership still exists and is active
    membership = db.get(RestaurantMembership, membership_id)
    if not membership or membership.user_id != user_id:
        raise HTTPException(401, "Membership not found")
    if membership.status != "ACTIVE":
        raise HTTPException(401, "Membership is not active")
    if membership.token_version != token_version:
        raise HTTPException(401, "Token revoked")

    # Verify MFA
    from app.modules.platform.services.crypto import decrypt_field
    user = membership.user

    if not user.mfa_enabled:
        raise HTTPException(400, "MFA not enabled")

    verified = False
    if payload.mfa_code and user.totp_secret:
        secret = decrypt_field(user.totp_secret)
        from app.modules.identity.services.mfa import verify_totp
        if verify_totp(secret, payload.mfa_code):
            verified = True

    if not verified and payload.recovery_code and user.recovery_codes_hash:
        from app.modules.identity.services.mfa import verify_and_consume_recovery_code
        matched, remaining_hash = verify_and_consume_recovery_code(
            user.recovery_codes_hash, payload.recovery_code
        )
        if matched:
            user.recovery_codes_hash = remaining_hash
            verified = True

    if not verified:
        raise HTTPException(401, "Invalid MFA code or recovery code")

    # MFA verified - create full token pair
    access_token = create_access_token(
        user_id=user_id,
        membership_id=membership_id,
        restaurant_id=restaurant_id,
        token_version=token_version,
    )
    refresh_token = await create_refresh_token(
        user_id=user_id,
        membership_id=membership_id,
        restaurant_id=restaurant_id,
        token_version=token_version,
    )

    active_memberships = [m for m in user.memberships if m.status == "ACTIVE"]
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=auth_service.me_from_membership(user, membership, active_memberships),
    )


@router.post("/auth/mfa/enroll", response_model=MFAEnrollResponse)
async def enroll_mfa(actor: Actor = Depends(get_actor), db: Session = Depends(get_db)) -> MFAEnrollResponse:
    """Start MFA enrollment. Returns QR code URI and recovery codes."""
    if actor.user.mfa_enabled:
        raise HTTPException(400, "MFA already enabled")

    uri, recovery_codes, enrollment_ticket = await mfa_service.enroll_mfa(actor.user, db)
    return MFAEnrollResponse(
        provisioning_uri=uri,
        recovery_codes=recovery_codes,
        enrollment_ticket=enrollment_ticket,
    )


@router.post("/auth/mfa/verify")
async def verify_mfa_enrollment(
    payload: MFAVerifyRequest,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
) -> dict:
    """Verify MFA enrollment with a TOTP code from authenticator app."""
    if actor.user.mfa_enabled:
        raise HTTPException(400, "MFA already enabled")

    success = await mfa_service.verify_mfa_enrollment(actor.user, payload.code, payload.enrollment_ticket, db)
    if not success:
        raise HTTPException(400, "Invalid TOTP code")

    return {"status": "enabled", "message": "MFA successfully enabled"}


@router.post("/auth/mfa/disable")
async def disable_mfa(
    payload: MFADisableRequest,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
) -> dict:
    """Disable MFA (requires password confirmation)."""
    if not actor.user.mfa_enabled:
        raise HTTPException(400, "MFA not enabled")

    from app.core.security import verify_password
    if not verify_password(payload.password, actor.user.password_hash):
        raise HTTPException(401, "Invalid password")

    await mfa_service.disable_mfa(actor.user, db)
    return {"status": "disabled", "message": "MFA successfully disabled"}


@router.get("/auth/mfa/status")
async def mfa_status(actor: Actor = Depends(get_actor)) -> dict:
    """Get MFA status for current user."""
    return {
        "enabled": actor.user.mfa_enabled,
        "enrolled_at": actor.user.mfa_enrolled_at.isoformat() if actor.user.mfa_enrolled_at else None,
    }


@router.post("/auth/refresh", response_model=LoginResponse)
async def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Exchange a refresh token for a new access token + refresh token pair."""
    refresh_payload = await verify_and_consume_refresh_token(payload.refresh_token)
    if not refresh_payload:
        raise HTTPException(401, "Invalid or expired refresh token")

    user_id = UUID(refresh_payload["sub"])
    membership_id = UUID(refresh_payload["mid"])
    restaurant_id = UUID(refresh_payload["rid"])
    token_version = refresh_payload["ver"]

    # Verify membership still exists and is active
    membership = db.get(RestaurantMembership, membership_id)
    if not membership or membership.user_id != user_id:
        raise HTTPException(401, "Membership not found")
    if membership.status != "ACTIVE":
        raise HTTPException(401, "Membership is not active")
    if membership.token_version != token_version:
        # Token version mismatch = revoked (password change, role change, etc.)
        raise HTTPException(401, "Token revoked")

    # Create new token pair (rotate refresh token)
    access_token = create_access_token(
        user_id=user_id,
        membership_id=membership_id,
        restaurant_id=restaurant_id,
        token_version=token_version,
    )
    new_refresh_token = await create_refresh_token(
        user_id=user_id,
        membership_id=membership_id,
        restaurant_id=restaurant_id,
        token_version=token_version,
    )

    active_memberships = [m for m in membership.user.memberships if m.status == "ACTIVE"]
    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=auth_service.me_from_membership(membership.user, membership, active_memberships),
    )


@router.post("/auth/switch-membership", response_model=LoginResponse)
async def switch_membership(
    payload: SwitchMembershipRequest,
    actor: Actor = Depends(get_actor),
    db: Session = Depends(get_db),
) -> LoginResponse:
    # Verify the user has access to this membership
    target_membership = db.get(RestaurantMembership, payload.membership_id)
    if not target_membership or target_membership.user_id != actor.user.id:
        raise HTTPException(403, "Membership not found or access denied")
    if target_membership.status != "ACTIVE":
        raise HTTPException(403, "Membership is not active")

    # If branch_id provided, verify access
    active_branch_id = None
    if payload.branch_id:
        if target_membership.role != "OWNER":
            # Check if membership has access to this branch
            has_access = any(
                bs.branch_id == payload.branch_id for bs in target_membership.branch_scopes
            )
            if not has_access:
                raise HTTPException(403, "No access to this branch")
        active_branch_id = payload.branch_id

    token = create_access_token(
        user_id=actor.user.id,
        membership_id=target_membership.id,
        restaurant_id=target_membership.restaurant_id,
        token_version=target_membership.token_version,
    )
    new_refresh_token = await create_refresh_token(
        user_id=actor.user.id,
        membership_id=target_membership.id,
        restaurant_id=target_membership.restaurant_id,
        token_version=target_membership.token_version,
    )
    active_memberships = [m for m in actor.user.memberships if m.status == "ACTIVE"]
    return LoginResponse(
        access_token=token,
        refresh_token=new_refresh_token,
        user=auth_service.me_from_membership(
            actor.user, target_membership, active_memberships, active_branch_id
        ),
    )


@router.get("/me", response_model=MeOut)
def me(actor: Actor = Depends(get_actor)) -> MeOut:
    return auth_service.me_from_membership(actor.user, actor.membership)


# ──────────────────────────────────────────────────────────────────────────────
# Invitation acceptance (public endpoints, no auth required)
# ──────────────────────────────────────────────────────────────────────────────

class InvitationTokenRequest(BaseModel):
    token: str


class InvitationValidateResponse(BaseModel):
    valid: bool
    email: str | None = None
    restaurant_name: str | None = None
    expires_at: str | None = None


class InvitationAcceptRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


@router.post("/invitations/validate", response_model=InvitationValidateResponse)
async def validate_invitation(
    payload: InvitationTokenRequest,
    db: Session = Depends(get_db),
) -> InvitationValidateResponse:
    """Validate an invitation token (public endpoint)."""
    token_hash = hash_token(payload.token)
    invitation = db.scalar(
        __import__("sqlalchemy").select(PlatformOneTimeToken).where(
            PlatformOneTimeToken.token_hash == token_hash,
            PlatformOneTimeToken.purpose == "OWNER_INVITE",
        )
    )

    if not invitation:
        return InvitationValidateResponse(valid=False)

    if invitation.used_at is not None:
        return InvitationValidateResponse(valid=False, email=invitation.email)

    if invitation.expires_at < datetime.now(UTC):
        return InvitationValidateResponse(valid=False, email=invitation.email)

    # Get restaurant name
    from app.modules.tenancy.models import Restaurant
    restaurant = db.get(Restaurant, invitation.restaurant_id) if invitation.restaurant_id else None

    return InvitationValidateResponse(
        valid=True,
        email=invitation.email,
        restaurant_name=restaurant.name if restaurant else None,
        expires_at=invitation.expires_at.isoformat(),
    )


@router.post("/invitations/accept", response_model=LoginResponse)
async def accept_invitation(
    payload: InvitationAcceptRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Accept an invitation and set password (public endpoint)."""
    from datetime import UTC, datetime

    token_hash = hash_token(payload.token)
    invitation = db.scalar(
        __import__("sqlalchemy").select(PlatformOneTimeToken).where(
            PlatformOneTimeToken.token_hash == token_hash,
            PlatformOneTimeToken.purpose == "OWNER_INVITE",
        )
    )

    if not invitation:
        raise HTTPException(400, "Invalid or expired invitation token")

    if invitation.used_at is not None:
        raise HTTPException(400, "Invitation already used")

    if invitation.expires_at < datetime.now(UTC):
        raise HTTPException(400, "Invitation has expired")

    # Find the invited user
    from app.modules.identity.models import User
    user = db.scalar(
        __import__("sqlalchemy").select(User).where(
            User.email == invitation.email,
            User.status == "INVITED",
        )
    )

    if not user:
        raise HTTPException(400, "Invitation user not found")

    # Update user with password and activate
    user.password_hash = hash_password(payload.password)
    user.status = "ACTIVE"

    # Mark invitation as used
    invitation.used_at = datetime.now(UTC)

    # Create first membership (owner) if not exists
    membership = db.scalar(
        __import__("sqlalchemy").select(RestaurantMembership).where(
            RestaurantMembership.user_id == user.id,
            RestaurantMembership.restaurant_id == invitation.restaurant_id,
        )
    )

    if not membership and invitation.restaurant_id:
        from uuid import uuid4
        membership_id = uuid4()
        db.execute(
            __import__("sqlalchemy").text(
                """
                INSERT INTO restaurant_memberships
                    (id, restaurant_id, user_id, role, status, token_version, created_at, updated_at)
                VALUES
                    (:id, :rid, :uid, 'owner', 'ACTIVE', 0, :now, :now)
                """
            ),
            {
                "id": membership_id,
                "rid": invitation.restaurant_id,
                "uid": user.id,
                "now": datetime.now(UTC),
            },
        )
        membership = db.get(RestaurantMembership, membership_id)

    if not membership:
        raise HTTPException(400, "Failed to create membership")

    db.commit()

    # Create token pair
    active_memberships = [m for m in user.memberships if m.status == "ACTIVE"]
    access_token = create_access_token(
        user_id=user.id,
        membership_id=membership.id,
        restaurant_id=membership.restaurant_id,
        token_version=membership.token_version,
    )
    refresh_token = await create_refresh_token(
        user_id=user.id,
        membership_id=membership.id,
        restaurant_id=membership.restaurant_id,
        token_version=membership.token_version,
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=auth_service.me_from_membership(user, membership, active_memberships),
    )
