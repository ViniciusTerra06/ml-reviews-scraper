# SETUP — Documentação de Implementação

Este documento detalha **tudo que foi feito para construir este projeto**, incluindo decisões técnicas, comandos executados, problemas encontrados e como replicar o setup do zero em uma nova máquina.

Destinado a: você mesmo daqui a 6 meses, um colega que vai manter o projeto, ou outra pessoa querendo reproduzir a mesma solução para outro produto.

---

## Índice

1. [Objetivo do projeto](#objetivo-do-projeto)
2. [Requisitos](#requisitos)
3. [Arquitetura completa](#arquitetura-completa)
4. [Decisões técnicas (por quê X e não Y)](#decisões-técnicas-por-quê-x-e-não-y)
5. [Recriar o projeto do zero — passo a passo](#recriar-o-projeto-do-zero--passo-a-passo)
6. [Clonar o projeto em outra máquina](#clonar-o-projeto-em-outra-máquina)
7. [Anatomia de cada arquivo](#anatomia-de-cada-arquivo)
8. [Fluxo de execução (o que acontece a cada dia)](#fluxo-de-execução-o-que-acontece-a-cada-dia)
9. [Problemas encontrados durante o desenvolvimento](#problemas-encontrados-durante-o-desenvolvimento)
10. [Manutenção e monitoramento](#manutenção-e-monitoramento)
11. [Roadmap / melhorias futuras](#roadmap--melhorias-futuras)

---

## Objetivo do projeto

Coletar **automaticamente e diariamente** todas as avaliações públicas de produtos do Mercado Livre e disponibilizá-las como arquivos CSV para análise em ferramentas de BI (Power BI principalmente).

**Restrições:**
- Rotina deve ser **independente da máquina do usuário** (executar mesmo com PC desligado).
- CSV final deve estar disponível em uma pasta local no PC (`C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv\`) quando o PC estiver ligado.
- Custo mensal: R$ 0.
- Nenhuma manutenção diária.

---

## Requisitos

### No PC de desenvolvimento (Windows)

| Ferramenta | Versão | Verificação |
|---|---|---|
| Windows 10/11 | qualquer | — |
| Python | 3.13 ou 3.14 | `py -3 --version` |
| Git | 2.30+ | `git --version` |
| GitHub CLI (`gh`) | 2.40+ | `gh --version` |
| PowerShell | 5.1+ (nativo) | `$PSVersionTable.PSVersion` |
| Conta GitHub (com CLI logada) | — | `gh auth status` |

### Na cloud

- Repositório GitHub (privado ou público, tanto faz).
- GitHub Actions habilitado (padrão).

---

## Arquitetura completa

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMADA CLOUD (GitHub)                        │
│                                                                 │
│   Repo: ViniciusTerra06/ml-reviews-scraper (privado)            │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  src/scraper.py                                          │  │
│   │  config.json                                             │  │
│   │  requirements.txt                                        │  │
│   │  .github/workflows/daily.yml                             │  │
│   │  data/  ← CSVs commitados diariamente                    │  │
│   └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             │ trigger: cron 10:00 UTC           │
│                             ▼                                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  GitHub Actions Runner (Ubuntu VM, efêmero)              │  │
│   │  ┌────────────────────────────────────────────────────┐  │  │
│   │  │ 1. actions/checkout@v4                             │  │  │
│   │  │ 2. actions/setup-python@v5  (python 3.13)          │  │  │
│   │  │ 3. pip install -r requirements.txt                 │  │  │
│   │  │ 4. python src/scraper.py                           │  │  │
│   │  │    env OUTPUT_DIR=./data                           │  │  │
│   │  │ 5. git add data/ && git commit && git push         │  │  │
│   │  │ 6. actions/upload-artifact@v4 (backup 30d)         │  │  │
│   │  └────────────────────────────────────────────────────┘  │  │
│   └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             │ HTTP GET                          │
│                             ▼                                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  Endpoint público Mercado Livre (frontend, sem OAuth)    │  │
│   │  /noindex/catalog/reviews/{ID}/search                    │  │
│   │      ?objectId={ID}&siteId=MLB&isItem={bool}             │  │
│   │      &offset=N&limit=10                                  │  │
│   │  Retorna JSON com reviews (rating, texto, data, likes)   │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ git clone / git pull (HTTPS)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CAMADA LOCAL (PC Windows)                    │
│                                                                 │
│   C:\viniciusdev\Projects\Aula-Antonio\                         │
│   ├── Web Scraping\               ← pasta de desenvolvimento    │
│   │   ├── src/scraper.py                                        │
│   │   ├── config.json             ← editar aqui para add MLBs   │
│   │   ├── .github/workflows/                                    │
│   │   └── ... (é a origem do repo)                              │
│   │                                                             │
│   └── Scrappings - csv\           ← pasta de destino do CSV     │
│       ├── data/                                                 │
│       │   ├── reviews_MLB15238956_latest.csv  ← BI lê daqui     │
│       │   └── reviews_MLB15238956_YYYY-MM-DD.csv                │
│       ├── sync.bat                (git pull --ff-only)          │
│       └── sync.log                (histórico de sync)           │
│                                                                 │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  Windows Task Scheduler                                  │  │
│   │  ┌──────────────────────────────────────────────────┐    │  │
│   │  │ ML_Reviews_Sync_Daily                            │    │  │
│   │  │   trigger: DailyTrigger 09:00                    │    │  │
│   │  │   action:  sync.bat                              │    │  │
│   │  │                                                  │    │  │
│   │  │ ML_Reviews_Sync_Startup                          │    │  │
│   │  │   trigger: LogonTrigger (todo logon)             │    │  │
│   │  │   action:  sync.bat                              │    │  │
│   │  │   StartWhenAvailable: True                       │    │  │
│   │  └──────────────────────────────────────────────────┘    │  │
│   └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│                       Power BI / Excel                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Decisões técnicas (por quê X e não Y)

### 1. Endpoint frontend em vez de `api.mercadolibre.com/reviews/item/{id}`

**Rejeitada:** API oficial `https://api.mercadolibre.com/reviews/item/{ID}`.
- Retorna **403 Forbidden** sem autenticação OAuth.
- Setup de OAuth exige criar Application no ML, gerenciar `access_token` + `refresh_token`, e ainda expor secret no workflow.

**Escolhida:** endpoint interno do frontend `https://www.mercadolivre.com.br/noindex/catalog/reviews/{ID}/search`.
- Retorna JSON estruturado, sem autenticação.
- Mesma fonte que a página de reviews do próprio ML consome.
- Suporta paginação via `offset` + `limit`.
- Suporta produtos de catálogo (`isItem=false`) e itens de vendedor (`isItem=true`).

**Risco:** endpoint não é oficial → pode mudar sem aviso. Se quebrar, alternativa é scrapear o HTML com BeautifulSoup.

### 2. GitHub Actions em vez de Claude Cloud routine, Windows Task Scheduler puro ou Vercel Cron

| Opção | Prós | Contras | Veredicto |
|---|---|---|---|
| **Windows Task Scheduler local** | Zero-config, roda no PC | Precisa PC ligado 24/7 | ❌ falha ao requisito de independência |
| **Claude Cloud routine** | Fácil (skill `/schedule`) | Custa tokens Claude, sandbox efêmero, beta | ❌ overkill para tarefa fixa |
| **Vercel Cron** | Free tier generoso | Sandbox 60s max (ok), complica commit para GitHub | ❌ mais partes móveis |
| **GitHub Actions** | Gratuito, integrado com repo, commit direto | 2000 min/mês em repo privado | ✅ **escolhido** |

### 3. Cron 07:00 BRT (10:00 UTC)

- Antes do horário comercial → dados prontos quando o usuário chega para trabalhar.
- Fim de semana também roda (Mercado Livre nunca dorme).
- Se quiser mudar: editar `.github/workflows/daily.yml → cron`.

### 4. `git pull` local com Task Scheduler em vez de OneDrive/Dropbox

**Rejeitada:** OneDrive/Dropbox sync automático.
- Exigiria workflow escrever no OneDrive via API (OAuth).
- Latência de sync imprevisível.
- Cliente do OneDrive nem sempre está rodando.

**Escolhida:** `git pull --ff-only` chamado por Task Scheduler.
- Determinístico: `git pull` sempre traz a versão mais nova.
- Zero credenciais além do já configurado (git no PC).
- Rápido (~1s se já up-to-date).
- Histórico completo disponível localmente via `git log`.

### 5. Dois triggers no Task Scheduler (Daily + Startup)

- **Daily 09:00:** cobre o caso PC ligado 24/7 (ou ligado antes de 09:00).
- **Startup (LogonTrigger):** cobre o caso PC ficou desligado dias — ao logar, sincroniza.

Sem o Startup, quem desliga PC toda noite perderia dias.

### 6. `Register-ScheduledTask` (PowerShell) em vez de `schtasks` para o trigger LogonTrigger

- `schtasks /SC ONLOGON` exige elevação (Admin). Falhava com "Acesso negado".
- `Register-ScheduledTask` com `LogonType Interactive` e `RunLevel Limited` cria a task para o usuário atual sem exigir Admin.
- `schtasks /SC DAILY /RL LIMITED` funciona sem Admin — usado para a task Daily.

### 7. `page_size=10` e `request_delay_seconds=1.5`

Descoberto empiricamente. Configurações maiores dispararam rate limit do ML (HTTP 400 disfarçado). Com esses valores, coleta 310 reviews em ~60s sem falhas.

### 8. Snapshot diário + `_latest.csv` sobrescrito

- **Snapshot diário** (`reviews_MLB..._2026-07-21.csv`) preserva histórico. Útil para detectar reviews removidas ou notas alteradas.
- **`_latest.csv`** é uma cópia sempre atualizada. O BI aponta para este arquivo — assim não precisa reconfigurar a fonte de dados a cada dia.

### 9. Encoding `utf-8-sig`

Excel PT-BR abre CSV UTF-8 sem BOM como se fosse cp1252 (bagunça acentos e emojis). BOM `\xEF\xBB\xBF` no início força Excel a interpretar corretamente.

---

## Recriar o projeto do zero — passo a passo

Cenário: você (ou outra pessoa) quer construir este projeto do início, para um produto diferente ou em outro ambiente.

### Pré-requisitos

Instalar:
- Python 3.13+: https://www.python.org/downloads/ (marcar "Add to PATH")
- Git for Windows: https://git-scm.com/download/win
- GitHub CLI: https://cli.github.com

Autenticar `gh`:
```powershell
gh auth login
# Escolher: GitHub.com → HTTPS → login via browser
```

### Passo 1 — Criar estrutura de pastas

```powershell
New-Item -ItemType Directory -Path "C:\seu-caminho\Web Scraping" -Force
Set-Location "C:\seu-caminho\Web Scraping"
New-Item -ItemType Directory -Path "src", "data", "logs", ".github\workflows" -Force
```

### Passo 2 — Criar `requirements.txt`

Conteúdo:
```
requests>=2.31
pandas>=2.2
python-dateutil>=2.9
```

### Passo 3 — Instalar dependências localmente

```powershell
py -3 -m pip install -r requirements.txt
```

### Passo 4 — Criar `config.json`

```json
{
  "product_ids": ["MLB_SEU_ID_AQUI"],
  "output_dir": "C:\\seu-caminho\\Scrappings - csv",
  "api_base": "https://api.mercadolibre.com",
  "page_size": 10,
  "request_delay_seconds": 1.5,
  "max_retries": 5,
  "timeout_seconds": 20
}
```

### Passo 5 — Criar `src/scraper.py`

Copiar o conteúdo de `src/scraper.py` deste projeto. Explicação detalhada em [Anatomia de cada arquivo](#anatomia-de-cada-arquivo).

### Passo 6 — Testar local

```powershell
py -3 -X utf8 src\scraper.py
```

Esperado: log mostra "offset=0 got=10", CSVs aparecem em `data/`.

### Passo 7 — Criar `.gitignore`

```
__pycache__/
*.pyc
.venv/
logs/
*.log
.DS_Store
.vscode/
.idea/
.claude/
/Scrappings - csv/
```

### Passo 8 — Init git + criar repo GitHub

```powershell
git init -b main
gh repo create SEU_USER/ml-reviews-scraper --private --source=. --remote=origin
```

Se o repo já existe, apenas:
```powershell
git init -b main
git remote add origin https://github.com/SEU_USER/ml-reviews-scraper.git
```

### Passo 9 — Criar `.github/workflows/daily.yml`

Copiar o arquivo deste projeto. Ajustar:
- `cron`: horário desejado (em UTC).
- `python-version`: se quiser outra versão.

### Passo 10 — Criar `README.md` e `SETUP.md`

Este arquivo e o `README.md` — copiar do projeto ou adaptar.

### Passo 11 — Primeiro commit e push

```powershell
git add .
git commit -m "Initial ML reviews scraper with daily GitHub Actions cron"
git push -u origin main
```

### Passo 12 — Testar o workflow manualmente

```powershell
gh workflow run "Daily ML Reviews Scrape" --ref main
Start-Sleep 30
gh run list --workflow=daily.yml --limit 3
```

Se `completed success`, a cloud está funcional. `git pull` para trazer o CSV commitado pelo workflow.

### Passo 13 — Criar pasta destino e clonar

```powershell
New-Item -ItemType Directory -Path "C:\seu-caminho\Scrappings - csv" -Force
git clone https://github.com/SEU_USER/ml-reviews-scraper.git "C:\seu-caminho\Scrappings - csv"
```

### Passo 14 — Criar `sync.bat` na pasta destino

Conteúdo:
```bat
@echo off
cd /d "C:\seu-caminho\Scrappings - csv"
git pull --ff-only >> sync.log 2>&1
echo [%DATE% %TIME%] pull exit=%ERRORLEVEL% >> sync.log
exit /b %ERRORLEVEL%
```

### Passo 15 — Registrar Windows Scheduled Tasks

Daily (sem Admin, via `schtasks`):
```powershell
schtasks /Create /SC DAILY `
  /TN "ML_Reviews_Sync_Daily" `
  /TR "`"C:\seu-caminho\Scrappings - csv\sync.bat`"" `
  /ST 09:00 /RL LIMITED /F
```

Startup on-logon (sem Admin, via `Register-ScheduledTask`):
```powershell
$action = New-ScheduledTaskAction -Execute "cmd.exe" `
  -Argument "/c `"C:\seu-caminho\Scrappings - csv\sync.bat`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
  -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "ML_Reviews_Sync_Startup" `
  -Action $action -Trigger $trigger -Settings $settings `
  -Principal $principal -Force
```

### Passo 16 — Validar tudo

```powershell
# Cloud
gh run list --workflow=daily.yml --limit 3

# Tasks locais
Get-ScheduledTask -TaskName "ML_Reviews_Sync_*" | Format-Table

# Sync manual
Start-ScheduledTask -TaskName "ML_Reviews_Sync_Startup"
Get-Content "C:\seu-caminho\Scrappings - csv\sync.log" -Tail 5

# CSV existe?
Get-Item "C:\seu-caminho\Scrappings - csv\data\reviews_*_latest.csv"
```

**Pronto.** Setup completo.

---

## Clonar o projeto em outra máquina

Cenário: você já tem o repo, quer configurar em um segundo PC.

### Passo 1 — Instalar Python, Git, gh (como acima)

### Passo 2 — Clonar o repo

```powershell
git clone https://github.com/ViniciusTerra06/ml-reviews-scraper.git "C:\NovaPasta\Scrappings - csv"
```

### Passo 3 — Criar `sync.bat` na pasta

Mesmo conteúdo do [Passo 14](#passo-14--criar-syncbat-na-pasta-destino), apenas ajustar o caminho.

### Passo 4 — Registrar Scheduled Tasks

Mesmo procedimento do [Passo 15](#passo-15--registrar-windows-scheduled-tasks).

Nomes das tasks devem ser únicos por máquina. Se rodar em dois PCs simultâneos, cada um roda seu próprio `git pull` — não há conflito porque apenas leem do GitHub.

### Passo 5 — (Opcional) Instalar dev environment

Se este segundo PC também vai desenvolver:
```powershell
git clone https://github.com/ViniciusTerra06/ml-reviews-scraper.git "C:\dev\Web Scraping"
cd "C:\dev\Web Scraping"
py -3 -m pip install -r requirements.txt
```

---

## Anatomia de cada arquivo

### `src/scraper.py`

Estrutura:

| Função | Responsabilidade |
|---|---|
| `setup_logging()` | Configura logger para console + arquivo `logs/scraper.log` |
| `load_config()` | Lê `config.json`, aplica overrides `OUTPUT_DIR` e `PRODUCT_IDS` das env vars |
| `normalize_product_id(raw)` | Aceita URL ou ID cru, extrai `MLB\d+` via regex |
| `build_session(max_retries)` | Cria `requests.Session` com retry exponencial em 429/5xx |
| `warm_up_session(...)` | Visita a página do produto antes do JSON — recebe cookies que evitam 400 imediato |
| `fetch_reviews_page(...)` | 1 chamada HTTP → lista de reviews. Trata 400 como fim de stream |
| `paginate_reviews(...)` | Loop de páginas, para em página vazia ou 2 duplicadas consecutivas |
| `flatten(review, ...)` | Transforma o JSON aninhado em dict plano (uma linha do CSV) |
| `write_csvs(df, product_id, output_dir)` | Salva `_YYYY-MM-DD.csv` + `_latest.csv` com encoding `utf-8-sig` |
| `scrape_product(session, product_id, cfg)` | Orquestra warm-up → catalog mode → fallback item mode → write |
| `main()` | Ponto de entrada, loop pelos produtos, agrega estatísticas, retorna exit code |

**Estratégia de detecção de fim de stream:**

O endpoint `/noindex/catalog/reviews/{ID}/search` **não retorna metadados de paginação** (`total`, `has_more`). Fim de stream é detectado por:

1. Página vazia (`reviews: []`) → fim natural.
2. HTTP 400 → fim (endpoint retorna 400 quando `offset > total`).
3. Duas páginas consecutivas com todos os IDs já vistos → segurança contra loops.

### `config.json`

Chaves:

| Chave | Tipo | Descrição |
|---|---|---|
| `product_ids` | list[str] | IDs ou URLs de produtos. Aceita ambos, extrai MLB via regex |
| `output_dir` | str | Pasta destino (Windows path). Overrideável via env `OUTPUT_DIR` |
| `page_size` | int | Reviews por chamada. 10 é seguro; 50 disparou rate limit |
| `request_delay_seconds` | float | Delay entre chamadas. 1.5s empírico |
| `max_retries` | int | Tentativas em 429/5xx antes de desistir da página |
| `timeout_seconds` | int | Timeout HTTP por request |

### `.github/workflows/daily.yml`

- `on.schedule.cron: "0 10 * * *"` — 10 UTC = 07 BRT.
- `on.workflow_dispatch: {}` — habilita botão "Run workflow" no GitHub UI e `gh workflow run`.
- `permissions.contents: write` — necessário para o step de commit + push.
- `concurrency` — impede runs simultâneos (evita conflito de push).
- `env.OUTPUT_DIR: ./data` — sobrescreve o caminho Windows do config; a VM Ubuntu não tem `C:\`.
- Passo 5 (commit): usa `git diff --cached --quiet` para evitar commit vazio quando reviews não mudaram.
- Passo 6 (artifact): backup redundante. Baixável do run page por 30 dias mesmo se o repo for corrompido.

### `sync.bat` (na pasta destino)

Uma única linha útil: `git pull --ff-only`.
- `--ff-only`: recusa merge se houver divergência. Como só o Actions escreve no repo, nunca deveria haver conflito.
- `>> sync.log 2>&1`: append de stdout + stderr.
- `echo [%DATE% %TIME%] pull exit=%ERRORLEVEL%`: linha de resumo com timestamp.

### Windows Scheduled Tasks

`ML_Reviews_Sync_Daily`:
- Trigger: `MSFT_TaskDailyTrigger`, 09:00.
- Ação: executa `sync.bat`.
- RunLevel: Limited (usuário atual, sem elevação).

`ML_Reviews_Sync_Startup`:
- Trigger: `MSFT_TaskLogonTrigger`, LogonType Interactive.
- Ação: executa `sync.bat`.
- Settings: `StartWhenAvailable=True` (roda mesmo se agendamento anterior perdeu janela).

---

## Fluxo de execução (o que acontece a cada dia)

### 10:00:00 UTC (07:00 BRT)

GitHub aciona o cron. Fila de jobs GitHub Actions.

### 10:00:XX UTC — Runner sobe

VM Ubuntu 22.04 é provisionada. Cerca de 5–10 segundos.

### Steps do workflow (em ordem):

1. **Checkout** (~2s): clona o repo.
2. **Setup Python 3.13** (~10s primeira vez, ~2s com cache).
3. **Install deps** (~15s primeira vez, ~3s com cache).
4. **Run scraper** (~60s):
   - `load_config()` lê `config.json`, aplica `OUTPUT_DIR=./data`.
   - Para cada produto:
     - `warm_up_session` visita a página de reviews (ganha cookies).
     - `paginate_reviews` loop:
       - GET `?offset=0&limit=10` → 10 reviews.
       - `time.sleep(1.5)`.
       - GET `?offset=10&limit=10` → 10 reviews.
       - ... até HTTP 400 ou página vazia.
     - `flatten` para cada review.
     - `write_csvs` salva 2 CSVs em `./data/`.
5. **Commit** (~5s):
   - `git add data/`.
   - Se `git diff --cached --quiet` (sem mudanças): pula.
   - Senão: `git commit + push`.
6. **Upload artifact** (~3s): compacta `data/*.csv` como zip.

**Total: ~90 segundos.**

### 10:01:30 UTC (~07:01:30 BRT) — CSV atualizado no repo

Novo commit visível em https://github.com/ViniciusTerra06/ml-reviews-scraper/commits/main

### 12:00:00 BRT — Task Scheduler local (se PC ligado)

`ML_Reviews_Sync_Daily` dispara. `git pull` traz o commit das 08:01. CSVs atualizados na pasta local.

### Ao ligar PC (se estava desligado)

`ML_Reviews_Sync_Startup` dispara no logon. `git pull` traz todos os commits acumulados desde o último logon.

---

## Problemas encontrados durante o desenvolvimento

Registro histórico para não repetir os mesmos erros.

### 1. API oficial ML retorna 403

Tentativa inicial: `https://api.mercadolibre.com/reviews/item/{ID}`.
Resposta: `HTTP 403 Forbidden`. Requer OAuth.

**Solução:** trocar para endpoint frontend `noindex/catalog/reviews/{ID}/search`.

### 2. Rate limit disfarçado de HTTP 400

Após ~30 requests rápidos, endpoint começa a retornar HTTP 400 (não 429).

**Solução:**
- `page_size=10` (não 50).
- `request_delay_seconds=1.5`.
- Retry com backoff exponencial apenas em 429/5xx (400 é tratado como fim de stream).
- Cooldown de 45–60s entre execuções durante testes.

### 3. Windows console cp1252 não renderiza emojis nas reviews

Reviews com emojis (🎁😍👍🏻) causavam `UnicodeEncodeError` ao imprimir com Python padrão.

**Solução:** `py -3 -X utf8 src\scraper.py`. No workflow: `env PYTHONIOENCODING: utf-8`.

### 4. Excel PT-BR bagunça UTF-8 sem BOM

CSVs abertos no Excel mostravam `Ã©` em vez de `é`.

**Solução:** encoding `utf-8-sig` no `df.to_csv()`.

### 5. `schtasks /SC ONLOGON` exige elevação

Falhava com "ERRO: Acesso negado" mesmo com `/RL LIMITED`.

**Solução:** usar `Register-ScheduledTask` (cmdlet PowerShell), que aceita `LogonType Interactive` + `RunLevel Limited` sem prompt de UAC.

### 6. `git clone . URL` falhava em pasta não-vazia

Pasta destino já tinha 2 CSVs de teste manual.

**Solução:** `rm *.csv` antes do `git clone`. Alternativa: `git init` + `git remote add` + `git pull`.

### 7. Bash do Git mangla flags do schtasks

`git-bash` interpretava `/SC` como caminho e traduzia para `C:\Program Files\Git\SC`. Comando executado ficava inválido.

**Solução:** usar PowerShell (`schtasks` executado nativo do Windows). Regra geral do projeto: registrar tasks via PowerShell, não Bash.

---

## Manutenção e monitoramento

### Verificação semanal (2 min)

```powershell
# Últimos 7 runs cloud — checar se todos foram success
gh run list --workflow=daily.yml --limit 7

# Últimos syncs locais
Get-Content "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv\sync.log" -Tail 10

# Total de reviews no CSV mais recente
$latest = "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv\data\reviews_MLB15238956_latest.csv"
(Import-Csv $latest).Count
```

### Rebuild se algo quebrou

Seguir seção [Recriar o projeto do zero](#recriar-o-projeto-do-zero--passo-a-passo).

### Adicionar alertas de falha

Não implementado. Sugestão: adicionar step ao workflow que envia notificação em falha.

Exemplo (Discord webhook):
```yaml
- name: Notify on failure
  if: failure()
  run: |
    curl -X POST -H "Content-Type: application/json" \
      -d '{"content":"❌ ML scraper failed. Run: ${{ github.run_id }}"}' \
      ${{ secrets.DISCORD_WEBHOOK_URL }}
```

Configurar secret em Settings → Secrets and variables → Actions.

### Migrar para outra máquina

Ver [Clonar o projeto em outra máquina](#clonar-o-projeto-em-outra-máquina).

### Remover o projeto completamente

```powershell
# Remover tasks
schtasks /Delete /TN "ML_Reviews_Sync_Daily" /F
schtasks /Delete /TN "ML_Reviews_Sync_Startup" /F

# Remover pastas
Remove-Item -Recurse -Force "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv"
Remove-Item -Recurse -Force "C:\viniciusdev\Projects\Aula-Antonio\Web Scraping"

# Deletar repo GitHub (irreversível)
gh repo delete ViniciusTerra06/ml-reviews-scraper --yes
```

---

## Roadmap / melhorias futuras

Ordenadas por relação custo/valor.

### Alta prioridade

- **Notificação de falha por Discord/Slack/email** (10 min de setup).
- **Habilitar `StartWhenAvailable=True` na Daily task** (fecha o único gap de sincronização).

### Média prioridade

- **Consolidação multi-produto:** step adicional no workflow que gera `reviews_all_latest.csv` com todos os produtos concatenados.
- **Notebook Jupyter de exploração** em `notebooks/eda.ipynb` para análise ad hoc.
- **Dashboard Streamlit** hospedado em Vercel/Fly.io para visualização sem depender do BI.

### Baixa prioridade

- **Análise de sentimento com LLM** (Claude/OpenAI): coluna `sentiment` + `themes` derivada de `content`. Rodar como job separado após o scraper.
- **Suporte multi-país:** parametrizar `siteId` (`MLA` Argentina, `MLM` México, etc.).
- **Detecção de reviews editadas/deletadas:** diff automático entre snapshots consecutivos, gerando relatório.
- **Cache de imagens:** baixar `picture_urls` para armazenamento local (Vercel Blob ou repo git-lfs).

### Provavelmente não vale a pena

- Migrar de GitHub Actions para servidor próprio (mais moving parts, mesmo custo).
- Migrar de CSV para banco de dados relacional (o BI já processa CSVs sem esforço).
- Playwright headless em vez do endpoint JSON (mais lento, mais frágil).

---

## Referências e links úteis

- Repositório: https://github.com/ViniciusTerra06/ml-reviews-scraper
- Guia de uso: [`README.md`](./README.md)
- Cron helper: https://crontab.guru
- GitHub Actions docs: https://docs.github.com/actions
- Task Scheduler PowerShell: https://learn.microsoft.com/powershell/module/scheduledtasks
- Endpoint ML testado: https://www.mercadolivre.com.br/noindex/catalog/reviews/MLB15238956/search?objectId=MLB15238956&siteId=MLB&isItem=false&offset=0&limit=10
- Códigos de erro Task Scheduler: https://learn.microsoft.com/windows/win32/taskschd/task-scheduler-error-codes

---

_Última atualização deste documento: 2026-07-20._
