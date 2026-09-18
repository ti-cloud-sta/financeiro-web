import logging
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.google_auth_service import GoogleAuthService

logger = logging.getLogger("santamaria")

router = APIRouter()


@router.get("/url")
def obter_url_autorizacao(current_user: User = Depends(get_current_user)):
    """
    Gera a URL de autorização do Google OAuth 2.0 contendo state assinado com o id do usuário.
    """
    try:
        url = GoogleAuthService.gerar_url_autorizacao(current_user.iduser)
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao gerar URL do Google OAuth: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao preparar autenticação do Google: {str(e)}",
        )


@router.get("/callback", response_class=HTMLResponse)
def callback_google_oauth(
    code: str = Query(..., description="Código de autorização retornado pelo Google"),
    state: str = Query(..., description="State assinado contendo a identificação do usuário"),
    db: Session = Depends(get_db),
):
    """
    Endpoint público acessado pelo navegador via redirecionamento do Google após o consentimento.
    Processa o código, grava o refresh token no banco e fecha a janela popup retornando postMessage.
    """
    try:
        resultado = GoogleAuthService.processar_callback(code=code, state=state, db=db)
        email = resultado.get("email") or ""

        html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Autorização do Gmail Concluída</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
      background-color: #f8fafc;
      color: #1e293b;
      text-align: center;
    }}
    .card {{
      background: #ffffff;
      padding: 2.5rem 2rem;
      border-radius: 14px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.06);
      max-width: 400px;
      width: 90%;
      border: 1px solid #e2e8f0;
    }}
    .icon {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 56px;
      height: 56px;
      background-color: #dcfce7;
      color: #16a34a;
      border-radius: 50%;
      font-size: 28px;
      margin-bottom: 1.25rem;
    }}
    h2 {{
      margin: 0 0 0.5rem;
      font-size: 1.25rem;
      font-weight: 600;
      color: #0f172a;
    }}
    p {{
      color: #64748b;
      font-size: 0.9rem;
      line-height: 1.5;
      margin: 0 0 1rem;
    }}
    .email-badge {{
      display: inline-block;
      background-color: #f1f5f9;
      color: #334155;
      font-size: 0.85rem;
      font-weight: 500;
      padding: 0.35rem 0.75rem;
      border-radius: 6px;
      margin-bottom: 1rem;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✓</div>
    <h2>Conta Conectada!</h2>
    <p>Sua conta do Gmail foi vinculada com sucesso ao Santamaria ERP.</p>
    {f'<div class="email-badge">{email}</div>' if email else ''}
    <p style="font-size: 0.8rem; color: #94a3b8;">Esta janela será fechada automaticamente em instantes...</p>
  </div>
  <script>
    try {{
      if (window.opener) {{
        window.opener.postMessage({{ type: 'GOOGLE_AUTH_SUCCESS', email: '{email}' }}, '*');
        setTimeout(function() {{ window.close(); }}, 1200);
      }} else {{
        setTimeout(function() {{ window.location.href = '/'; }}, 2000);
      }}
    }} catch (e) {{
      console.error(e);
    }}
  </script>
</body>
</html>"""
        return HTMLResponse(content=html_content, status_code=200)

    except HTTPException as e:
        logger.error("Erro HTTP no callback do Google: %s", e.detail)
        error_msg = str(e.detail)
        html_error = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Erro de Autorização</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;
      background-color: #f8fafc; color: #1e293b; text-align: center;
    }}
    .card {{
      background: #ffffff; padding: 2.5rem 2rem; border-radius: 14px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.06); max-width: 420px; width: 90%; border: 1px solid #fee2e2;
    }}
    .icon {{
      display: inline-flex; align-items: center; justify-content: center;
      width: 56px; height: 56px; background-color: #fee2e2; color: #dc2626; border-radius: 50%;
      font-size: 28px; margin-bottom: 1.25rem;
    }}
    h2 {{ margin: 0 0 0.5rem; font-size: 1.25rem; color: #991b1b; }}
    p {{ color: #64748b; font-size: 0.9rem; line-height: 1.5; margin: 0 0 1.5rem; }}
    button {{
      background-color: #dc2626; color: white; border: none; padding: 0.6rem 1.25rem;
      border-radius: 6px; font-weight: 500; cursor: pointer;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">✕</div>
    <h2>Falha na Autorização</h2>
    <p>{error_msg}</p>
    <button onclick="window.close()">Fechar Janela</button>
  </div>
  <script>
    if (window.opener) {{
      window.opener.postMessage({{ type: 'GOOGLE_AUTH_ERROR', detail: '{error_msg}' }}, '*');
    }}
  </script>
</body>
</html>"""
        return HTMLResponse(content=html_error, status_code=e.status_code)
    except Exception as e:
        logger.error("Exceção inesperada no callback do Google: %s", e)
        error_msg = f"Erro inesperado: {str(e)}"
        html_error = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Erro de Autorização</title>
</head>
<body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
  <h2 style="color: #dc2626;">Falha ao conectar com o Google</h2>
  <p>{error_msg}</p>
  <button onclick="window.close()" style="padding: 8px 16px;">Fechar</button>
  <script>
    if (window.opener) {{
      window.opener.postMessage({{ type: 'GOOGLE_AUTH_ERROR', detail: '{error_msg}' }}, '*');
    }}
  </script>
</body>
</html>"""
        return HTMLResponse(content=html_error, status_code=500)


@router.get("/status")
def obter_status_conexao(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retorna o status atual da conexão do usuário com a conta Google.
    """
    try:
        return GoogleAuthService.verificar_status(current_user, db)
    except Exception as e:
        logger.error("Erro ao checar status do Google OAuth: %s", e)
        return {"conectado": False, "email": None}


@router.post("/desconectar")
def desconectar_google(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Desconecta a conta do Google do usuário logado, revogando e limpando o refresh token.
    """
    try:
        return GoogleAuthService.desconectar(current_user, db)
    except Exception as e:
        logger.error("Erro ao desconectar conta Google: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao desconectar conta Google: {str(e)}",
        )
