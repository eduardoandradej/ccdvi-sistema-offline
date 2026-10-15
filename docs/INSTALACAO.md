# Instalação e operação (Ubuntu Server 24.04 LTS)

**Requisitos mínimos sugeridos para laboratório:** x86_64, 4 vCPU, 8 GB de RAM e 50 GB de disco, mais o espaço dos
anexos. Este dimensionamento ainda não foi medido sob carga.

## 1. Desenvolvimento local (sem contêineres)

```bash
sudo apt update && sudo apt install -y git postgresql-16 python3.12-venv curl
# Node 22: instale pelo pacote oficial do NodeSource ou por binário pré-baixado (ver seção 4)
git clone <repo> && cd ccdvi-sistema-offline
sudo -u postgres psql -c "CREATE ROLE dvi LOGIN PASSWORD 'TROQUE_ESTA_SENHA' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE dvi OWNER dvi;"
sudo -u postgres psql -c "CREATE DATABASE dvi_test OWNER dvi;"   # para pytest
cp .env.example backend/.env       # ajuste DVI_DATABASE_URL e defina DVI_SEED_PASSWORD
scripts/dev-up.sh
```

Abra `http://<IP-do-servidor>:5173` em qualquer notebook ou tablet da mesma rede.

## 2. Implantação com Podman + Quadlet (rootless)

> Situação: os arquivos estão prontos (`deploy/`), mas **ainda não foram executados em um host com Podman**. O ambiente
> de desenvolvimento usado não tinha Podman, e a construção das imagens pelo Docker foi bloqueada por limite de
> requisições do registro e pelo proxy do ambiente. Validar no servidor do laboratório antes de considerar concluído.

```bash
sudo apt install -y podman
scripts/podman-deploy.sh build          # imagens localhost/dvi-api:0.1.0 e localhost/dvi-web:0.1.0
scripts/podman-deploy.sh secrets        # pede a senha do banco e cria os segredos Podman
sudo mkdir -p /etc/dvi && sudo cp deploy/config/dvi.env.example /etc/dvi/dvi.env && sudo chmod 600 /etc/dvi/dvi.env
sudo chown "$USER" /etc/dvi/dvi.env
scripts/podman-deploy.sh install        # copia as unidades para ~/.config/containers/systemd e inicia os serviços
DVI_SEED_PASSWORD='senha-de-laboratorio' scripts/podman-deploy.sh seed --demo-records
scripts/podman-deploy.sh status
```

Acesse `http://<IP-do-servidor>:8080`. Libere no firewall apenas a sub-rede da operação:

```bash
sudo ufw allow from 192.168.10.0/24 to any port 8080 proto tcp
```

O exemplo usa `192.168.10.0/24`; troque pela sub-rede real.

**HTTPS interno:**

1. Monte o certificado institucional no contêiner `dvi-web`.
2. Acrescente `listen 8443 ssl` em `deploy/config/nginx.conf`.
3. Defina `DVI_COOKIE_SECURE=true` em `/etc/dvi/dvi.env`.

## 3. Backup e restauração

```bash
export DVI_DATABASE_URL=postgresql+psycopg://dvi:SENHA@localhost:5432/dvi
export DVI_STORAGE_DIR=/caminho/dos/anexos
export DVI_BACKUP_GPG_RECIPIENT=<id da chave pública institucional>   # recomendado: backup cifrado
scripts/backup.sh /media/backup-autorizado

# Em ambiente limpo: banco vazio e diretório de anexos vazio
export DVI_DATABASE_URL=postgresql+psycopg://dvi:SENHA@localhost:5432/dvi_restaurado
export DVI_STORAGE_DIR=/novo/diretorio/vazio
scripts/restore.sh /media/backup-autorizado/dvi-backup-AAAAMMDDTHHMMSSZ.tar.gpg
```

O restore confere o manifesto SHA-256 do pacote e, depois de restaurar, recalcula o SHA-256 de cada anexo e compara com
o valor registrado no banco. Para Podman, execute os scripts com o `pg_dump` do contêiner, ou monte os volumes; essa
adaptação ainda está pendente.

## 4. Instalação sem internet (provisionamento isolado)

Prepare em uma máquina com internet e transfira por mídia autorizada:

1. Imagens: depois de `scripts/podman-deploy.sh build`, rode
   `podman save -o dvi-imagens.tar localhost/dvi-api:0.1.0 localhost/dvi-web:0.1.0 docker.io/library/postgres:16-bookworm`
   e depois `sha256sum dvi-imagens.tar > dvi-imagens.tar.sha256`.
2. No servidor isolado, rode `sha256sum -c dvi-imagens.tar.sha256 && podman load -i dvi-imagens.tar` e siga a seção 2,
   **sem** o passo `build`.
3. As versões das dependências Python e npm estão fixadas em `backend/pyproject.toml` e `frontend/package-lock.json`.
   Para desenvolvimento offline, use `pip download -d wheels .` e `npm ci --offline` com um cache pré-carregado.

## 5. Teste de operação sem internet

1. Desconecte o servidor e os notebooks da WAN e mantenha apenas a LAN/Wi-Fi local.
2. Execute o fluxo de demonstração (login, cadastro AM e PM, anexos, reconciliação).
3. Verificações automáticas:
   - `scripts/check-offline-assets.sh` confirma que o build do frontend não referencia nenhum recurso externo.
   - Os testes E2E (`frontend/e2e/fluxos.spec.ts`) registram todas as requisições do navegador e falham se houver
     qualquer host diferente do servidor local.
   - A CSP do Nginx (`default-src 'self'`) bloqueia, no navegador, qualquer recurso de outro domínio.
4. Bloqueio explícito de saída no servidor, para confirmar que a API não depende de internet:

   ```bash
   sudo iptables -I OUTPUT -o <interface-WAN> -j REJECT
   ```
