import {
  ArrowRight,
  Cloud,
  Download,
  FileCheck2,
  FileText,
  FolderOpen,
  ListChecks,
  LoaderCircle,
  MousePointer,
  Table2,
  UploadCloud,
  X,
} from "lucide-react";
import type { ChangeEvent, DragEvent } from "react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import { ToggleRow } from "../components/ToggleRow";
import { callBackend, uploadLocalDocuments } from "../services/backend";
import type {
  DownloadableFile,
  ExcelMode,
  ProcessingOptions,
  ProcessingResponse,
  ProcessingSource,
} from "../types/backend";
import { useAsyncAction } from "../hooks/useAsyncAction";

interface BrowserDirectoryHandle {
  name: string;
  getFileHandle: (name: string, options: { create: boolean }) => Promise<BrowserFileHandle>;
}

interface BrowserFileHandle {
  createWritable: () => Promise<BrowserWritableFileStream>;
}

interface BrowserWritableFileStream {
  write: (data: Blob) => Promise<void>;
  close: () => Promise<void>;
}

declare global {
  interface Window {
    showDirectoryPicker?: () => Promise<BrowserDirectoryHandle>;
  }
}

const columns = [
  { key: "name", label: "Nome" },
  { key: "documentType", label: "Documento" },
  { key: "pageCount", label: "Páginas" },
  {
    key: "sizeBytes",
    label: "Tamanho",
    render: (row: Record<string, unknown>) => formatBytes(row["sizeBytes"] as number | null),
  },
  { key: "status", label: "Status" },
  {
    key: "source",
    label: "Origem",
    render: (row: Record<string, unknown>) => displayOrigin(String(row["source"] ?? "-")),
  },
  {
    key: "hash",
    label: "Hash",
    render: (row: Record<string, unknown>) =>
      typeof row["hash"] === "string" ? String(row["hash"]).slice(0, 12) : "-",
  },
  { key: "parser", label: "Parser" },
  {
    key: "downloadedPath",
    label: "Arquivo local",
    render: (row: Record<string, unknown>) =>
      displayPath(String(row["downloadedPath"] ?? row["path"] ?? "-")),
  },
  {
    key: "error",
    label: "Erro",
    render: (row: Record<string, unknown>) => String(row["error"] ?? "-"),
  },
  {
    key: "progress",
    label: "Progresso",
    render: (row: Record<string, unknown>) => `${String(row["progress"] ?? 0)}%`,
  },
];

const folderInputAttributes = {
  directory: "",
  webkitdirectory: "",
} as Record<string, string>;

