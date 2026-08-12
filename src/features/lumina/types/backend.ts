export interface CommandResult<T> {
  ok: boolean;
  data: T | null;
  error: string | null;
}

export interface OperatorProfile {
  name: string;
  role: string;
  email: string | null;
  avatar_url: string | null;
  source: "supabase" | "fallback";
}

export interface UploadedDocumentsResponse {
  paths: string[];
  count: number;
}

export type ProcessingSource = "supabase" | "folder" | "files";
export type ExcelMode = "single_sheet" | "multi_sheet" | "one_file_per_pdf";

export interface ProcessingOptions {
  source: ProcessingSource;
  paths: string[];
  downloadPath: string | null;
  downloadPathLabel?: string | null;
  generateExcel: boolean;
  downloadPdfsLocally: boolean;
  ignoreDuplicates: boolean;
  useCache: boolean;
  detectXml: boolean;
  useAiWhenNeeded: boolean;
  processSubfolders: boolean;
  excelMode: ExcelMode;
}

export interface ProcessingRow {
  name: string | null;
  type: string;
  pageCount: number | null;
  sizeBytes: number | null;
  status: string;
  source: string;
  hash: string | null;
  documentType: string | null;
  parser: string | null;
  error: string | null;
  progress: number;
  path?: string | null;
  originPath?: string | null;
  downloadedPath?: string | null;
  downloaded?: boolean;
}

export interface ProcessingResponse {
  source: string;
  rows?: ProcessingRow[];
  sessionId?: string;
  processedAt?: string;
  downloadPath?: string | null;
  summary: {
    listed: number;
    processed: number;
    ignored: number;
    failed: number;
    duplicated: number;
    elapsedSeconds?: number;
  };
}

export interface SpreadsheetInfo {
  name: string;
  path: string;
  sizeBytes: number;
  modifiedAt: number;
}

export interface NoticiaConstrucao {
  titulo: string;
  resumo: string | null;
  fonte: string;
  url: string;
  dataPublicacao: string | null;
}

export interface PontoIndicador {
  valor: number;
  dataReferencia: string;
}

export interface IndicadorConstrucao {
  codigo: string;
  nome: string;
  valor: number;
  unidade: string | null;
  dataReferencia: string | null;
  fonte: string | null;
  variacao: number | null;
  variacaoSufixo: "%" | "p.p." | null;
  historico: PontoIndicador[];
}

export interface PainelIndicadores {
  indicadores: IndicadorConstrucao[];
  atualizadoEm?: string | null;
}

export interface DefaultDownloadPathResponse {
  path: string;
}

export interface LocalFileInfo {
  id: string;
  name: string;
  type: string;
  path: string;
  originPath: string | null;
  sizeBytes: number | null;
  hash: string | null;
  source: string | null;
  documentType: string | null;
  parser: string | null;
  pageCount: number | null;
  status: string | null;
  error: string | null;
  processedAt: string | null;
  modifiedAt: string | null;
}

export interface ProcessingHistoryItem {
  sessionId: string;
  processedAt: string;
  source: string;
  downloadPath: string | null;
  listed: number;
  processed: number;
  ignored: number;
  failed: number;
  duplicated: number;
  elapsedSeconds: number;
  status: string;
}
