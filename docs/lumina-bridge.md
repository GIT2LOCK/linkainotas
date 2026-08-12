# Executor Lumina no ambiente publicado

O LinkAI Web publicado nao consegue abrir o Lumina diretamente, porque o Lumina e uma aplicacao Windows controlada por `pywinauto`. Para os botoes de automacao funcionarem no dominio publicado, mantenha o executor Python rodando em uma maquina Windows com o Lumina instalado e exponha essa API por uma URL HTTPS segura.

## Variaveis do Lovable

Configure no ambiente publicado:

```env
LINKAI_BRIDGE_URL=https://sua-url-publica-do-executor
LINKAI_BRIDGE_TOKEN=um-token-longo-e-secreto
```

`LINKAI_BRIDGE_TOKEN` e opcional no codigo, mas recomendado. Quando definido, o app publicado chama o executor pelo servidor, sem expor o token no browser.

## Maquina Windows do executor

Na maquina onde o Lumina esta instalado:

```powershell
$env:LINKAI_BRIDGE_TOKEN="o-mesmo-token-do-lovable"
$env:LINKAI_ALLOWED_ORIGINS="https://linkai.2lock.app.br"
.\scripts\start-lumina-bridge.ps1
```

Depois publique a porta `8765` por um tunel HTTPS ou proxy seguro e use essa URL em `LINKAI_BRIDGE_URL`.
