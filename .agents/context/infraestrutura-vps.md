# Contexto de Infraestrutura: VPS de Produção (Hostinger)

Mapeamento técnico do servidor de produção do ERP SANTAMARIA, levantado em modo somente leitura em **05/10/2026**. Valores de segredos (senhas, chaves, tokens) nunca devem ser registrados neste arquivo.

---

## 1. Servidor

| Item | Valor |
|---|---|
| Provedor | Hostinger (VPS) |
| Hostname | `srv1955604` |
| Domínio | `stamaria.cloud` / `www.stamaria.cloud` (IPv4 `187.127.7.252`) |
| Sistema | Ubuntu 26.04.1 LTS, kernel 7.0.0-30 |
| Recursos | 1 vCPU, 3,8 GB RAM, **sem swap**, disco 48 GB (≈13% usado) |
| Fuso do host | `Etc/UTC` (sincronizado via chrony) |
| Agentes do provedor | `monarx-agent` (scanner de malware da Hostinger), `qemu-guest-agent` |

### Acesso
- SSH na porta 22, usuário `root`.
- `/etc/ssh/sshd_config.d/50-cloud-init.conf` habilita `PasswordAuthentication yes` (sobrepõe o `no` do outro arquivo) e `PermitRootLogin yes`.
- Chaves autorizadas em `/root/.ssh/authorized_keys`: apenas `claude-code-readonly@financeiro-web` (chave do assistente). O acesso humano é por senha.
- `fail2ban` ativo desde 05/10/2026 (jail `sshd`: 5 falhas em 10 min → IP bloqueado por 10 min). Um bloqueio vale para todo o IP público da rede de origem.

### Firewall (UFW)
- Padrão: bloqueia entrada, libera saída.
- Liberadas: `22/tcp`, `80/tcp`, `443/tcp` (IPv4 e IPv6).
- MySQL (`3306`) e frontend (`8080`) escutam somente em `127.0.0.1`.

---

## 2. Aplicação (Docker Compose)

- Diretório: `/root/projects/financeiro-web` — clone HTTPS de `github.com/ti-cloud-sta/financeiro-web`, branch `main`.
- Deploy: `git pull` + `docker compose up -d --build [serviço]` (ver `notas.local.txt`).
- Docker 29.x e Compose v5.x; `docker` e `containerd` habilitados no boot.
- Projeto compose `financeiro-web`, todos com `restart: unless-stopped`:

| Container | Imagem | Porta | Observação |
|---|---|---|---|
| `financeiro-web-frontend-1` | build `./frontend` (nginx:alpine) | `127.0.0.1:8080 → 80` | Serve o Angular e faz proxy de `/api/v1/` para `backend:8000`. Fuso UTC. |
| `financeiro-web-backend-1` | build `./backend` (python:3.12-slim) | `8000` (rede interna) | Uvicorn, 1 worker. Fuso `America/Sao_Paulo`. |
| `financeiro-web-db-1` | `mysql:8.0` | `127.0.0.1:3306` | Healthcheck ativo. Volume `financeiro-web_db_data`. Fuso `-03:00`. |

### Variáveis do `.env` da raiz (somente nomes)
`MYSQL_ROOT_PASSWORD`, `JWT_KEY`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `FRONTEND_URL`.
- `FRONTEND_URL` existe no `.env`, mas não é repassada pelo `docker-compose.yml` ao backend.
- Não há variáveis `SMTP_*` (necessárias para o script de backup).

---

## 3. Proxy Reverso e HTTPS (nginx do host)

Fluxo de uma requisição:

```text
Internet → nginx do host (:443, TLS) → 127.0.0.1:8080 (nginx do container frontend)
         → /api/v1/* → backend:8000 (Uvicorn)
         → demais rotas → arquivos do Angular (fallback index.html)
```

- Site: `/etc/nginx/sites-available/stamaria.cloud` (link em `sites-enabled`). HTTP `:80` redireciona para HTTPS.
- Certificado Let's Encrypt (`certbot`), renovação automática pelo `certbot.timer`. Validade atual até **03/12/2026**.
- `/etc/nginx/nginx.conf`: `client_max_body_size 100M`, `gzip on`.
- Até 05/10/2026 não havia `proxy_read_timeout` em nenhuma das camadas (limite padrão de 60 s; houve 504 em `POST /api/v1/despesas-viagens/analisar-arquivo` em 01/10/2026). O `frontend/nginx.conf` passou a usar 300 s e `proxy_buffering off` em `/api/v1/`; o nginx do host precisa do mesmo ajuste (ver seção 6, passo 7).

