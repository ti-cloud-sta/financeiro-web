import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
from sqlalchemy import create_engine, text
import urllib.parse

pwd = "Likeaboos@70"
url = f"mysql+pymysql://root:{urllib.parse.quote_plus(pwd)}@localhost:3306/stamariabd"
engine = create_engine(url)

with engine.connect() as conn:
    print("Recent history events:")
    res = conn.execute(text("SELECT idhistoricopendencia, idNfPendencias, tipo, observacao, createdAt FROM historicopendencia WHERE tipo IN ('Alteração de Status', 'Atualização de Carteira', 'Pendencia Importada') ORDER BY idhistoricopendencia DESC LIMIT 50")).fetchall()
    for row in res:
        print(f"[{row[4]}] ID_NF: {row[1]}, Tipo: {row[2]}, Obs: {row[3]}")


