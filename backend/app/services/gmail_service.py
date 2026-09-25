import base64
import logging
import mimetypes
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
import httpx
from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger("santamaria")

GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def html_to_plain_text(html_content: str) -> str:
    """
    Remove tags HTML básicas para produzir a versão em texto puro da mensagem,
    preservando quebras de linha e marcadores de lista.
    """
    if not html_content:
        return ""
    import html
    text = html.unescape(html_content)
    text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</(ul|ol)>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class GmailService:

    @staticmethod
    def enviar_email(
        access_token: str,
        destinatarios: str,
        assunto: str,
        corpo_html: str,
        copia: Optional[str] = None,
        reply_message_id: Optional[str] = None,
        reply_thread_id: Optional[str] = None,
        anexos: Optional[List[UploadFile]] = None,
        remetente_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Monta uma mensagem MIME usando MIMEMultipart explícito (sem MIME-Version em sub-partes)
        e envia via Gmail API REST. Suporta HTML, texto plano, Cc e anexos binários.
        """
        if not destinatarios or not destinatarios.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pelo menos um destinatário deve ser informado.",
            )

        if not assunto or not assunto.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O assunto da mensagem é obrigatório.",
            )

        # Verifica se há anexos reais com conteúdo
        lista_anexos = list(anexos) if anexos else []
        tem_anexos = len(lista_anexos) > 0

        # Estrutura MIME:
        # - Com anexos:  multipart/mixed → multipart/alternative (plain + html) + cada anexo
        # - Sem anexos:  multipart/alternative (plain + html)
        if tem_anexos:
            msg_raiz = MIMEMultipart("mixed")
            corpo_container = MIMEMultipart("alternative")
            msg_raiz.attach(corpo_container)
        else:
            msg_raiz = MIMEMultipart("alternative")
            corpo_container = msg_raiz

        # Cabeçalhos principais (apenas no nível raiz — sub-partes não devem ter MIME-Version)
        # Nota: NÃO definimos "From" aqui — deixamos o Gmail API puxar do contexto OAuth.
        # Definir From explicitamente pode causar conflito de assinatura DKIM para destinatários externos.
        msg_raiz["To"] = destinatarios.strip()
        msg_raiz["Subject"] = assunto.strip()
        if copia and copia.strip():
            msg_raiz["Cc"] = copia.strip()
            
        rfc_message_id = None
        if reply_message_id:
            # Para clientes externos, o In-Reply-To precisa ser o formato RFC 2822 (<...>)
            if reply_message_id.startswith("<") and reply_message_id.endswith(">"):
                rfc_message_id = reply_message_id
            else:
                try:
                    with httpx.Client(timeout=5.0) as client:
                        res = client.get(
                            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{reply_message_id}",
                            params={"format": "metadata", "metadataHeaders": "Message-ID"},
                            headers={"Authorization": f"Bearer {access_token}"}
                        )
                        if res.status_code == 200:
                            headers = res.json().get("payload", {}).get("headers", [])
                            for h in headers:
                                if h.get("name", "").lower() == "message-id":
                                    rfc_message_id = h.get("value")
                                    break
                except Exception as e:
                    logger.warning("Falha ao buscar Message-ID RFC 2822 para a mensagem %s: %s", reply_message_id, e)
            
            if rfc_message_id:
                msg_raiz["In-Reply-To"] = rfc_message_id
                msg_raiz["References"] = rfc_message_id
            else:
                # Fallback, mas pode quebrar a thread em clientes externos
                msg_raiz["In-Reply-To"] = reply_message_id
                msg_raiz["References"] = reply_message_id

        # Parte texto puro
        plain_text = html_to_plain_text(corpo_html) or " "
        corpo_container.attach(MIMEText(plain_text, "plain", "utf-8"))

        # Parte HTML (com estilos inline para compatibilidade máxima de clientes de e-mail)
        if corpo_html and corpo_html.strip():
            html_styled = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:#1e293b;background:#fff;">
  <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:#1e293b;">
    {corpo_html}
  </div>
</body>
</html>"""
            corpo_container.attach(MIMEText(html_styled, "html", "utf-8"))

        # Anexos — cada arquivo como parte binária separada no nível mixed
        if tem_anexos:
            for upload_file in lista_anexos:
                try:
                    upload_file.file.seek(0)
                    conteudo = upload_file.file.read()
                    if not conteudo:
                        continue

                    filename = upload_file.filename or "anexo"
                    ctype, encoding = mimetypes.guess_type(filename)
                    if ctype is None or encoding is not None:
                        ctype = "application/octet-stream"
                    maintype, subtype = ctype.split("/", 1)

                    parte = MIMEBase(maintype, subtype)
                    parte.set_payload(conteudo)
                    encoders.encode_base64(parte)
                    # RFC 5987 — encoding correto para nomes com espaços e acentos
                    parte.add_header(
                        "Content-Disposition",
                        "attachment",
                        filename=("utf-8", "", filename),
                    )
                    msg_raiz.attach(parte)
                except Exception as e:
                    logger.error("Erro ao processar anexo %s: %s", getattr(upload_file, "filename", "desconhecido"), e)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Falha ao ler o anexo '{getattr(upload_file, 'filename', '')}': {str(e)}",
                    )

        # Codificação Base64 URL-safe exigida pela Gmail API
        raw_bytes = msg_raiz.as_bytes()
        raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

        # Envio via REST
        req_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {"raw": raw_b64}
        if reply_thread_id:
            payload["threadId"] = reply_thread_id

        try:
            # Timeout separado: conexão curta, escrita longa (para anexos grandes), leitura moderada
            timeout = httpx.Timeout(connect=10.0, write=120.0, read=60.0, pool=5.0)
            with httpx.Client(timeout=timeout) as client:
                res = client.post(GMAIL_SEND_URL, headers=req_headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    logger.info("E-mail enviado com sucesso pelo Gmail. MessageId: %s", data.get("id"))
                    return {
                        "sucesso": True,
                        "messageId": data.get("id"),
                        "threadId": data.get("threadId"),
                    }

                logger.error("Erro ao enviar mensagem via Gmail API: %s (Status: %s)", res.text, res.status_code)
                error_detail = res.text
                try:
                    res_json = res.json()
                    error_detail = res_json.get("error", {}).get("message", res.text)
                except Exception:
                    pass

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"O Gmail recusou o envio da mensagem: {error_detail}",
                )
        except httpx.RequestError as e:
            logger.error("Falha de conexão ao enviar e-mail pelo Gmail: %s", e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não foi possível conectar aos servidores do Gmail: {str(e)}",
            )
