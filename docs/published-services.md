# Servicos do LinkAI Web publicado

O app publicado no Lovable roda o frontend e as server functions em ambiente web. Por isso, as responsabilidades ficam separadas:

- Processamento de documentos: PDF, XML, leitura fiscal, geracao de planilhas e historico. Nao precisa abrir o Lumina.
- Automacao Lumina: abertura do programa Windows e lancamento de notas. Precisa de uma maquina Windows com Lumina instalado.

## Processamento de documentos

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

Configure no Lovable:

```env
LINKAI_LUMINA_URL=https://sua-url-publica-do-executor-lumina
LINKAI_LUMINA_TOKEN=outro-token-longo-e-secreto
```

Na maquina Windows com Lumina instalado:

```powershell
$env:LINKAI_LUMINA_TOKEN="o-mesmo-token-do-lovable"
$env:LINKAI_ALLOWED_ORIGINS="https://linkai.2lock.app.br"
.\scripts\start-lumina-bridge.ps1
```

Essa URL e usada apenas para `lumina.start`.

## Compatibilidade

`LINKAI_BRIDGE_URL` e `LINKAI_BRIDGE_TOKEN` continuam aceitos como fallback para ambientes antigos, mas as variaveis especificas acima sao preferiveis.
