# Deploy na Oracle Cloud Free Tier

Guia para colocar este projeto no ar em uma VM Always Free da Oracle, com Gunicorn, Nginx e HTTPS.

Tempo estimado: 40 a 60 minutos. Custo dentro dos limites: R$ 0.

## Limites reais do Free Tier (2026)

A Oracle reduziu a cota Ampere em junho de 2026. Guias antigos ainda falam em 4 OCPU e 24 GB.

| Recurso | Cota Always Free |
|---|---|
| Ampere A1 (ARM) | **2 OCPU e 12 GB no total** |
| AMD E2.1.Micro | 2 VMs, 1/8 OCPU e 1 GB cada |
| Block volume | 200 GB no total, mínimo 50 GB por VM |
| Saída de dados | 10 TB/mês |
| IP público | 1 por VM |

Duas consequências práticas:

- A VM ARM cabe este projeto com folga. Use 1 OCPU e 6 GB se quiser dividir em duas VMs.
- A Oracle pode recuperar instância ociosa. Ela considera ociosa quando, em 7 dias, CPU (p95), rede e memória ficam abaixo de 20%. Uma pizzaria com pouco tráfego se encaixa nisso. Para produção real, migre para Pay As You Go: a cota Always Free continua, a recuperação por ociosidade não se aplica.

A região é escolhida no cadastro e não muda depois. Escolha uma perto do Brasil (São Paulo, quando houver cota).

## 1. Criar a VM

No console da Oracle:

1. Menu → Compute → Instances → **Create instance**.
2. Name: `pizzaria`.
3. Image: **Canonical Ubuntu 24.04**.
4. Shape: **Ampere** → `VM.Standard.A1.Flex` → 1 OCPU e 6 GB (ou 2 e 12).
5. Boot volume: 50 GB.
6. Networking: marque **Assign a public IPv4 address**. Aceite a VCN criada pelo assistente.
7. SSH keys: **Generate a key pair** e baixe a chave privada, ou cole sua chave pública.
8. Create.

Se aparecer `Out of host capacity`, troque o Availability Domain, tente outro horário, ou use `VM.Standard.E2.1.Micro` (AMD, 1 GB). O projeto roda em 1 GB, mas com pouca folga.

Anote o **public IP**.

## 2. Conectar por SSH

No Windows, proteja a chave e conecte:

```powershell
icacls .\ssh-key-2026-10-28.key /inheritance:r /grant:r "$($env:USERNAME):(R)"
ssh -i .\ssh-key-2026-10-28.key ubuntu@SEU_IP
```

O usuário padrão das imagens Ubuntu é `ubuntu`.

## 3. Abrir as portas (duas camadas)

A Oracle bloqueia em dois lugares. Abrir só um não funciona.

### 3.1 Security List (rede)

Console → Networking → Virtual Cloud Networks → sua VCN → Security Lists → **Default Security List** → Add Ingress Rules:

| Source CIDR | Protocol | Destination Port |
|---|---|---|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |

A porta 22 já vem liberada.

### 3.2 iptables (dentro da VM)

Imagens Ubuntu da Oracle usam `iptables-persistent`, não `ufw`.

```bash
sudo iptables -I INPUT 6 -p tcp -m multiport --dports 80,443 -m conntrack --ctstate NEW -j ACCEPT
sudo netfilter-persistent save
sudo iptables -L INPUT -n --line-numbers
```

A regra nova precisa ficar **acima** da linha `REJECT`. Se `netfilter-persistent` não existir:

```bash
sudo apt update && sudo apt install -y iptables-persistent
```

Teste de fora da VM:

```powershell
curl http://SEU_IP
```

Um `connection refused` significa regra de iptables faltando. Um timeout costuma ser Security List.

## 4. Preparar o servidor

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip git nginx sqlite3
```

## 5. Código e ambiente

```bash
cd /home/ubuntu
git clone https://github.com/kaikysousa/PizzariaDjango.git pizzaria
cd pizzaria
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
nano .env
```

Conteúdo do `.env` para produção:

```dotenv
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=COLE_A_CHAVE_GERADA_ACIMA
DJANGO_ALLOWED_HOSTS=SEU_IP,pizzaria.seudominio.com
DJANGO_DB_PATH=/home/ubuntu/pizzaria/db.sqlite3
DJANGO_SECURE_SSL_REDIRECT=0
DJANGO_HSTS_SECONDS=0
PIZZARIA_CNPJ=
PIZZARIA_TELEFONE=
PIZZARIA_ENDERECO=
PIZZARIA_HORARIO=
```

Três detalhes que quebram deploy:

- `DJANGO_SECRET_KEY` é obrigatória com `DEBUG=0`. Sem ela o app não sobe.
- `DJANGO_SECURE_SSL_REDIRECT=1` é o padrão do `settings.py` quando `DEBUG=0`. Com HTTP puro, todo acesso vira um redirecionamento para `https://` e a página não abre. Deixe `0` até o certificado existir.
- `DJANGO_HSTS_SECONDS=0` até o HTTPS estar estável. HSTS é irreversível no navegador do visitante pelo prazo configurado.
- Valores com espaço (`PIZZARIA_ENDERECO`) precisam de aspas.

