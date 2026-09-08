from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Registra um novo usuário no sistema.
    """
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="Já existe um usuário com esse email cadastrado.",
        )
    
    hashed_password = security.get_password_hash(user_in.password)
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password=hashed_password,
        active='N'
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login_user(user_in: UserLogin, db: Session = Depends(get_db)):
    """
    Autentica um usuário e retorna um token JWT.
    """
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email ou senha incorretos")
    if not security.verify_password(user_in.password, user.password):
        raise HTTPException(status_code=400, detail="Email ou senha incorretos")
    if user.active != 'S':
        raise HTTPException(status_code=400, detail="Usuário bloqueado pelo administrador")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.iduser, expires_delta=access_token_expires
    )
    query = text("""
        SELECT r.name 
        FROM roles r 
        JOIN userrole ur ON r.idRole = ur.idRole 
        WHERE ur.idUser = :user_id
    """)
    result = db.execute(query, {"user_id": user.iduser}).first()
    role_name = result[0] if result else 'user'

    return {
        "access_token": access_token,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "iduser": user.iduser,
        "name": user.name,
        "email": user.email,
        "createdAt": user.createdAt,
        "role": role_name
    }

@router.get("/me", response_model=UserResponse)
def get_user_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retorna os dados do usuário logado atualmente.
    """
    query = text("""
        SELECT r.name 
        FROM roles r 
        JOIN userrole ur ON r.idRole = ur.idRole 
        WHERE ur.idUser = :user_id
    """)
    result = db.execute(query, {"user_id": current_user.iduser}).first()
    role_name = result[0] if result else 'user'
    
    return {
        "name": current_user.name,
        "email": current_user.email,
        "iduser": current_user.iduser,
        "createdAt": current_user.createdAt,
        "role": role_name
    }