---

## 4. Banco de Dados

- MySQL 8.0.46, schema `stamariabd` (≈3,5 MB), `lower_case_table_names=1`, `time_zone=-03:00`, charset `utf8mb4`.
- Usuários: apenas `root` (`%` e `localhost`); a porta só é acessível pela própria máquina.
- View `vw_nfpendencias_fase` existe somente no banco (o DDL não está no repositório). Há também a tabela `colaboradorunidade`, sem model no backend.
- Situação em 05/10/2026: `nfpendencias`, `historicopendencia`, `tratativas`, `nfpendencias_mensagens` e `turnover_planos_saude` **vazias**, embora existam 10 importações do tipo `PENDENCIAS` registradas.
- Consulta somente leitura (SQL via stdin, sem expor a senha):
  ```bash
  docker exec -i financeiro-web-db-1 sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot stamariabd' < consulta.sql
  ```

---

## 5. Rotinas Agendadas

| Rotina | Agendamento | Origem |
|---|---|---|
| `docker builder prune -f` | segundas, 02:33 UTC | `/etc/cron.d/docker-builder-prune` |
| `docker image prune -af --filter until=24h` | diário, 04:29 UTC | `/etc/cron.d/docker-image-prune` |
| Renovação de certificado | 2x ao dia | `certbot.timer` |
| Atualizações de segurança | diário (`apt-daily-upgrade.timer`) | `unattended-upgrades` — apenas origem `-security`, **sem reboot automático** |
| Backup do banco | **não configurado** | `backend/scripts/backup_rotina.py` existe, mas sem crontab e sem `SMTP_*` |

---

## 6. Ambiente de Teste

Mesmo repositório, dois ambientes independentes no mesmo domínio. O caminho define tudo: cada site consome a própria API, que consome o próprio banco.

```text
PRODUÇÃO  https://stamaria.cloud/         → frontend (main)     → /api/v1        → backend (main)     → stamariabd
TESTE     https://stamaria.cloud/teste/   → frontend-dev (dev)  → /teste/api/v1  → backend-dev (dev)  → stamariabd_dev
```

Todas as rotas do teste ficam sob `/teste/` (ex.: `/teste/login`, `/teste/inadimplencia`, `/teste/compartilhar/logistica`).

| Peça | Detalhe |
|---|---|
| Banco | `stamariabd_dev` no mesmo MySQL; usuário `app_dev` com acesso **somente** a esse banco. |
| Clone | `backend/scripts/clonar_banco_dev.sh` (host), toda **sexta 00:00 (Brasília)** via `clone-banco-dev.timer`. Recria o banco de teste do zero, apaga `users.refresh_token_google`, valida views/contagens e reinicia o `backend-dev`. Log: `/var/log/clone-banco-dev.log`. |
| Containers | Checkout da branch `dev` em `/root/projects/financeiro-web-dev`, subido com `docker-compose.dev.yml` (projeto `financeiro-web-dev`): `frontend-dev` em `127.0.0.1:8081` e `backend-dev` (JWT próprio `JWT_KEY_DEV`, Gmail desligado, `ENVIRONMENT=development`). |
| Redes | Rede própria `financeiro-web-dev_teste`, onde o `backend-dev` tem o alias `backend` (por isso o mesmo `frontend/nginx.conf` serve aos dois ambientes). O `backend-dev` também entra na rede `financeiro-web_default` **só para alcançar o `db`** — lá ele é apenas `backend-dev` e nunca recebe tráfego de produção. Não conectar o `frontend-dev` à rede de produção. |
| Frontend | Mesmo código, sem seletor. O `frontend-dev` é buildado com `--base-href /teste/` (build arg `BASE_HREF` no `Dockerfile`). `core/config/ambiente.ts` deriva tudo do `<base href>`: `apiUrl` vira `/teste/api/v1`, o badge "Ambiente de Teste" e a navbar laranja aparecem, e as chaves de sessão (`erp_access_token`, `erp_current_user`, `despesas_viagens_draft`) ganham o prefixo `teste_` — os dois ambientes compartilham o `localStorage` por estarem no mesmo domínio. |
| Roteamento | Bloco `location /teste/` no site `stamaria.cloud` do nginx do host → `127.0.0.1:8081/` (remove o prefixo). O nginx do `frontend-dev` recebe `/api/v1/...` e `/rotas` como na produção. Sem domínio, DNS ou certificado novos. |
| Atenção | Caminhos absolutos no front (`'/algo'` em `http.get`, `fetch`, `href`, `src`) quebram o teste: usar caminhos relativos ao `<base href>` ou `environment.apiUrl`. Links fixos do backend para `https://stamaria.cloud/compartilhar/...` (e-mails de compartilhamento) apontam sempre para a produção — no teste o Gmail fica desligado. |