## 6. Banco, estáticos e dados iniciais

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python importar_produtos.py
```

O `collectstatic` é obrigatório: em produção o WhiteNoise serve os arquivos de `staticfiles/`.

## 7. Gunicorn como serviço

Crie `/etc/systemd/system/pizzaria.service`:

```ini
[Unit]
Description=Pizzaria Django (Gunicorn)
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/pizzaria
EnvironmentFile=/home/ubuntu/pizzaria/.env
ExecStart=/home/ubuntu/pizzaria/.venv/bin/gunicorn DjangoProject.wsgi:application \
    --bind 127.0.0.1:8001 \
    --workers 2 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pizzaria
sudo systemctl status pizzaria --no-pager
curl -I http://127.0.0.1:8001
```

SQLite com vários workers pode gerar `database is locked`. Dois workers e dois threads atendem bem uma pizzaria. Se aparecer o erro, ative WAL:

```bash
sqlite3 /home/ubuntu/pizzaria/db.sqlite3 "PRAGMA journal_mode=WAL;"
```

## 8. Nginx

Crie `/etc/nginx/sites-available/pizzaria`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name SEU_IP pizzaria.seudominio.com;

    client_max_body_size 2m;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Ative e teste:

```bash
sudo ln -s /etc/nginx/sites-available/pizzaria /etc/nginx/sites-enabled/pizzaria
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Acesse `http://SEU_IP`. O cardápio deve carregar com os 35 produtos.

## 9. HTTPS

O certificado exige um domínio. Um subdomínio DuckDNS resolve e é grátis:

1. Crie `pizzaria-seunome.duckdns.org` no DuckDNS.
2. Aponte para o IP da VM.
3. Espere a propagação: `nslookup pizzaria-seunome.duckdns.org`.

Instale o certificado:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d pizzaria-seunome.duckdns.org
```

O Certbot edita o Nginx e cria a renovação automática. Teste:

```bash
sudo certbot renew --dry-run
```

Depois do HTTPS funcionando, mude no `.env`:

```dotenv
DJANGO_SECURE_SSL_REDIRECT=1
DJANGO_HSTS_SECONDS=31536000
```

E reinicie:

```bash
sudo systemctl restart pizzaria
```

Com `DEBUG=0`, o Django também marca cookies como `Secure`. Login e CSRF só funcionam por HTTPS. Por isso a ordem importa: certificado primeiro, redirect depois.

## 10. Verificação

```bash
curl -I https://pizzaria-seunome.duckdns.org
sudo journalctl -u pizzaria -n 50 --no-pager
sudo tail -f /var/log/nginx/error.log
```

Checklist:

- [ ] Home responde 200 e lista os produtos
- [ ] `/admin/` abre e o login funciona
- [ ] CSS e JS carregam (sem 404 no console do navegador)
- [ ] Adicionar ao carrinho, revisar e finalizar gera o recibo
- [ ] Recibo abre em `/pedido/<token>/recibo/`
- [ ] `python manage.py check --deploy` sem erros críticos

Avisos de HSTS e SSL no `check --deploy` são esperados antes do passo 9.

## 11. Operação

Backup diário do SQLite:

```bash
mkdir -p /home/ubuntu/backups
crontab -e
```

```cron
0 3 * * * sqlite3 /home/ubuntu/pizzaria/db.sqlite3 ".backup '/home/ubuntu/backups/db-$(date +\%F).sqlite3'" && find /home/ubuntu/backups -name 'db-*.sqlite3' -mtime +30 -delete
```

Atualizar o código:

```bash
cd /home/ubuntu/pizzaria
git pull
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart pizzaria
```

Logs e status:

```bash
sudo systemctl status pizzaria
sudo journalctl -u pizzaria -f
sudo systemctl restart nginx
```

## 12. Erros comuns

| Sintoma | Causa provável | Correção |
|---|---|---|
| Site não abre, `connection refused` | iptables da VM | regra na seção 3.2 |
| Timeout no navegador | Security List | ingress 80/443 na seção 3.1 |
| Redireciona para `https://` e falha | `DJANGO_SECURE_SSL_REDIRECT=1` sem TLS | mude para `0` |
| `DisallowedHost` | IP ou domínio fora de `ALLOWED_HOSTS` | adicione e reinicie |
| `Bad Request (400)` no login | cookies `Secure` em HTTP | use HTTPS |
| CSS quebrado, 404 | `collectstatic` não rodou | rode e reinicie |
| `database is locked` | concorrência no SQLite | WAL e menos workers |
| `Out of host capacity` | cota ARM esgotada | outro AD ou shape AMD |
| Instância desapareceu | recuperação por ociosidade | migre para Pay As You Go |

## Ordem resumida

1. VM Ubuntu 24.04, 2 OCPU / 12 GB, IP público.
2. Security List 80/443 + iptables.
3. `git clone`, venv, `pip install`, `.env`.
4. `migrate`, `collectstatic`, superusuário, importar produtos.
5. systemd com Gunicorn em `127.0.0.1:8001`.
6. Nginx na 80.
7. Domínio, Certbot, depois `SSL_REDIRECT=1` e HSTS.
8. Backup diário e `git pull` para atualizar.
