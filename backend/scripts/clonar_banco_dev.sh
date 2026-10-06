#!/bin/sh
# Clona o banco de produção (stamariabd) para o banco de desenvolvimento (stamariabd_dev).
#
# Roda no HOST da VPS (não dentro de container), disparado pelo timer systemd
# clone-banco-dev.timer toda sexta-feira às 00:00 (America/Sao_Paulo).
# Execução manual:  sh /root/projects/financeiro-web/backend/scripts/clonar_banco_dev.sh
# Log:              /var/log/clone-banco-dev.log
#
# O dev é sobrescrito por completo: tudo o que foi alterado nele durante a semana é perdido.
set -eu

ORIGEM="stamariabd"
DESTINO="stamariabd_dev"
CONTAINER_DB="financeiro-web-db-1"
CONTAINER_BACKEND_DEV="financeiro-web-dev-backend-dev-1"
LOG="/var/log/clone-banco-dev.log"

exec >>"$LOG" 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
falhar() { log "ERRO: $*"; log "===== clone ABORTADO"; exit 1; }

# Trava de segurança: o destino nunca pode ser o banco de produção.
[ "$DESTINO" != "$ORIGEM" ] || falhar "destino igual à origem"
case "$DESTINO" in
  *_dev) ;;
  *) falhar "destino '$DESTINO' não termina com _dev" ;;
esac

# Executa o cliente mysql dentro do container do banco, sem expor a senha na linha de comando.
mysql_root() {
  docker exec -i "$CONTAINER_DB" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot --default-character-set=utf8mb4 "$@"' mysql "$@"
}

DUMP=$(mktemp /tmp/clone-banco-dev.XXXXXX)
trap 'rm -f "$DUMP"' EXIT

log "===== início do clone $ORIGEM -> $DESTINO"

# 1. Dump da produção. --single-transaction lê um snapshot consistente sem travar as tabelas.
#    Sem --databases: o dump não traz CREATE DATABASE/USE, então só pode ser importado onde mandarmos.
docker exec "$CONTAINER_DB" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysqldump -uroot --default-character-set=utf8mb4 --single-transaction --routines --triggers --events --set-gtid-purged=OFF --no-tablespaces "$1"' mysqldump "$ORIGEM" >"$DUMP" \
  || falhar "mysqldump falhou"

tail -n 1 "$DUMP" | grep -q "Dump completed" || falhar "dump incompleto"
if grep -qE "^USE |\`$ORIGEM\`\." "$DUMP"; then
  falhar "o dump referencia o banco $ORIGEM explicitamente; importar poderia gravar na produção"
fi
log "dump gerado ($(wc -c <"$DUMP") bytes)"

# 2. Recria o destino com o mesmo charset/collation da origem.
#    Os grants do usuário app_dev são por nome de banco e sobrevivem ao DROP.
set -- $(mysql_root -N -e "SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='$ORIGEM'")
[ $# -eq 2 ] || falhar "não foi possível ler o charset de $ORIGEM"
mysql_root -e "DROP DATABASE IF EXISTS \`$DESTINO\`; CREATE DATABASE \`$DESTINO\` CHARACTER SET $1 COLLATE $2;" \
  || falhar "não foi possível recriar $DESTINO"
log "banco $DESTINO recriado ($1 / $2)"

# 3. Importa o dump no destino.
mysql_root "$DESTINO" <"$DUMP" || falhar "importação falhou ($DESTINO pode estar incompleto)"
log "dump importado"

# 4. Limpeza: o dev não pode enviar e-mails reais pelas contas Gmail dos usuários.
mysql_root "$DESTINO" -e "UPDATE users SET refresh_token_google = NULL WHERE refresh_token_google IS NOT NULL;" \
  || falhar "não foi possível limpar os tokens Google"
log "tokens Google removidos do $DESTINO"

# 5. Validação: views apontando para o próprio dev e contagem de linhas por tabela.
VIEWS_PRODUCAO=$(mysql_root -N -e "SELECT COUNT(*) FROM information_schema.VIEWS WHERE TABLE_SCHEMA='$DESTINO' AND VIEW_DEFINITION LIKE '%\`$ORIGEM\`.%'")
[ "$VIEWS_PRODUCAO" = "0" ] || falhar "$VIEWS_PRODUCAO view(s) do $DESTINO leem dados do $ORIGEM"

DIVERGENTES=0
for TABELA in $(mysql_root -N -e "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='$ORIGEM' AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME"); do
  QTD_ORIGEM=$(mysql_root -N -e "SELECT COUNT(*) FROM \`$ORIGEM\`.\`$TABELA\`")
  QTD_DESTINO=$(mysql_root -N -e "SELECT COUNT(*) FROM \`$DESTINO\`.\`$TABELA\`")
  if [ "$QTD_ORIGEM" != "$QTD_DESTINO" ]; then
    # Pode ocorrer se a produção recebeu escrita entre o dump e a contagem.
    log "AVISO: $TABELA origem=$QTD_ORIGEM destino=$QTD_DESTINO"
    DIVERGENTES=$((DIVERGENTES + 1))
  fi
done
log "validação concluída: $DIVERGENTES tabela(s) com contagem diferente"

# 6. Reinicia o backend dev: as conexões abertas no pool apontavam para o banco que foi recriado.
if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_BACKEND_DEV"; then
  docker restart "$CONTAINER_BACKEND_DEV" >/dev/null || falhar "não foi possível reiniciar $CONTAINER_BACKEND_DEV"
  log "$CONTAINER_BACKEND_DEV reiniciado"
fi

log "===== clone concluído com sucesso"