export function ProcessPdfsPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [source, setSource] = useState<ProcessingSource>("supabase");
  const [downloadPath, setDownloadPath] = useState<string | null>(null);
  const [downloadPathLabel, setDownloadPathLabel] = useState<string | null>(null);
  const [browserDownloadDirectory, setBrowserDownloadDirectory] =
    useState<BrowserDirectoryHandle | null>(null);
  const [selectedPaths, setSelectedPaths] = useState<string[]>([]);
  const [selectedBrowserFiles, setSelectedBrowserFiles] = useState<File[]>([]);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const [persistedResponse, setPersistedResponse] = useState<ProcessingResponse | null>(null);
  const [options, setOptions] = useState<
    Omit<ProcessingOptions, "source" | "paths" | "downloadPath" | "downloadPathLabel">
  >({
    generateExcel: true,
    downloadPdfsLocally: true,
    ignoreDuplicates: true,
    useCache: true,
    detectXml: true,
    useAiWhenNeeded: false,
    processSubfolders: true,
    excelMode: "single_sheet",
  });
  const action = useAsyncAction((payload: ProcessingOptions) =>
    callBackend<ProcessingResponse>("documents.process", payload),
  );
  const lastProcessingAction = useAsyncAction(() =>
    callBackend<ProcessingResponse | null>("documents.last"),
  );
  const { run: loadLastProcessing } = lastProcessingAction;

  useEffect(() => {
    let active = true;

    loadLastProcessing()
      .then((lastProcessing) => {
        if (!active || !lastProcessing) {
          return;
        }

        setPersistedResponse(lastProcessing);

        if (
          lastProcessing.downloadPath &&
          !lastProcessing.downloadPath.startsWith("Pasta escolhida no navegador:")
        ) {
          setDownloadPath(lastProcessing.downloadPath);
          setDownloadPathLabel(lastProcessing.downloadPath);
        }
      })
      .catch(() => undefined);

    return () => {
      active = false;
    };
  }, [loadLastProcessing]);

  const rows = action.data?.rows ?? persistedResponse?.rows ?? [];
  const selectedDownloadLabel = downloadPathLabel ?? downloadPath;
  const sourceLabel = sourceSummaryLabel(source);
  const selectionLabel =
    source === "supabase"
      ? "Nuvem privada"
      : selectedPaths.length === 0
        ? "Nenhum item"
        : selectedPaths.length === 1
          ? "1 item"
          : `${selectedPaths.length} itens`;

  async function runProcessing() {
    if (options.downloadPdfsLocally && !selectedDownloadLabel && window.showDirectoryPicker) {
      setSelectionError("Escolha o local padrão de download antes de processar.");
      return;
    }

    if (options.downloadPdfsLocally && !selectedDownloadLabel && !window.showDirectoryPicker) {
      setDownloadPathLabel("Pasta padrão de downloads do navegador");
    }

    if (source !== "supabase" && selectedPaths.length === 0) {
      setSelectionError("Selecione uma pasta ou pelo menos um PDF/XML antes de processar.");
      return;
    }

    setSelectionError(null);

    if (
      options.downloadPdfsLocally &&
      browserDownloadDirectory &&
      selectedBrowserFiles.length > 0
    ) {
      try {
        await copyBrowserFilesToDirectory(selectedBrowserFiles, browserDownloadDirectory);
      } catch {
        setSelectionError(
          "Não foi possível salvar os documentos na pasta escolhida pelo navegador.",
        );
        return;
      }
    }

    try {
      const result = await action.run({
        ...options,
        source,
        paths: selectedPaths,
        downloadPath,
        downloadPathLabel: selectedDownloadLabel,
      });
      setPersistedResponse(result);
      try {
        await saveExcelFilesForUser(result.excelFiles ?? [], browserDownloadDirectory);
      } catch {
        setSelectionError(
          "O processamento terminou, mas não foi possível salvar o Excel na pasta escolhida.",
        );
      }
    } catch {
      return;
    }
  }

  function setExcelMode(excelMode: ExcelMode) {
    setOptions((current) => ({ ...current, excelMode }));
  }

  function selectCloud() {
    setSource("supabase");
    setSelectionError(null);
  }

  async function selectDownloadPath() {
    setSelectionError(null);

    if (!window.showDirectoryPicker) {
      setBrowserDownloadDirectory(null);
      setDownloadPath(null);
      setDownloadPathLabel("Pasta padrão de downloads do navegador");
      setSelectionError(
        "Este navegador não permite escolher pasta de destino. Use Chrome ou Edge atualizado.",
      );
      return;
    }

    try {
      const directory = await window.showDirectoryPicker();
      setBrowserDownloadDirectory(directory);
      setDownloadPath(null);
      setDownloadPathLabel(`Pasta escolhida no navegador: ${directory.name}`);
    } catch (error) {
      setSelectionError(selectionDialogError(error));
    }
  }

  async function selectFolder() {
    setSelectionError(null);
    folderInputRef.current?.click();
  }

  async function selectFiles() {
    setSelectionError(null);
    fileInputRef.current?.click();
  }

  async function handleBrowserFileSelection(event: ChangeEvent<HTMLInputElement>) {
    await uploadBrowserSelection(Array.from(event.target.files ?? []), "files");
    event.target.value = "";
  }

  async function handleBrowserFolderSelection(event: ChangeEvent<HTMLInputElement>) {
    await uploadBrowserSelection(Array.from(event.target.files ?? []), "folder");
    event.target.value = "";
  }

  async function uploadBrowserSelection(files: File[], nextSource: ProcessingSource) {
    const documentFiles = files.filter((file) => isSupportedFiscalDocument(file.name));

    if (documentFiles.length === 0) {
      setSelectionError("Nenhum PDF ou XML foi encontrado na seleção.");
      return;
    }

    try {
      const uploaded = await uploadLocalDocuments(documentFiles);

      if (uploaded.paths.length === 0) {
        setSelectionError("Nenhum PDF ou XML válido foi enviado para processamento.");
        return;
      }

      setSelectedBrowserFiles(documentFiles);
      setSelectedPaths(uploaded.paths);
      setSource(nextSource);
      setSelectionError(null);
    } catch (error) {
      setSelectionError(uploadErrorMessage(error));
    }
  }

  function clearSelection() {
    setSelectedBrowserFiles([]);
    setSelectedPaths([]);
    setSelectionError(null);
  }

  async function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();

    const files = Array.from(event.dataTransfer.files);
    const paths = files
      .map((file) => (file as File & { path?: string }).path)
      .filter((path): path is string => Boolean(path));

    if (paths.length > 0) {
      setSelectedBrowserFiles([]);
      setSelectedPaths(paths);
      setSource("files");
      setSelectionError(null);
      return;
    }

    await uploadBrowserSelection(files, "files");
  }

  return (
    <div className="page-stack">
      <input
        accept="application/pdf,application/xml,text/xml,.pdf,.xml"
        className="hidden-file-input"
        multiple
        onChange={handleBrowserFileSelection}
        ref={fileInputRef}
        type="file"
      />
      <input
        {...folderInputAttributes}
        className="hidden-file-input"
        multiple
        onChange={handleBrowserFolderSelection}
        ref={folderInputRef}
        type="file"
      />

      {action.error ? <div className="alert danger">{action.error}</div> : null}
      {selectionError ? <div className="alert danger">{selectionError}</div> : null}

      <div className="process-workspace">
        <div className="workflow-primary">
          <section className="process-hero">
            <div>
              <span className="eyebrow">Fluxo fiscal</span>
              <h2>Processamento de documentos</h2>
              <p>Importe PDFs e XMLs, acompanhe a detecção fiscal e gere planilhas consolidadas.</p>
            </div>
            <div className="process-hero-actions">
              <button
                className="button primary process-button"
                disabled={action.loading}
                onClick={runProcessing}
                type="button"
              >
                {action.loading ? "Processando" : "Processar"}
                {action.loading ? (
                  <LoaderCircle className="spin" size={18} />
                ) : (
                  <ArrowRight size={18} />
                )}
              </button>
            </div>
          </section>

          <div className="process-summary">
            <MetricCard icon={FileText} label="Documentos" value={rows.length} />
            <MetricCard icon={Cloud} label="Origem" value={sourceLabel} />
            <MetricCard icon={FileCheck2} label="Seleção" value={selectionLabel} />
            <MetricCard
              icon={Table2}
              label="Excel"
              tone="success"
              value={excelModeLabel(options.excelMode)}
            />
          </div>

          <div className="source-grid process-source-grid">
            <SourceOption
              active={source === "supabase"}
              description="Documentos salvos na nuvem"
              icon={UploadCloud}
              label="Nuvem"
              onClick={selectCloud}
            />
            <SourceOption
              active={source === "folder"}
              description="PDFs/XMLs de uma pasta"
              icon={FolderOpen}
              label="Pasta inteira"
              onClick={selectFolder}
            />
            <SourceOption
              active={source === "files"}
              description="Seleção avulsa de arquivos"
              icon={MousePointer}
              label="Arquivos manuais"
              onClick={selectFiles}
            />
          </div>

          <div
            className="drop-zone"
            onDragOver={(event) => event.preventDefault()}
            onDrop={handleDrop}
          >
            <div className="drop-zone-copy">
              <span className="drop-zone-icon" aria-hidden="true">
                <UploadCloud size={28} />
              </span>
              <div>
                <strong>{selectionTitle(source, selectedPaths.length)}</strong>
                <span>{selectionDescription(source, selectedPaths)}</span>
              </div>
            </div>
            <div className="drop-actions">
              <button className="button secondary" onClick={selectFolder} type="button">
                Selecionar pasta
              </button>
              <button className="button secondary" onClick={selectFiles} type="button">
                Selecionar arquivos
              </button>
              {selectedPaths.length > 0 ? (
                <button className="button ghost" onClick={clearSelection} type="button">
                  <X size={16} />
                  Limpar
                </button>
              ) : null}
            </div>
          </div>

          <DataTable
            columns={columns}
            emptyLabel="Nenhum documento processado ainda."
            rows={rows as unknown as Record<string, unknown>[]}
          />
        </div>

        <aside className="workflow-aside">
          <div className="download-location-panel">
            <div>
              <strong>Local padrão de download</strong>
              <span>{selectedDownloadLabel ?? "Escolha uma pasta antes de processar."}</span>
            </div>
            <button className="button secondary" onClick={selectDownloadPath} type="button">
              <Download size={16} />
              Escolher pasta
            </button>
          </div>

          {selectedPaths.length > 0 ? (
            <div className="selected-files-panel">
              <div>
                <span>Selecionado</span>
                <strong>
                  {selectedPaths.length === 1 ? "1 item" : `${selectedPaths.length} itens`}
                </strong>
              </div>
              <ul>
                {selectedPaths.slice(0, 6).map((path) => (
                  <li key={path}>{displayPath(path)}</li>
                ))}
              </ul>
              {selectedPaths.length > 6 ? (
                <small>+{selectedPaths.length - 6} arquivo(s) oculto(s)</small>
              ) : null}
            </div>
          ) : null}

          <div className="content-band option-panel">
            <div className="panel-heading">
              <h3>Opções</h3>
              <span>Preferências do processamento</span>
            </div>
            <div className="toggle-grid">
              <ToggleRow
                checked={options.generateExcel}
                label="Gerar Excel"
                onChange={(checked) =>
                  setOptions((current) => ({ ...current, generateExcel: checked }))
                }
              />
              <ToggleRow
                checked={options.downloadPdfsLocally}
                label="Baixar PDFs localmente"
                onChange={(checked) =>
                  setOptions((current) => ({ ...current, downloadPdfsLocally: checked }))
                }
              />
              <ToggleRow
                checked={options.ignoreDuplicates}
                label="Ignorar PDFs duplicados"
                onChange={(checked) =>
                  setOptions((current) => ({ ...current, ignoreDuplicates: checked }))
                }
              />
              <ToggleRow
                checked={options.useCache}
                label="Utilizar cache"
                onChange={(checked) => setOptions((current) => ({ ...current, useCache: checked }))}
              />
              <ToggleRow
                checked={options.detectXml}
                label="Detectar XML automaticamente"
                onChange={(checked) =>
                  setOptions((current) => ({ ...current, detectXml: checked }))
                }
              />
              <ToggleRow
                checked={options.useAiWhenNeeded}
                label="Utilizar IA quando necessário"
                onChange={(checked) =>
                  setOptions((current) => ({ ...current, useAiWhenNeeded: checked }))
                }
              />
              <ToggleRow
                checked={options.processSubfolders}
                label="Processar subpastas"
                onChange={(checked) =>
                  setOptions((current) => ({ ...current, processSubfolders: checked }))
                }
              />
            </div>
          </div>

          <div className="content-band excel-panel">
            <div className="panel-heading">
              <h3>Excel</h3>
              <span>Formato de saída</span>
            </div>
            <div className="segmented-stack" role="group" aria-label="Modo de geração do Excel">
              <button
                className={`segmented ${options.excelMode === "one_file_per_pdf" ? "is-active" : ""}`}
                onClick={() => setExcelMode("one_file_per_pdf")}
                type="button"
              >
                Uma planilha por PDF
              </button>
              <button
                className={`segmented ${options.excelMode === "single_sheet" ? "is-active" : ""}`}
                onClick={() => setExcelMode("single_sheet")}
                type="button"
              >
                Uma única aba
              </button>
              <button
                className={`segmented ${options.excelMode === "multi_sheet" ? "is-active" : ""}`}
                onClick={() => setExcelMode("multi_sheet")}
                type="button"
              >
                Abas separadas
              </button>
            </div>
            <div className="hint">
              <ListChecks size={16} />
              Cada documento pode virar uma aba dedicada dentro do mesmo Excel.
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

async function saveExcelFilesForUser(
  files: DownloadableFile[],
  directory: BrowserDirectoryHandle | null,
) {
  if (files.length === 0) {
    return;
  }

  if (directory) {
    for (const file of files) {
      const fileHandle = await directory.getFileHandle(file.name, { create: true });
      const writable = await fileHandle.createWritable();
      await writable.write(base64ToBlob(file.contentBase64, file.mimeType));
      await writable.close();
    }
    return;
  }

  for (const file of files) {
    const url = URL.createObjectURL(base64ToBlob(file.contentBase64, file.mimeType));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = file.name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

function base64ToBlob(contentBase64: string, mimeType: string): Blob {
  const binary = atob(contentBase64);
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return new Blob([bytes], { type: mimeType });
}

interface SourceOptionProps {
  active: boolean;
  description: string;
  icon: LucideIcon;
  label: string;
  onClick: () => void | Promise<void>;
}

function SourceOption({ active, description, icon: Icon, label, onClick }: SourceOptionProps) {
  return (
    <button
      className={`source-option ${active ? "is-active" : ""}`}
      onClick={onClick}
      type="button"
    >
      <span className="source-option-icon" aria-hidden="true">
        <Icon size={21} />
      </span>
      <span>
        <strong>{label}</strong>
        <small>{description}</small>
      </span>
    </button>
  );
}

async function copyBrowserFilesToDirectory(files: File[], directory: BrowserDirectoryHandle) {
  for (const file of files) {
    const fileHandle = await directory.getFileHandle(file.name, { create: true });
    const writable = await fileHandle.createWritable();
    await writable.write(file);
    await writable.close();
  }
}

function formatBytes(value: number | null) {
  if (!value) {
    return "-";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.floor(Math.log(value) / Math.log(1024));
  return `${(value / 1024 ** index).toFixed(1)} ${units[index]}`;
}

function displayPath(path: string) {
  return path.split(/[\\/]/).filter(Boolean).pop() ?? path;
}

function displayOrigin(source: string) {
  if (source === "supabase" || source === "fallback") {
    return "Nuvem";
  }

  if (source === "folder") {
    return "Pasta";
  }

  if (source === "files") {
    return "Arquivos";
  }

  return source;
}

function selectionTitle(source: ProcessingSource, count: number) {
  if (source === "supabase") {
    return "Entrada pela nuvem";
  }

  if (count > 0) {
    return source === "folder" ? "Pasta selecionada" : "Arquivos selecionados";
  }

  return source === "folder" ? "Selecione uma pasta" : "Selecione arquivos";
}

function selectionDescription(source: ProcessingSource, paths: string[]) {
  if (source === "supabase") {
    return "Os documentos serão buscados automaticamente na nuvem configurada.";
  }

  if (paths.length === 0) {
    return "Use o botão de seleção para abrir o explorador do computador.";
  }

  if (source === "folder") {
    return displayPath(paths[0] ?? "-");
  }

  return paths.length === 1
    ? displayPath(paths[0] ?? "-")
    : `${paths.length} arquivos selecionados.`;
}

function sourceSummaryLabel(source: ProcessingSource) {
  if (source === "supabase") {
    return "Nuvem";
  }

  return source === "folder" ? "Pasta" : "Arquivos";
}

function excelModeLabel(excelMode: ExcelMode) {
  if (excelMode === "one_file_per_pdf") {
    return "Por PDF";
  }

  return excelMode === "single_sheet" ? "Aba única" : "Multiabas";
}

function isSupportedFiscalDocument(fileName: string) {
  const normalized = fileName.toLowerCase();
  return normalized.endsWith(".pdf") || normalized.endsWith(".xml");
}

function selectionDialogError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);

  if (message.toLowerCase().includes("cancel")) {
    return null;
  }

  return "Não foi possível abrir o seletor nativo do aplicativo.";
}

function uploadErrorMessage(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);

  if (
    message.includes("conector de processamento") ||
    message.includes("processamento de documentos") ||
    message.includes("LINKAI_PROCESSING_URL")
  ) {
    return message;
  }

  if (message.includes("404")) {
    return "A API local está rodando, mas está desatualizada. Rode stop-linkai-web.ps1 e depois run-linkai-web.ps1.";
  }

  if (message.includes("Failed to fetch") || message.includes("unavailable")) {
    return "Não foi possível enviar os documentos para a API local. Verifique se o backend está rodando na porta 8765.";
  }

  return "Não foi possível enviar os documentos para a API local.";
}
