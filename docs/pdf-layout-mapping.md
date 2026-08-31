# Mapeamento fiscal PDF

O processamento classifica o texto antes de escolher o parser. Os layouts
determinísticos atualmente cobertos são:

- `NFSE_SP`: NFS-e municipal de São Paulo, incluindo a página IBS/CBS.
- `NFSE_COTIA_1P`: NFS-e municipal de Cotia em uma página, com RPS,
  competência, serviço, obra, CEI/CNO, IBS/CBS e retenções.
- `NFE_DANFE_55`: DANFE de NF-e modelo 55, incluindo os sublayouts
  `ECOMIX_OCR`, `FHOENIX` e `STAMP`, itens, duplicatas, transportador,
  volumes, totais e dados adicionais.

O leitor mantém texto por página e palavras com coordenadas. O parser grava
proveniência dos campos extraídos em `outros_campos.fontes`, sem impedir o
fallback dos parsers genéricos para outros documentos.

Cada documento gera XML normalizado `linkai.documento-fiscal.v1`. Excel é
opcional e, quando habilitado no modo padrão, preenche o modelo
`lumina_bot/templates/Lote_de_Fatura_CEF_Consignado.xlsx`. O arquivo é mantido
intacto e somente as linhas de lançamento da aba `Lançamentos` recebem os
valores extraídos. Há uma linha por item fiscal; número, série, datas, valores,
parcelas e tributos são mapeados para as colunas do modelo. As abas de apoio,
fórmulas, nomes definidos, validações e estilos originais são preservados.

O modo estruturado legado continua disponível para diagnósticos internos e
separa `documentos`, `itens`, `parcelas`, `tributos` e `validacoes` em abas
próprias. Ele não é o formato contábil usado pelo modo padrão.

Esse XML é uma representação normalizada do LinkAI. Ele não substitui o XML
oficial autorizado pela SEFAZ ou pela prefeitura quando o PDF não o contém.
