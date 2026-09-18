import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import httpx
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger("santamaria")

GOOGLE_AUTH_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


class GoogleAuthService:

    @staticmethod
    def gerar_url_autorizacao(id_user: int) -> str:
        """
        Gera a URL para redirecionamento ao Google OAuth 2.0.
        O state é assinado como um token JWT para evitar ataques de CSRF e
        vincular a autorização ao id do usuário que iniciou o fluxo.
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Credenciais do Google OAuth não configuradas no servidor (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET).",
            )

        # Criação do state assinado (válido por 15 minutos)
        exp = datetime.now(timezone.utc) + timedelta(minutes=15)
        state_payload = {
            "sub": str(id_user),
            "exp": exp,
            "purpose": "google_oauth",
        }
        state_jwt = jwt.encode(state_payload, settings.JWT_KEY, algorithm=settings.ALGORITHM)

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",  # Garante o envio do refresh_token
            "prompt": "consent",       # Força nova confirmação para sempre receber o refresh_token
            "state": state_jwt,
        }

        return f"{GOOGLE_AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"

    @staticmethod
    def processar_callback(code: str, state: str, db: Session) -> Dict[str, Any]:
        """
        Processa o código recebido no callback do Google, troca pelo par de tokens
        (access_token e refresh_token) e armazena o refresh_token no usuário.
        """
        # 1. Validar e decodificar o state
        try:
            payload = jwt.decode(
                state,
                settings.JWT_KEY,
                algorithms=[settings.ALGORITHM],
            )
            if payload.get("purpose") != "google_oauth":
                raise HTTPException(status_code=400, detail="State inválido.")
            id_user = int(payload.get("sub"))
        except (jwt.PyJWTError, ValueError) as e:
            logger.error("Falha ao validar state do OAuth: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parâmetro state inválido ou expirado. Tente novamente.",
            )

        # 2. Localizar usuário no banco
        user = db.query(User).filter(User.iduser == id_user).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário do sistema não encontrado.")

        # 3. Trocar o authorization_code pelos tokens no Google
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(GOOGLE_TOKEN_URL, data=data)
                if res.status_code != 200:
                    logger.error("Erro na troca do token Google: %s", res.text)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Erro ao obter tokens do Google: {res.text}",
                    )
                tokens = res.json()
        except httpx.RequestError as e:
            logger.error("Erro de conexão com o Google: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falha de comunicação com os servidores do Google.",
            )

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        # 4. Salvar o refresh_token no usuário
        if refresh_token:
            user.refresh_token_google = refresh_token
            db.commit()
            db.refresh(user)
            logger.info("Novo refresh_token_google gravado para o usuário %s", user.iduser)
        elif not user.refresh_token_google:
            logger.warning("Google não retornou refresh_token e usuário %s ainda não possui um cadastrado.", user.iduser)

        # 5. Obter o e-mail do Google da conta conectada
        google_email = None
        if access_token:
            try:
                with httpx.Client(timeout=10.0) as client:
                    info_res = client.get(
                        GOOGLE_USERINFO_URL,
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    if info_res.status_code == 200:
                        user_info = info_res.json()
                        google_email = user_info.get("email")
            except Exception as e:
                logger.warning("Não foi possível buscar dados do perfil do Google: %s", e)

        return {
            "sucesso": True,
            "email": google_email,
            "id_user": user.iduser,
        }

    @staticmethod
    def obter_access_token_valido(user: User, db: Session) -> str:
        """
        Garante e retorna um access_token válido utilizando o refresh_token do usuário.
        Se a autorização tiver sido revogada pelo usuário no painel do Google, limpa o token no banco.
        """
        if not user.refresh_token_google:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Conta do Google não conectada. Por favor, autorize o envio de e-mails na aba de Mensagens.",
            )

        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": user.refresh_token_google,
            "grant_type": "refresh_token",
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(GOOGLE_TOKEN_URL, data=data)
                if res.status_code == 200:
                    tokens = res.json()
                    return tokens["access_token"]

                # Verificando se o token foi revogado
                res_data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                error_code = res_data.get("error", "")

                if res.status_code == 400 and error_code in ["invalid_grant", "unauthorized_client"]:
                    logger.warning("Refresh token inválido/revogado para o usuário %s. Limpando.", user.iduser)
                    user.refresh_token_google = None
                    db.commit()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Sua autorização de envio do Gmail expirou ou foi revogada. Por favor, conecte sua conta Google novamente.",
                    )

                logger.error("Erro ao renovar access_token do Google: %s", res.text)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Erro ao renovar credencial junto ao Google: {res.text}",
                )
        except httpx.RequestError as e:
            logger.error("Falha ao comunicar com Google Token endpoint: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Não foi possível comunicar com o servidor de autenticação do Google.",
            )

    @staticmethod
    def verificar_status(user: User, db: Session) -> Dict[str, Any]:
        """
        Verifica se o usuário possui autorização ativa com o Google e tenta obter o e-mail conectado.
        """
        if not user.refresh_token_google:
            return {"conectado": False, "email": None}

        # Tenta renovar o access_token para validar se a conexão permanece ativa
        try:
            access_token = GoogleAuthService.obter_access_token_valido(user, db)
            with httpx.Client(timeout=8.0) as client:
                info_res = client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if info_res.status_code == 200:
                    email = info_res.json().get("email")
                    return {"conectado": True, "email": email}
            return {"conectado": True, "email": None}
        except HTTPException as e:
            if e.status_code == 401:
                return {"conectado": False, "email": None}
            return {"conectado": True, "email": None}
        except Exception:
            return {"conectado": True, "email": None}

    @staticmethod
    def desconectar(user: User, db: Session) -> Dict[str, Any]:
        """
        Revoga o refresh token no Google e remove do banco de dados.
        """
        if user.refresh_token_google:
            try:
                with httpx.Client(timeout=8.0) as client:
                    client.post(
                        GOOGLE_REVOKE_URL,
                        params={"token": user.refresh_token_google},
                    )
            except Exception as e:
                logger.warning("Erro ao tentar revogar token no Google: %s", e)

            user.refresh_token_google = None
            db.commit()
            db.refresh(user)

        return {
            "sucesso": True,
            "mensagem": "Conta Google desconectada com sucesso.",
        }
