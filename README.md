# ML Reviews Scraper — Guia de Uso

Scraper diário de avaliações do Mercado Livre. Extrai **todas as reviews** de qualquer produto (catálogo ou item de vendedor), gera CSVs prontos para BI (Power BI, Excel, Metabase, Looker Studio).

Roda **automaticamente na cloud** (GitHub Actions), com CSV sincronizado para pasta local via `git pull` agendado.

---

## Índice

1. [O que este projeto faz](#o-que-este-projeto-faz)
2. [Arquitetura em 30 segundos](#arquitetura-em-30-segundos)
3. [Como obter o CSV](#como-obter-o-csv)
4. [Adicionar um novo produto](#adicionar-um-novo-produto)
5. [Rodar local (opcional, teste rápido)](#rodar-local-opcional-teste-rápido)
6. [Estrutura do CSV](#estrutura-do-csv)
7. [Conectar Power BI / Excel](#conectar-power-bi--excel)
8. [Personalizações comuns](#personalizações-comuns)
9. [Importar o projeto em outra máquina](#importar-o-projeto-em-outra-máquina)
10. [Troubleshooting](#troubleshooting)
11. [Limitações](#limitações)

---

## O que este projeto faz

- Recebe uma lista de **produtos do Mercado Livre** (por ID `MLBxxxxxxxxx` ou URL completa).
- **Todo dia 07:00 (horário de Brasília)** consulta o endpoint público de reviews do ML e coleta **todas as avaliações** de cada produto.
- Salva um snapshot diário do dia + um arquivo `_latest.csv` sempre atualizado (fonte estável para o BI apontar).
- Commita os CSVs num repositório privado (`ViniciusTerra06/ml-reviews-scraper`) — histórico completo versionado.
- Sincroniza automaticamente para a pasta local `C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv\data\`.

---

## Arquitetura em 30 segundos

```
GitHub Actions (cloud, 07:00 BRT)
        │
        ▼
   scraper.py → data/reviews_MLB*.csv (commit + push)
        │
        ▼
Repositório GitHub (histórico versionado)
        │
        ▼  git pull (auto: no logon + diário 09:00)
        │
C:\...\Scrappings - csv\data\reviews_MLB*_latest.csv
        │
        ▼
     Power BI / Excel / Metabase
```

**Independente do seu PC:** o scrape roda no GitHub mesmo com sua máquina desligada. Quando você ligar, o `git pull` puxa os CSVs acumulados.

---

## Como obter o CSV

**Local (pasta do seu PC):**

```
C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv\data\reviews_MLB15238956_latest.csv
```

Este arquivo é atualizado automaticamente. Não precisa fazer nada manual.

**Direto da nuvem (raw URL — para BI que aceita URL):**

```
https://raw.githubusercontent.com/ViniciusTerra06/ml-reviews-scraper/main/data/reviews_MLB15238956_latest.csv
```

> ⚠️ Repositório é **privado**. Para BI acessar a raw URL, precisa de um Personal Access Token (PAT) do GitHub configurado no header `Authorization: Bearer TOKEN`.

**Histórico (snapshots diários):**

```
C:\...\Scrappings - csv\data\reviews_MLB15238956_2026-07-21.csv
C:\...\Scrappings - csv\data\reviews_MLB15238956_2026-07-22.csv
...
```

---

## Adicionar um novo produto

### Passo 1 — Encontrar o MLB ID

O ID do produto está na URL do Mercado Livre. Formato: `MLB` seguido de dígitos.

**Exemplos:**

| URL do produto | ID extraído |
|---|---|
| `https://www.mercadolivre.com.br/chapinha-.../p/MLB15238956` | `MLB15238956` (catálogo) |
| `https://produto.mercadolivre.com.br/MLB-4258928805-...` | `MLB4258928805` (item de vendedor) |
| `...?item_id=MLB4258928805#reviews` | `MLB4258928805` (item embutido no query) |

O scraper aceita **URL completa** ou **só o ID** — ele extrai o `MLBxxxx` automaticamente via regex.

### Passo 2 — Editar `config.json`

Abra `C:\viniciusdev\Projects\Aula-Antonio\Web Scraping\config.json` e adicione o novo ID à lista:

```json
{
  "product_ids": [
    "MLB15238956",
    "MLB1234567890",
    "https://www.mercadolivre.com.br/qualquer-coisa/p/MLB9876543210"
  ],
  "output_dir": "C:\\viniciusdev\\Projects\\Aula-Antonio\\Scrappings - csv",
  "page_size": 10,
  "request_delay_seconds": 1.5,
  "max_retries": 5,
  "timeout_seconds": 20
}
```

Pode misturar IDs e URLs — tanto faz.

### Passo 3 — Commitar e fazer push

```powershell
cd "C:\viniciusdev\Projects\Aula-Antonio\Web Scraping"
git add config.json
git commit -m "config: adiciona produto MLB1234567890"
git push
```

**Pronto.** Na próxima execução diária (07:00 BRT), o scraper coletará todos os produtos da lista. Cada produto gera seus próprios CSVs (`reviews_{MLB_ID}_*.csv`).

Se quiser resultado imediato sem esperar 07:00, dispare o workflow manualmente:

```powershell
gh workflow run "Daily ML Reviews Scrape" --ref main
```

---

## Rodar local (opcional, teste rápido)

Útil pra validar um produto novo antes de commitar, ou pra rodar sob demanda.

### Setup único

```powershell
cd "C:\viniciusdev\Projects\Aula-Antonio\Web Scraping"
py -3 -m pip install -r requirements.txt
```

### Executar

```powershell
py -3 -X utf8 src\scraper.py
```

Saída: CSVs em `C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv\` (definido em `config.json → output_dir`).

Logs em `logs\scraper.log`.

### Rodar só um produto específico (sem editar config)

```powershell
$env:PRODUCT_IDS = "MLB1234567890"
py -3 -X utf8 src\scraper.py
```

### Salvar em outra pasta temporariamente

```powershell
$env:OUTPUT_DIR = "D:\Temp\ML"
py -3 -X utf8 src\scraper.py
```

---

## Estrutura do CSV

Encoding: **UTF-8 com BOM** (compatível com Excel português).

| Coluna | Tipo | Descrição |
|---|---|---|
| `review_id` | int | ID único da review no ML |
| `product_id` | string | MLB ID do produto |
| `product_type` | string | `catalog` (catálogo) ou `item` (listagem específica) |
| `rating` | int 1–5 | Nota dada pelo comprador |
| `content` | string | Texto da avaliação (pode ser vazio se comprador só deu nota) |
| `date_relative` | string | Data em português relativo ("Há 2 meses") |
| `date_created` | ISO datetime | Data absoluta (ex.: `2024-02-25T16:37:33Z`) |
| `likes` | int | Quantidade de "útil" recebida |
| `has_comment` | bool | `True` se a review tem texto |
| `picture_count` | int | Quantidade de fotos anexadas |
| `video_count` | int | Quantidade de vídeos anexados |
| `position_in_list` | int | Posição em que apareceu na listagem original |
| `site_id` | string | Sempre `MLB` (Brasil) |
| `picture_urls` | string | URLs das fotos separadas por ` \| ` |
| `collected_at` | ISO datetime | Timestamp da coleta (UTC) |

---

## Conectar Power BI / Excel

### Power BI (arquivo local)

1. **Obter Dados** → **Texto/CSV**
2. Selecionar: `C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv\data\reviews_MLB15238956_latest.csv`
3. Encoding: `65001: Unicode (UTF-8)`
4. **Carregar**
5. Configurar atualização automática: diária, depois das 09:15 (após o `git pull` local).

### Power BI (raw URL do GitHub)

Repo privado exige token. Use conector Web:

1. **Obter Dados** → **Web** → **Avançado**
2. URL: `https://raw.githubusercontent.com/ViniciusTerra06/ml-reviews-scraper/main/data/reviews_MLB15238956_latest.csv`
3. Cabeçalho HTTP:
   - `Authorization` : `Bearer ghp_SEU_PAT_AQUI`
4. Encoding: UTF-8.

### Excel

- **Dados** → **De Texto/CSV** → apontar para o arquivo `_latest.csv`.
- **Atualizar tudo** para pegar a versão mais nova (roda `git pull` implícito se pasta aberta).

### Metabase / Looker Studio / outros

Aceitam CSV direto. Aponte para o caminho local ou raw URL (com auth).

---

## Personalizações comuns

### Mudar horário do scrape na cloud

Editar `.github/workflows/daily.yml`:

```yaml
on:
  schedule:
    - cron: "0 10 * * *"   # 10 UTC = 07 BRT
```

Referência: [crontab.guru](https://crontab.guru/). Lembrar: cron do GitHub Actions usa **UTC**. BRT = UTC−3.

**Exemplos:**

| Horário desejado (BRT) | Cron UTC |
|---|---|
| 06:00 | `0 9 * * *` |
| 07:00 | `0 10 * * *` |
| 08:00 | `0 11 * * *` |
| 12:00 | `0 15 * * *` |
| 18:00 | `0 21 * * *` |
| 23:00 | `0 2 * * *` |

Depois `git commit + push` — GitHub aplica na próxima janela.

### Mudar horário do `git pull` local

```powershell
schtasks /Change /TN "ML_Reviews_Sync_Daily" /ST 10:30
```

### Mudar pasta destino local

1. Mover a pasta atual: `Move-Item "C:\...\Scrappings - csv" "D:\NovaPasta"`
2. Editar `config.json → output_dir` para o novo caminho (apenas afeta runs locais; a cloud usa `env OUTPUT_DIR=./data`).
3. Editar `sync.bat` na nova pasta se necessário.
4. Recriar as scheduled tasks com o novo caminho.

### Coletar múltiplos produtos

Basta adicionar mais IDs ao array `product_ids`. Sem limite prático até ~50 produtos (limitação real = rate limit do ML, não do scraper).

Cada produto = CSV separado. Se quiser um único CSV consolidado, faça `UNION` no BI.

---

## Importar o projeto em outra máquina

Cenário: você tem uma segunda máquina Windows (colega, notebook novo, outro escritório) e quer que ela receba o CSV atualizado automaticamente, sem precisar reconstruir o projeto do zero.

O scraper roda **na cloud (GitHub Actions)** — a máquina nova não executa o scraper, apenas sincroniza os CSVs já gerados. Setup total: ~10 minutos.

### Passo 1 — Instalar pré-requisitos

| Ferramenta | Link | Verificação |
|---|---|---|
| Git for Windows | https://git-scm.com/download/win | `git --version` |
| GitHub CLI | https://cli.github.com | `gh --version` |
| Python 3.13+ *(opcional, só se for rodar scraper local)* | https://www.python.org/downloads/ | `py -3 --version` |

Durante a instalação do Python, marcar **"Add Python to PATH"**.

### Passo 2 — Autenticar no GitHub

O repositório é privado, então o clone exige credenciais.

```powershell
gh auth login
# Selecionar: GitHub.com → HTTPS → Login with a web browser
gh auth setup-git
```

Confirmar:
```powershell
gh auth status
```

Esperado: `Logged in to github.com as SEU_USER`.

### Passo 3 — Clonar o repositório

Escolher uma pasta destino. O padrão do projeto é `C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv`, mas pode ser qualquer caminho.

```powershell
$dest = "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv"
New-Item -ItemType Directory -Path (Split-Path $dest) -Force | Out-Null
git clone https://github.com/ViniciusTerra06/ml-reviews-scraper.git $dest
```

Se você usou outro caminho, substitua `$dest` em todos os passos seguintes.

### Passo 4 — Criar `sync.bat` na pasta destino

O `sync.bat` é o script que puxa os CSVs mais recentes do GitHub. Rodá-lo manualmente ou via Task Scheduler tem o mesmo efeito.

```powershell
$dest = "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv"
@"
@echo off
cd /d "$dest"
git pull --ff-only >> sync.log 2>&1
echo [%DATE% %TIME%] pull exit=%ERRORLEVEL% >> sync.log
exit /b %ERRORLEVEL%
"@ | Out-File -Encoding ascii "$dest\sync.bat"
```

Testar manualmente:
```powershell
& "$dest\sync.bat"
Get-Content "$dest\sync.log" -Tail 3
```

Esperado: linha `pull exit=0` no log.

### Passo 5 — Registrar Windows Scheduled Tasks

Dois gatilhos garantem que o CSV sempre esteja atualizado:

- **Daily 09:00** — cobre o caso PC ligado durante o horário comercial.
- **On-logon** — cobre o caso PC ficou dias desligado; sincroniza no próximo login.

Ambas rodam sem exigir privilégios de Administrador.

```powershell
$dest = "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv"

# Task diária
schtasks /Create /SC DAILY `
  /TN "ML_Reviews_Sync_Daily" `
  /TR "`"$dest\sync.bat`"" `
  /ST 09:00 /RL LIMITED /F

# Task on-logon
$action    = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$dest\sync.bat`""
$trigger   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "ML_Reviews_Sync_Startup" `
  -Action $action -Trigger $trigger -Settings $settings `
  -Principal $principal -Force
```

### Passo 6 — Validar a instalação

```powershell
$dest = "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv"

# Tasks foram criadas
Get-ScheduledTask -TaskName "ML_Reviews_Sync_*" | Format-Table TaskName, State

# Disparar sync agora (simula logon)
Start-ScheduledTask -TaskName "ML_Reviews_Sync_Startup"
Start-Sleep 3
Get-Content "$dest\sync.log" -Tail 5

# CSV existe e tem conteúdo
Get-ChildItem "$dest\data\reviews_*_latest.csv" | Select-Object Name, Length, LastWriteTime
```

Esperado:
- Duas tasks com `State = Ready`.
- Log com `pull exit=0`.
- Pelo menos um arquivo `reviews_MLBxxxxx_latest.csv` com tamanho > 0.

### Passo 7 — Conectar Power BI / Excel

Seguir a seção [Conectar Power BI / Excel](#conectar-power-bi--excel), apontando para o novo caminho local.

### Passo 8 — (Opcional) Preparar ambiente de desenvolvimento

Só é necessário se esta máquina também for editar o scraper ou testá-lo localmente. Para uso apenas de consumo do CSV, **pular este passo**.

```powershell
git clone https://github.com/ViniciusTerra06/ml-reviews-scraper.git "C:\dev\Web Scraping"
cd "C:\dev\Web Scraping"
py -3 -m pip install -r requirements.txt
py -3 -X utf8 src\scraper.py
```

### Notas importantes

- **Nomes das tasks devem ser únicos por máquina.** Se dois PCs rodarem o mesmo `sync.bat`, cada um puxa independentemente do GitHub — não há conflito, pois ambos apenas leem.
- **Não é necessário fork nem push writes na nova máquina.** Apenas o GitHub Actions escreve no repositório.
- **Se o repositório for tornado público**, o passo `gh auth login` pode ser pulado — `git clone` funciona anônimo.
- **Remover tudo depois:** ver seção [Remover o projeto completamente](./SETUP.md#remover-o-projeto-completamente) no `SETUP.md`.

---

## Troubleshooting

### CSV não atualiza no meu PC

**Verificar cadeia:**

```powershell
# 1. GitHub Actions rodou?
gh run list --workflow=daily.yml --limit 5

# 2. Repo tem commit recente?
cd "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv"
git log --oneline -5

# 3. Task de sync executou?
Get-ScheduledTaskInfo -TaskName "ML_Reviews_Sync_Daily"
Get-ScheduledTaskInfo -TaskName "ML_Reviews_Sync_Startup"

# 4. Log de sync
Get-Content "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv\sync.log" -Tail 20
```

**Forçar sync agora:**

```powershell
cd "C:\viniciusdev\Projects\Aula-Antonio\Scrappings - csv"
.\sync.bat
```

### Workflow do GitHub falhou

Ver logs:

```powershell
gh run list --workflow=daily.yml --limit 5
gh run view <run_id> --log
```

Causas comuns:
- **ML bloqueou o IP do runner** (raro, rotativos). Rodar de novo manualmente com `gh workflow run "Daily ML Reviews Scrape"`.
- **Produto sem reviews** — CSV fica vazio, workflow ainda passa.
- **Config JSON quebrado** — sintaxe inválida. Validar em [jsonlint.com](https://jsonlint.com).

### Rate limit do ML

Sintomas: HTTP 400 no meio da paginação, logs mostram "HTTP 400 at offset=N".

Ajustes em `config.json`:

```json
{
  "page_size": 5,               // reduzir (padrão: 10)
  "request_delay_seconds": 3.0, // aumentar (padrão: 1.5)
  "max_retries": 7
}
```

### Produto retorna 0 reviews

- Produto pode não ter avaliações públicas.
- ID pode estar errado (não é `MLB`+dígitos válido).
- Testar manualmente:
  ```
  https://www.mercadolivre.com.br/noindex/catalog/reviews/MLB15238956/search?objectId=MLB15238956&siteId=MLB&isItem=false&offset=0&limit=1
  ```
- Se der 200 e retornar reviews no browser, mas o scraper não pega: possível rate limit — aguardar 10 min.

### Task Scheduler não executa

```powershell
# Estado das tasks
Get-ScheduledTask -TaskName "ML_Reviews_Sync_*"

# Última execução + código de erro
Get-ScheduledTaskInfo -TaskName "ML_Reviews_Sync_Daily"
```

`LastTaskResult`:
- `0` = sucesso
- `267009` = task ainda rodando
- `2147943645` = task disabled
- outros: [Google + código](https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-error-codes)

### Rebuild a partir do zero

Se algo quebrou irremediavelmente, consulte [`SETUP.md`](./SETUP.md) — recria tudo do zero em ~15 minutos.

---

## Limitações

- **Só produtos brasileiros** (`MLB`). Argentina (`MLA`), México (`MLM`), etc., não são suportados sem ajustar `siteId` no scraper.
- **Reviews públicas apenas.** Reviews moderadas/removidas não aparecem.
- **Rate limit ML:** ~300 reviews por sessão sem bloqueio. Produtos com >5.000 reviews podem exigir múltiplas execuções ou proxy.
- **Datas relativas em português** (`date_relative`) não são parseáveis programaticamente — use `date_created` (ISO).
- **CSV é sobrescrito** a cada dia. Snapshots diários preservam histórico, mas edições/deleções de reviews antigas não são detectadas explicitamente (aparecem sumidas).
- **Repositório privado no GitHub Free:** 2000 min/mês de Actions gratuitos. Uso atual ~2 min/dia = ~60 min/mês. Sobra bastante margem.

---

## Referências

- [Endpoint frontend usado](https://www.mercadolivre.com.br/noindex/catalog/reviews/MLB15238956/search?objectId=MLB15238956&siteId=MLB&isItem=false&offset=0&limit=10) (JSON público, sem OAuth)
- Documentação de implementação: [`SETUP.md`](./SETUP.md)
- Repositório: https://github.com/ViniciusTerra06/ml-reviews-scraper
