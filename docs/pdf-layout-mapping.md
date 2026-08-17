# Mapeamento fiscal PDF

O processamento classifica o texto antes de escolher o parser. Os layouts
determinísticos atualmente cobertos são:

- `NFSE_SP`: NFS-e municipal de São Paulo, incluindo a página IBS/CBS.
- `NFE_DANFE_55`: DANFE de NF-e modelo 55, incluindo itens, duplicatas,
  transportador, totais e ISSQN quando presentes.

O leitor mantém texto por página e palavras com coordenadas. O parser grava
proveniência dos campos extraídos em `outros_campos.fontes`, sem impedir o
fallback dos parsers genéricos para outros documentos.

Cada documento gera XML normalizado `linkai.documento-fiscal.v1`. Excel é
opcional e, quando habilitado, contém `documentos`, `itens`, `parcelas`,
`tributos` e `validacoes`.

Esse XML é uma representação normalizada do LinkAI. Ele não substitui o XML
oficial autorizado pela SEFAZ ou pela prefeitura quando o PDF não o contém.
