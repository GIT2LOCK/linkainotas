# Worker Python do LINKAI

Este diretório contém o processamento fiscal e a automação do Lumina. A API
FastAPI inicia o worker de fila automaticamente quando
`LINKAI_QUEUE_WORKER_ENABLED=true`.

## Processamento de PDFs e Excel

O processamento fiscal não depende do Lumina. Cada PDF gera sempre um XML
normalizado e, quando o usuário ativa a opção, um Excel baseado no modelo
`templates/Lote_de_Fatura_CEF_Consignado.xlsx`. O escritor altera somente os
valores das linhas de lançamento da aba `Lançamentos`, preservando as outras
abas, estilos, fórmulas, nomes definidos e validações do arquivo original.

Quando um PDF é escaneado e não possui camada de texto, o serviço usa
Tesseract para extrair texto e coordenadas antes de escolher o parser fiscal.
No Ubuntu, instale:

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-por
python -m pip install -r lumina_bot/requirements.txt
```

O modelo pode ser substituído por configuração, sem alterar o código:

```env
LINKAI_EXCEL_TEMPLATE_PATH=/opt/linkai/lumina_bot/templates/Lote_de_Fatura_CEF_Consignado.xlsx
LINKAI_OCR_LANG=por+eng
LINKAI_OCR_DPI=220
```

Valores ausentes no PDF não são inventados. Para campos administrativos do
modelo, como cliente de faturamento, centro de custo e código interno do
fornecedor, use `NotaFiscal.outros_campos` ou as variáveis de ambiente
`LINKAI_TEMPLATE_BILLING_CNPJ` e `LINKAI_TEMPLATE_BILLING_CLIENT`.

## Inicialização no Windows

Na máquina que possui o Lumina instalado:

```powershell
cd C:\LinkAI

$env:LINKAI_QUEUE_WORKER_ENABLED="true"
$env:LINKAI_WORKER_ID="lumina-maquina-01"

& ".\lumina_bot\.venv\Scripts\python.exe" `
  -m uvicorn backend.api.server:app `
  --host 0.0.0.0 `
  --port 8766
```

Na segunda máquina, use outro identificador, como
`lumina-maquina-02`. A porta local `8766` pode ser a mesma nas duas máquinas.

## Variáveis obrigatórias

Configure no ambiente seguro do worker:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=chave-de-servico
LINKAI_QUEUE_WORKER_ENABLED=true
LINKAI_WORKER_ID=lumina-maquina-01
LUMINA_USERNAME=usuario-do-lumina
LUMINA_PASSWORD=senha-do-lumina
LUMINA_EXECUTABLE_PATH=C:\caminho\para\900_Lumina.exe
```

O `SUPABASE_SERVICE_ROLE_KEY` nunca deve ser colocado no frontend ou no Git.

## Reinício e diagnóstico

O worker roda dentro do processo Uvicorn. Pressione `Ctrl+C` e execute o
comando novamente para reiniciar. Para verificar a API e o worker:

```powershell
curl.exe --max-time 5 http://127.0.0.1:8766/health
```

A resposta deve indicar `queue_worker.enabled=true`, o identificador da máquina
e `queue_worker.running=true`.

O fluxo completo da fila, as migrations e as regras de concorrência estão em
[`docs/lumina-queue.md`](../docs/lumina-queue.md).
