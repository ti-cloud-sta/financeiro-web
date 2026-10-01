import os
import sys
import subprocess
import smtplib
import zipfile
from email.message import EmailMessage
from datetime import datetime

# Garante que o script possa ser rodado via cron independentemente do diretório atual
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Pode usar dotenv se quiser carregar do .env do backend, mas para cron simples as configs no topo ajudam:
try:
    from dotenv import load_dotenv
    # Carrega .env da pasta pai (backend)
    load_dotenv(os.path.join(SCRIPT_DIR, '..', '.env'))
except ImportError:
    pass

# ================= CONFIGURAÇÕES =================
# Tenta pegar do ambiente (ex: VPS), senão usa o padrão fixado
DB_USER = os.getenv("DATABASE_USER", "root")
DB_PASS = os.getenv("DATABASE_PASSWORD", "sua_senha_do_banco_aqui")
DB_NAME = os.getenv("DATABASE_NAME", "stamariabd")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com") # ou smtp.office365.com
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "seu_email@empresa.com.br")
SMTP_PASS = os.getenv("SMTP_PASS", "sua_senha_app_aqui")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO", "diretoria@empresa.com.br")
# =================================================

data_atual = datetime.now().strftime("%Y-%m-%d_%H-%M")
sql_filename = os.path.join(SCRIPT_DIR, f"backup_{DB_NAME}_{data_atual}.sql")
zip_filename = os.path.join(SCRIPT_DIR, f"backup_{DB_NAME}_{data_atual}.zip")

def rodar_backup():
    print(f"[{datetime.now()}] Iniciando rotina de backup...")
    try:
        # 1. Faz o Dump usando mysqldump
        # Note: No linux VPS, mysqldump normalmente está no PATH.
        print(f"[{datetime.now()}] -> Gerando dump do banco de dados '{DB_NAME}'...")
        dump_cmd = f"mysqldump -u {DB_USER} -p'{DB_PASS}' {DB_NAME} > {sql_filename}"
        subprocess.run(dump_cmd, shell=True, check=True)
        
        # 2. Compacta para ZIP
        print(f"[{datetime.now()}] -> Compactando {sql_filename} para ZIP...")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(sql_filename, os.path.basename(sql_filename))
            
        # Limpeza do arquivo .sql pesado
        if os.path.exists(sql_filename):
            os.remove(sql_filename)
        
        # 3. Dispara o E-mail com anexo
        print(f"[{datetime.now()}] -> Preparando e-mail para {EMAIL_DESTINO}...")
        msg = EmailMessage()
        msg['Subject'] = f"🛡️ Backup Diário do ERP: {DB_NAME} - {data_atual}"
        msg['From'] = SMTP_USER
        msg['To'] = EMAIL_DESTINO
        msg.set_content(f"Olá!\n\nSegue em anexo o backup integral do banco de dados '{DB_NAME}' gerado em {data_atual}.\n\nEste é um e-mail automático gerado pela VPS.")
        
        with open(zip_filename, 'rb') as f:
            file_data = f.read()
            msg.add_attachment(file_data, maintype='application', subtype='zip', filename=os.path.basename(zip_filename))
            
        print(f"[{datetime.now()}] -> Conectando ao servidor SMTP {SMTP_SERVER}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            
        # (Opcional) Remove o ZIP local após enviar com sucesso para poupar disco
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        
        print(f"[{datetime.now()}] -> Sucesso! Backup gerado e enviado.")

    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] ERRO AO FAZER DUMP: {e}")
    except Exception as e:
        print(f"[{datetime.now()}] ERRO GERAL: {e}")

if __name__ == "__main__":
    # Verifica credenciais básicas
    if DB_PASS == "sua_senha_do_banco_aqui":
        print("AVISO: Credenciais de banco ou SMTP não foram preenchidas no código. Edite o script ou configure as variáveis de ambiente.")
    
    rodar_backup()
