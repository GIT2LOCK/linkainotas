# OCR para PDFs fiscais escaneados

Os layouts `ECOMIX_OCR` e `FHOENIX` dependem de OCR quando o PDF não possui camada de texto utilizável. O código usa Tesseract, preserva as coordenadas das palavras e grava `ocr_used` e a confiança média no XML e no Excel.

## Dependências Python

Dentro do ambiente virtual do serviço:

```powershell
& .\lumina_bot\.venv\Scripts\python.exe -m pip install -r .\lumina_bot\requirements.txt
```

## Windows

Instale o Tesseract OCR e confirme que `tesseract.exe` está no `PATH`. O serviço também procura automaticamente em `C:\Program Files\Tesseract-OCR\tesseract.exe`. Para uma instalação em outro local, defina `TESSERACT_CMD` ou `LINKAI_TESSERACT_CMD`. Depois valide:

```powershell
tesseract --version
& .\lumina_bot\.venv\Scripts\python.exe -c "import pytesseract; print(pytesseract.get_languages(config=''))"
```

Quando o pacote `por` estiver instalado, o serviço usa `por+eng`. Caso contrário, usa `eng` e mantém os números, códigos e valores extraídos sem inventar campos.

## Ubuntu

```bash
apt-get update
apt-get install -y tesseract-ocr tesseract-ocr-por
/opt/linkai/lumina_bot/.venv/bin/python -m pip install -r /opt/linkai/lumina_bot/requirements.txt
tesseract --version
```

Depois reinicie a API de processamento. PDFs com camada textual continuam usando a leitura nativa e não passam pelo OCR.
