from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_actor, Actor
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, MeOut
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    return auth_service.login(db, payload.email, payload.password)


@router.get("/me", response_model=MeOut)
def me(actor: Actor = Depends(get_actor)) -> MeOut:
    return auth_service.me_from_membership(actor.user, actor.membership)