### Instalação (uma vez)
1. Banco e usuário (executado pelo usuário em 05/10/2026): `CREATE DATABASE stamariabd_dev`, `CREATE USER 'app_dev'@'%'`, `GRANT ALL ON stamariabd_dev.*`.
2. Checkout dev:
   ```bash
   git clone -b dev https://github.com/ti-cloud-sta/financeiro-web.git /root/projects/financeiro-web-dev
   ```
3. `.env` em `/root/projects/financeiro-web-dev/.env` com `MYSQL_DEV_PASSWORD`, `JWT_KEY_DEV` (gerar com `openssl rand -hex 32`, diferente da produção), `GEMINI_API_KEY`, `GEMINI_MODEL`; `chmod 600`.
4. Timer do clone (o script é executado a partir do checkout de **produção**, então precisa estar na `main`):
   ```bash
   cp /root/projects/financeiro-web/backend/scripts/systemd/clone-banco-dev.* /etc/systemd/system/
   systemctl daemon-reload && systemctl enable --now clone-banco-dev.timer
   systemctl start clone-banco-dev.service   # primeiro clone
   ```
5. Subir o teste: `cd /root/projects/financeiro-web-dev && docker compose -f docker-compose.dev.yml up -d --build`
6. nginx do host, no bloco `server` HTTPS de `/etc/nginx/sites-available/stamaria.cloud` (antes do `location /`):
   ```nginx
   location = /teste { return 301 /teste/; }

   location /teste/ {
       proxy_pass http://127.0.0.1:8081/;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_read_timeout 300s;
       proxy_send_timeout 300s;
       proxy_buffering off;
   }
   ```
   No `location /` existente, acrescentar os mesmos `proxy_read_timeout`/`proxy_send_timeout`/`proxy_buffering`. Depois: `nginx -t && systemctl reload nginx`.
7. Rebuild do frontend de produção (timeouts no `nginx.conf` do container e `apiUrl` derivada do base href): `cd /root/projects/financeiro-web && docker compose up -d --build frontend`

### Operação
- Deploy do teste: `cd /root/projects/financeiro-web-dev && git pull && docker compose -f docker-compose.dev.yml up -d --build`
- Clone fora de hora: `systemctl start clone-banco-dev.service`
- Próxima execução: `systemctl list-timers clone-banco-dev.timer`

---

## 7. Pendências Levantadas (05/10/2026)

| # | Item | Decisão |
|---|---|---|
| 1 | Tabelas de pendências vazias em produção | Esperado — ignorar. |
| 2 | Backup do banco não configurado | Fazer depois (não é a próxima tarefa). |
| 3 | Timeout padrão de 60 s no proxy (host e container) | Container corrigido no `frontend/nginx.conf` (300 s + sem buffer); host aplicado junto com o ambiente dev. |
| 4 | SSH root com senha, sem fail2ban | fail2ban instalado em 05/10/2026 (5 falhas em 10 min → bloqueio de 10 min). Desligar senha: pendente (exige o usuário cadastrar a própria chave antes). |
| 5 | Reboot pendente desde 25/09 (kernel `7.0.0-34` e `libc6`) + 24 pacotes atualizáveis (inclui Docker/containerd) | Agendado pelo usuário: `manutencao-upgrade-reboot.timer` em 06/10/2026 06:30 UTC (log `/var/log/manutencao-upgrade-reboot.log`). |
| 6 | Fusos divergentes (host/frontend em UTC; backend/db em -03:00) | Ajustar depois. |
| 7 | `FRONTEND_URL` não repassada ao backend pelo compose | Ajustar depois. |

---

## 8. Regras Operacionais
- Qualquer alteração na VPS (configuração, pacotes, reinício, containers) só com pedido explícito do usuário; análises são somente leitura.
- Nunca imprimir valores do `.env` nem senhas; listar apenas nomes de variáveis.
- Alterações de schema continuam sendo executadas pelo usuário (ver `rules/banco-dados-sql.md`).
