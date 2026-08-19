# Servicos do LinkAI Web publicado

O app publicado no Lovable roda o frontend e as server functions em ambiente web. Por isso, as responsabilidades ficam separadas:

- Processamento de documentos: PDF, XML, leitura fiscal, geracao de planilhas e historico. Nao precisa abrir o Lumina.
- Automacao Lumina: abertura do programa Windows e lancamento de notas. Precisa de uma maquina Windows com Lumina instalado.

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

O lançamento atual usa a fila `public.lumina_jobs` no Supabase. O Lovable não precisa
conhecer as URLs ou portas das máquinas Windows e o usuário não escolhe executor.

Aplique a migração:

`supabase/migrations/20260819130000_create_lumina_jobs_queue.sql`

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
.\\lumina_bot\\.venv\\Scripts\\python.exe -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8766
```

O worker inicia automaticamente com a API e consulta a fila. Confira em
`/health` se `queue_worker.running` está como `true`.

O caminho antigo de chamada direta `lumina.start` continua disponível apenas
para compatibilidade com clientes legados; a tela atual de lançamento usa
exclusivamente a fila. O detalhamento está em [docs/lumina-queue.md](lumina-queue.md).

## Compatibilidade

`LINKAI_LUMINA_URLS`, `LINKAI_LUMINA_URL`, `LINKAI_BRIDGE_URL` e
`LINKAI_BRIDGE_TOKEN` continuam aceitos pelo endpoint legado, mas não participam
do novo fluxo de fila.
