# ML Reviews Scraper

Scraper diário de avaliações do Mercado Livre. Gera um CSV por produto por dia + um `_latest.csv` estável para conectar em ferramentas de BI (Power BI, Metabase, Excel).

## Como funciona

- Lê `config.json` com a lista de MLB IDs (ex.: `MLB1234567890`).
- Consulta a API pública `https://api.mercadolibre.com/reviews/item/{ID}` paginando de 50 em 50 até esgotar.
- Salva:
  - `data/reviews_{MLB_ID}_{YYYY-MM-DD}.csv` — snapshot do dia (histórico).
  - `data/reviews_{MLB_ID}_latest.csv` — sempre sobrescrito com a última coleta.

Colunas: `review_id, product_id, rating, title, content, date_created, reviewer_id, likes, dislikes, valorization, relevance, buying_date, collected_at`.

## Setup (uma vez)

1. Instalar dependências:
   ```
   py -3 -m pip install -r requirements.txt
   ```

2. Editar `config.json` e substituir `MLB_COLOQUE_SEU_ID_AQUI` pelo ID real do seu produto.
   Aceita também URL completa (ex.: `https://produto.mercadolivre.com.br/MLB-1234567890-...`) — o scraper extrai o `MLBxxxx` automaticamente.

3. Rodar manual para validar:
   ```
   py -3 src\scraper.py
   ```
   Confira `data\` e `logs\scraper.log`.

4. Registrar agendamento diário (rodar como Administrador):
   ```
   register_task.bat
   ```
   Default: 08:00. Edite o `.bat` para outro horário.

## Comandos úteis

| Ação | Comando |
|---|---|
| Rodar agora | `py -3 src\scraper.py` |
| Ver log | `type logs\scraper.log` |
| Consultar tarefa | `schtasks /Query /TN "ML_Reviews_Scraper" /V /FO LIST` |
| Rodar tarefa manual | `schtasks /Run /TN "ML_Reviews_Scraper"` |
| Remover tarefa | `schtasks /Delete /TN "ML_Reviews_Scraper" /F` |

## Adicionar mais produtos

Basta editar `config.json`:
```json
{
  "product_ids": ["MLB1111111111", "MLB2222222222"],
  ...
}
```

## Conectar Power BI

Aponte para `data\reviews_{SEU_MLB_ID}_latest.csv`. Encoding UTF-8 (com BOM). Faça refresh diariamente após 08:00.

## Troubleshooting

- **`404` ou reviews vazias:** o produto pode não ter avaliações públicas na API. Verificar se o ID está correto e se há reviews visíveis na página pública.
- **`py` não reconhecido:** instalar Python 3 do python.org (marcar "Add to PATH") ou trocar `py -3` por `python` nos `.bat`.
- **Task não roda com PC dormindo:** abrir Task Scheduler, editar `ML_Reviews_Scraper` → Conditions → marcar "Wake the computer to run this task".
