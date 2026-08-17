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

Configure no Lovable:

```env
LINKAI_LUMINA_URLS=http://escritorio.2lock.myddns.com:8766,http://escritorio.2lock.myddns.com:8767
LINKAI_LUMINA_TOKEN=outro-token-longo-e-secreto
```

Os executores sao tentados na ordem informada. Quando o primeiro responder que
esta ocupado (`409`) ou indisponivel, a server function tenta o proximo. A
variavel legada `LINKAI_LUMINA_URL` continua funcionando para uma unica maquina.

Cada executor Windows deve usar a porta local `8766`. O roteador deve publicar
portas externas diferentes, por exemplo `8766 -> maquina 01:8766` e
`8767 -> maquina 02:8766`.

Na maquina Windows com Lumina instalado:

```powershell
$env:LINKAI_LUMINA_TOKEN="o-mesmo-token-do-lovable"
$env:LINKAI_ALLOWED_ORIGINS="https://linkai.2lock.app.br"
.\scripts\start-lumina-bridge.ps1
```

Essa URL e usada apenas para `lumina.start`.

O endpoint `/health` informa `busy: true` quando existe uma sessao Lumina aberta.
Para liberar o executor, encerre o Lumina na maquina correspondente.

## Compatibilidade

`LINKAI_BRIDGE_URL` e `LINKAI_BRIDGE_TOKEN` continuam aceitos como fallback para ambientes antigos, mas as variaveis especificas acima sao preferiveis.
