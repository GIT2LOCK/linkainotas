# Servicos do LinkAI Web publicado

O app publicado no Lovable roda o frontend e as server functions em ambiente web. Por isso, as responsabilidades ficam separadas:

- Processamento de documentos: PDF, XML, leitura fiscal, geracao de planilhas e historico. Nao precisa abrir o Lumina.
- Automacao Lumina: abertura do programa Windows e lancamento de notas. Precisa de uma maquina Windows com Lumina instalado.

## Portas e responsabilidades

| Serviço | Máquina | Porta | Função |
| --- | --- | --- | --- |
| API de processamento | Ubuntu ou servidor Python | `8765` | PDF, XML, Excel e arquivos |
| Worker do Lumina | Cada máquina Windows | `8766` | Fila e automação do ERP Lumina |

A porta `8766` é local de cada máquina Windows. Todas podem usar o mesmo número
porque possuem endereços IP diferentes. O usuário não acessa diretamente essas
máquinas: ele cria uma solicitação no banco e a primeira máquina livre a assume.

## Processamento de documentos

Durante o desenvolvimento na rede local, o servidor web deve acessar a API Python
por meio de uma URL configurada no ambiente do servidor web. Nao use o IP da
maquina que esta exibindo o frontend, pois a API pode estar em outro computador.

Exemplo para a API Ubuntu publicada por DDNS:

```env
LINKAI_PROCESSING_URL=http://escritorio.2lock.myddns.com:8765
LINKAI_PROCESSING_TOKEN=mesmo-token-configurado-na-api-python
```

Essas variaveis devem ficar no `.env.local` do desenvolvimento ou nos secrets do
ambiente publicado. O token e lido por uma server function e nao e enviado para o
JavaScript do navegador.

Configure no Lovable:

```env
LINKAI_PROCESSING_URL=https://sua-url-publica-da-api-de-processamento
LINKAI_PROCESSING_TOKEN=um-token-longo-e-secreto
```

Na maquina/servidor que vai processar documentos:

```powershell
$env:LINKAI_PROCESSING_TOKEN="o-mesmo-token-do-lovable"
$env:LINKAI_ALLOWED_ORIGINS="https://linkai.2lock.app.br"
.\scripts\start-processing-api.ps1
```

Essa API executa `/uploads/documents` e `/invoke` para acoes como:

- `documents.process`
- `documents.last`
- `files.list`
- `history.list`
- `spreadsheets.list`
- `logs.latest`
- `cloud.test`

## Lancamento no Lumina

O lançamento usa as tabelas `public.lumina_queue_requests`,
`public.lumina_jobs` e `public.lumina_queue_logs` no Supabase. O Lovable não
precisa conhecer as URLs ou portas das máquinas Windows e o usuário não escolhe
executor.

Confirme no histórico do Supabase estas migrations, nesta ordem:

`supabase/migrations/20260819130000_create_lumina_jobs_queue.sql`

`supabase/migrations/20260827161250_*.sql`

`supabase/migrations/20260827161322_*.sql`

Os dois últimos arquivos foram gerados pelo Lovable. Não aplique a migration
local anterior `20260827120000_add_lumina_request_batches.sql` no mesmo banco.

Na aplicação publicada, mantenha as variáveis normais de sessão do Supabase já
configuradas. Não é necessário definir `LINKAI_LUMINA_URL` ou
`LINKAI_LUMINA_URLS` para a tela atual.

Em cada máquina Windows, configure no `lumina_bot/.env`:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=chave-de-servico
LINKAI_QUEUE_WORKER_ENABLED=true
LINKAI_WORKER_ID=lumina-maquina-01
LINKAI_QUEUE_POLL_SECONDS=3
LINKAI_QUEUE_LEASE_SECONDS=300
```

Use `lumina-maquina-02` na segunda máquina. A chave de serviço deve ser a mesma
nas duas máquinas, permanecer somente no backend e nunca ser versionada.

Inicie a API em cada máquina:

```powershell
.\lumina_bot\.venv\Scripts\python.exe -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8766
```

O worker inicia automaticamente com a API e consulta a fila. Confira em
`/health` se `queue_worker.running` está como `true`.

Para reiniciar, pressione `Ctrl+C` no terminal do Uvicorn e execute o comando
novamente. Se o terminal não estiver disponível:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match "uvicorn.*8766" } |
  Select-Object ProcessId,Name,CommandLine

Stop-Process -Id NUMERO_DO_PID
```

O `LINKAI_WORKER_ID` deve ser único, por exemplo `lumina-maquina-01` e
`lumina-maquina-02`. Em caso de falha, a reserva expira e outro worker pode
assumir a solicitação.

O caminho antigo de chamada direta `lumina.start` continua disponível apenas
para compatibilidade com clientes legados; a tela atual de lançamento usa
exclusivamente a fila. O detalhamento está em [docs/lumina-queue.md](lumina-queue.md).

## Compatibilidade

`LINKAI_LUMINA_URLS`, `LINKAI_LUMINA_URL`, `LINKAI_BRIDGE_URL` e
`LINKAI_BRIDGE_TOKEN` continuam aceitos pelo endpoint legado, mas não participam
do novo fluxo de fila.
