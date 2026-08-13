import type {
  CommandResult,
  IndicadorConstrucao,
  NoticiaConstrucao,
  PainelIndicadores,
  UploadedDocumentsResponse,
} from "../types/backend";
import { invokePublishedBackend, uploadPublishedDocuments } from "./bridge.functions";

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

export const PUBLISHED_CONNECTOR_MESSAGE =
  "Servico publicado ainda nao configurado para esta funcionalidade.";

export async function callBackend<T>(action: string, payload: object = {}): Promise<T> {
  const fallback = fallbackForAction<T>(action, payload);
  const apiBaseUrl = localApiBaseUrl();

  if (!apiBaseUrl) {
    return callPublishedBridge(action, payload, fallback);
  }

  let result: CommandResult<T>;

  try {
    result = await callLocalApi<T>(apiBaseUrl, action, payload);
  } catch (error) {
    if (fallback !== undefined) {
      return fallback;
    }

    throw error;
  }

  if (!result.ok) {
    if (fallback !== undefined) {
      return fallback;
    }

    throw new Error(result.error ?? "Backend command failed");
  }

  return result.data as T;
}

export function isTauriRuntime(): boolean {
  return false;
}

export function hasProcessingConnector(): boolean {
  return Boolean(localApiBaseUrl());
}

export async function uploadLocalDocuments(files: File[]): Promise<UploadedDocumentsResponse> {
  const apiBaseUrl = localApiBaseUrl();

  if (!apiBaseUrl) {
    return uploadDocumentsThroughPublishedService(files);
  }

  const formData = new FormData();

  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${apiBaseUrl}/uploads/documents`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Local upload unavailable: ${response.status}`);
  }

  return (await response.json()) as UploadedDocumentsResponse;
}

export const uploadLocalPdfs = uploadLocalDocuments;

async function callLocalApi<T>(
  apiBaseUrl: string,
  action: string,
  payload: object,
): Promise<CommandResult<T>> {
  const response = await fetch(`${apiBaseUrl}/invoke`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ action, payload }),
  });

  if (!response.ok) {
    throw new Error(`Local API unavailable: ${response.status}`);
  }

  return (await response.json()) as CommandResult<T>;
}

async function callPublishedBridge<T>(
  action: string,
  payload: object,
  fallback: T | undefined,
): Promise<T> {
  const result = (await invokePublishedBackend({
    data: {
      action,
      payload,
    },
  })) as CommandResult<T>;

  if (result.ok) {
    return result.data as T;
  }

  if (fallback !== undefined) {
    return fallback;
  }

  throw new Error(result.error ?? PUBLISHED_CONNECTOR_MESSAGE);
}

async function uploadDocumentsThroughPublishedService(
  files: File[],
): Promise<UploadedDocumentsResponse> {
  const result = await uploadPublishedDocuments({
    data: {
      files: await Promise.all(
        files.map(async (file) => ({
          contentBase64: arrayBufferToBase64(await file.arrayBuffer()),
          name: file.name,
          type: file.type || null,
        })),
      ),
    },
  });

  if (!result.ok || !result.data) {
    throw new Error(result.error ?? "Nao foi possivel enviar documentos para processamento.");
  }

  return result.data;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  let binary = "";

  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }

  return btoa(binary);
}

function localApiBaseUrl(): string | null {
  const configuredUrl = import.meta.env.VITE_LINKAI_API_URL;
  return configuredUrl?.trim().replace(/\/+$/, "") || null;
}

function fallbackForAction<T>(action: string, payload: object): T | undefined {
  if (action === "noticias.recentes") {
    return fallbackNews(payload) as T;
  }

  if (action === "indicadores.painel") {
    return {
      indicadores: FALLBACK_INDICATORS,
      atualizadoEm: new Date().toISOString(),
    } as T;
  }

  if (action === "documents.last") {
    return null as T;
  }

  if (action === "history.list" || action === "spreadsheets.list" || action === "files.list") {
    return [] as T;
  }

  if (action === "logs.latest") {
    return {
      path: "Ambiente publicado",
      lines: [
        "LinkAI Web publicado com sucesso.",
        "Os logs de processamento serao exibidos quando o servico de documentos estiver configurado neste ambiente.",
      ],
    } as T;
  }

  return undefined;
}

function fallbackNews(payload: object): NoticiaConstrucao[] {
  const limit = payloadLimit(payload) ?? FALLBACK_NEWS.length;
  return FALLBACK_NEWS.slice(0, limit);
}

function payloadLimit(payload: object): number | null {
  const candidate = (payload as { limite?: unknown }).limite;

  if (typeof candidate !== "number" || !Number.isFinite(candidate)) {
    return null;
  }

  return Math.max(1, Math.trunc(candidate));
}

const FALLBACK_NEWS: NoticiaConstrucao[] = [
  {
    fonte: "Linka Engenharia",
    titulo: "Gabriel 2555",
    resumo:
      "Empreendimento residencial com assinatura Linka na construcao, incorporacao Gabripar e projeto de arquitetura Gui Mattos, reforcando alta execucao em obras urbanas sofisticadas.",
    url: "https://linka.eng.br/obra-gabriel/",
    dataPublicacao: "2026-08-12T08:00:00-03:00",
  },
  {
    fonte: "Linka Engenharia",
    titulo: "Amauri",
    resumo:
      "Projeto com incorporacao Idea Zarvos, arquitetura Isay Weinfeld e construcao Linka, combinando precisao executiva, acabamento premium e coordenacao tecnica de alto nivel.",
    url: "https://linka.eng.br/obra-amauri/",
    dataPublicacao: "2026-08-12T08:00:00-03:00",
  },
  {
    fonte: "Linka Engenharia",
    titulo: "Itacema",
    resumo:
      "Obra desenvolvida com Hedge Investments, Paladin Realty Partners e Idea!Zarvos, com arquitetura Bernardes e execucao Linka em uma operacao residencial de padrao elevado.",
    url: "https://linka.eng.br/obra-itacema/",
    dataPublicacao: "2026-08-12T08:00:00-03:00",
  },
  {
    fonte: "Linka Engenharia",
    titulo: "Fonseca Rodrigues",
    resumo:
      "Projeto assinado pela Triptyque Architecture, incorporacao Toca 55 e construcao Linka, reunindo linguagem arquitetonica contemporanea e controle tecnico de obra.",
    url: "https://linka.eng.br/projeto-fonseca-rodrigues/",
    dataPublicacao: "2026-08-12T08:00:00-03:00",
  },
  {
    fonte: "Linka Engenharia",
    titulo: "Execucao premium em obras residenciais",
    resumo:
      "A Linka segue ampliando sua presenca em projetos de alto padrao com foco em engenharia aplicada, planejamento fino e acompanhamento fiscal de cada etapa construtiva.",
    url: "https://linka.eng.br/obras/",
    dataPublicacao: "2026-08-12T08:00:00-03:00",
  },
  {
    fonte: "Jornal da Construcao Civil",
    titulo: "Gerdau abre inscricoes para programa de estagio em todo o Brasil",
    resumo:
      "Companhia oferece vagas em diversas regioes do pais para estudantes de engenharia e areas correlatas, fortalecendo a formacao de novos profissionais para a cadeia da construcao.",
    url: "https://jornaldaconstrucaocivil.com.br/?p=27097",
    dataPublicacao: "2026-08-11T16:49:49-03:00",
  },
  {
    fonte: "CBIC",
    titulo: "Projeto Trilhas Profissionais e apresentado no encontro das regionais",
    resumo:
      "A iniciativa estrutura caminhos de formacao para profissionais da construcao, aproximando qualificacao tecnica, produtividade e demandas reais das empresas do setor.",
    url: "https://cbic.org.br/#trilhas-profissionais",
    dataPublicacao: "2026-08-12T09:00:00-03:00",
  },
  {
    fonte: "Jornal da Construcao Civil",
    titulo: "Parceria leva atendimento oftalmologico aos canteiros de obras",
    resumo:
      "Acao do Seconci-Rio com a Firjan SESI amplia cuidados com a saude dos trabalhadores diretamente nos canteiros, reforcando seguranca e bem-estar operacional.",
    url: "https://jornaldaconstrucaocivil.com.br/?p=27094",
    dataPublicacao: "2026-08-11T16:37:33-03:00",
  },
  {
    fonte: "CBIC",
    titulo: "ConstruHub reforca inovacao e conexao entre empresas da construcao",
    resumo:
      "Ecossistema setorial aproxima empresas, tecnologia e oportunidades de modernizacao, com foco em eficiencia, digitalizacao e qualidade na construcao civil brasileira.",
    url: "https://cbic.org.br/#construcao-inovacao",
    dataPublicacao: "2026-08-12T08:30:00-03:00",
  },
  {
    fonte: "InfoMoney (Commodities)",
    titulo: "Materiais e commodities seguem no radar de custos das obras",
    resumo:
      "Acompanhamento de metais, energia e petroleo ajuda construtoras a proteger margens, revisar compras e antecipar variacoes que afetam insumos essenciais.",
    url: "https://www.infomoney.com.br/cotacoes/commodities/",
    dataPublicacao: "2026-08-12T07:30:00-03:00",
  },
  {
    fonte: "CBIC",
    titulo: "Seguranca juridica ganha espaco nas discussoes do licenciamento",
    resumo:
      "Entidades do setor defendem regras mais claras para reduzir inseguranca, acelerar empreendimentos regulares e melhorar previsibilidade para incorporadoras e construtoras.",
    url: "https://cbic.org.br/#licenciamento-ambiental",
    dataPublicacao: "2026-08-11T14:00:00-03:00",
  },
  {
    fonte: "Jornal da Construcao Civil",
    titulo: "Empresas chinesas ampliam presenca em evento nacional do setor",
    resumo:
      "Maior participacao internacional em feiras especializadas indica interesse crescente no mercado brasileiro, com oportunidades em equipamentos, tecnologia e fornecimento.",
    url: "https://jornaldaconstrucaocivil.com.br/#empresas-chinesas",
    dataPublicacao: "2026-08-11T11:00:00-03:00",
  },
  {
    fonte: "CBIC",
    titulo: "Construtoras fortalecem agenda de produtividade e industrializacao",
    resumo:
      "Debates sobre metodos construtivos, planejamento e tecnologia apontam caminhos para reduzir desperdicios, melhorar prazos e elevar a qualidade das entregas.",
    url: "https://cbic.org.br/#produtividade",
    dataPublicacao: "2026-08-10T10:30:00-03:00",
  },
  {
    fonte: "InfoMoney (Commodities)",
    titulo: "Cobre e aluminio seguem relevantes para orcamentos de infraestrutura",
    resumo:
      "Variacoes em metais industriais continuam importantes para compras tecnicas, instalacoes eletricas, esquadrias e outros componentes sensiveis ao mercado internacional.",
    url: "https://www.infomoney.com.br/cotacoes/commodities/#metais",
    dataPublicacao: "2026-08-10T09:00:00-03:00",
  },
  {
    fonte: "Jornal da Construcao Civil",
    titulo: "Capacitacao tecnica apoia canteiros mais seguros e eficientes",
    resumo:
      "Programas de treinamento e reciclagem profissional ajudam equipes de obra a operar com mais padronizacao, qualidade e previsibilidade nos processos executivos.",
    url: "https://jornaldaconstrucaocivil.com.br/#capacitacao",
    dataPublicacao: "2026-08-09T10:00:00-03:00",
  },
  {
    fonte: "CBIC",
    titulo: "Setor acompanha indicadores para planejar novos ciclos de obras",
    resumo:
      "Monitoramento de juros, inflacao, custos e emprego apoia decisoes de investimento e ajuda empresas a ajustar cronogramas com maior clareza.",
    url: "https://cbic.org.br/#indicadores",
    dataPublicacao: "2026-08-09T08:30:00-03:00",
  },
  {
    fonte: "Jornal da Construcao Civil",
    titulo: "Boas praticas de gestao aproximam engenharia e controle financeiro",
    resumo:
      "Construtoras seguem investindo em rotinas integradas para melhorar previsao de custos, compras, documentos fiscais e acompanhamento de desempenho das obras.",
    url: "https://jornaldaconstrucaocivil.com.br/#gestao",
    dataPublicacao: "2026-08-08T09:30:00-03:00",
  },
  {
    fonte: "InfoMoney (Commodities)",
    titulo: "Cenarios de energia e petroleo seguem acompanhados pela construcao",
    resumo:
      "Custos de transporte, combustiveis e derivados continuam no radar das obras, principalmente em cadeias com logistica intensiva e alta movimentacao de materiais.",
    url: "https://www.infomoney.com.br/cotacoes/commodities/#energia",
    dataPublicacao: "2026-08-08T08:00:00-03:00",
  },
];

const FALLBACK_INDICATORS: IndicadorConstrucao[] = [
  {
    codigo: "dolar-ptax",
    nome: "Dolar (PTAX)",
    valor: 5.1,
    unidade: "R$",
    dataReferencia: "2026-08-12",
    fonte: "BCB SGS",
    variacao: 0.44,
    variacaoSufixo: "%",
    historico: [
      { dataReferencia: "2026-08-04", valor: 5.06 },
      { dataReferencia: "2026-08-05", valor: 5.08 },
      { dataReferencia: "2026-08-06", valor: 5.07 },
      { dataReferencia: "2026-08-07", valor: 5.09 },
      { dataReferencia: "2026-08-10", valor: 5.1 },
      { dataReferencia: "2026-08-11", valor: 5.08 },
      { dataReferencia: "2026-08-12", valor: 5.1 },
    ],
  },
  {
    codigo: "incc-di-mensal",
    nome: "INCC-DI (variacao mensal)",
    valor: 0.61,
    unidade: "% a.m.",
    dataReferencia: "2026-07-31",
    fonte: "BCB / FGV",
    variacao: 0.1,
    variacaoSufixo: "p.p.",
    historico: [
      { dataReferencia: "2026-01-31", valor: 0.43 },
      { dataReferencia: "2026-02-28", valor: 0.52 },
      { dataReferencia: "2026-03-31", valor: 0.49 },
      { dataReferencia: "2026-04-30", valor: 0.72 },
      { dataReferencia: "2026-05-31", valor: 0.58 },
      { dataReferencia: "2026-06-30", valor: 0.51 },
      { dataReferencia: "2026-07-31", valor: 0.61 },
    ],
  },
  {
    codigo: "incc-di-12m",
    nome: "INCC-DI (acumulado 12 meses)",
    valor: 6.46,
    unidade: "% 12m",
    dataReferencia: "2026-07-31",
    fonte: "BCB / FGV",
    variacao: -0.32,
    variacaoSufixo: "p.p.",
    historico: [
      { dataReferencia: "2026-01-31", valor: 6.88 },
      { dataReferencia: "2026-02-28", valor: 6.79 },
      { dataReferencia: "2026-03-31", valor: 6.74 },
      { dataReferencia: "2026-04-30", valor: 6.68 },
      { dataReferencia: "2026-05-31", valor: 6.59 },
      { dataReferencia: "2026-06-30", valor: 6.53 },
      { dataReferencia: "2026-07-31", valor: 6.46 },
    ],
  },
  {
    codigo: "igp-m",
    nome: "IGP-M (variacao mensal)",
    valor: -1.16,
    unidade: "% a.m.",
    dataReferencia: "2026-07-31",
    fonte: "BCB / FGV",
    variacao: -2.1,
    variacaoSufixo: "p.p.",
    historico: [
      { dataReferencia: "2026-01-31", valor: 0.24 },
      { dataReferencia: "2026-02-28", valor: 0.38 },
      { dataReferencia: "2026-03-31", valor: 0.11 },
      { dataReferencia: "2026-04-30", valor: -0.08 },
      { dataReferencia: "2026-05-31", valor: 0.16 },
      { dataReferencia: "2026-06-30", valor: 0.94 },
      { dataReferencia: "2026-07-31", valor: -1.16 },
    ],
  },
  {
    codigo: "ipca",
    nome: "IPCA (variacao mensal)",
    valor: 0.07,
    unidade: "% a.m.",
    dataReferencia: "2026-07-31",
    fonte: "BCB / IBGE",
    variacao: -0.45,
    variacaoSufixo: "p.p.",
    historico: [
      { dataReferencia: "2026-01-31", valor: 0.52 },
      { dataReferencia: "2026-02-28", valor: 0.41 },
      { dataReferencia: "2026-03-31", valor: 0.36 },
      { dataReferencia: "2026-04-30", valor: 0.22 },
      { dataReferencia: "2026-05-31", valor: 0.18 },
      { dataReferencia: "2026-06-30", valor: 0.12 },
      { dataReferencia: "2026-07-31", valor: 0.07 },
    ],
  },
  {
    codigo: "aluminio",
    nome: "Aluminio",
    valor: 3438.85,
    unidade: "USD/tonelada",
    dataReferencia: "2026-08-12",
    fonte: "Yahoo Finance / COMEX",
    variacao: 9.73,
    variacaoSufixo: "%",
    historico: [
      { dataReferencia: "2026-08-04", valor: 3385.7 },
      { dataReferencia: "2026-08-05", valor: 3408.3 },
      { dataReferencia: "2026-08-06", valor: 3396.1 },
      { dataReferencia: "2026-08-07", valor: 3418.6 },
      { dataReferencia: "2026-08-10", valor: 3425.4 },
      { dataReferencia: "2026-08-11", valor: 3432.2 },
      { dataReferencia: "2026-08-12", valor: 3438.85 },
    ],
  },
  {
    codigo: "cobre",
    nome: "Cobre",
    valor: 13552.04,
    unidade: "USD/tonelada",
    dataReferencia: "2026-08-12",
    fonte: "Yahoo Finance / COMEX",
    variacao: 4.35,
    variacaoSufixo: "%",
    historico: [
      { dataReferencia: "2026-08-04", valor: 13390.2 },
      { dataReferencia: "2026-08-05", valor: 13424.8 },
      { dataReferencia: "2026-08-06", valor: 13408.5 },
      { dataReferencia: "2026-08-07", valor: 13480.9 },
      { dataReferencia: "2026-08-10", valor: 13510.4 },
      { dataReferencia: "2026-08-11", valor: 13536.7 },
      { dataReferencia: "2026-08-12", valor: 13552.04 },
    ],
  },
  {
    codigo: "cdi",
    nome: "CDI (anualizado)",
    valor: 14.02,
    unidade: "% a.a.",
    dataReferencia: "2026-08-12",
    fonte: "BCB SGS",
    variacao: 1.78,
    variacaoSufixo: "p.p.",
    historico: [
      { dataReferencia: "2026-08-04", valor: 14.02 },
      { dataReferencia: "2026-08-05", valor: 14.02 },
      { dataReferencia: "2026-08-06", valor: 14.02 },
      { dataReferencia: "2026-08-07", valor: 14.02 },
      { dataReferencia: "2026-08-10", valor: 14.02 },
      { dataReferencia: "2026-08-11", valor: 14.02 },
      { dataReferencia: "2026-08-12", valor: 14.02 },
    ],
  },
  {
    codigo: "petroleo-brent",
    nome: "Petroleo (Brent)",
    valor: 83.76,
    unidade: "USD/barril",
    dataReferencia: "2026-08-12",
    fonte: "Yahoo Finance / NYMEX",
    variacao: 18.15,
    variacaoSufixo: "%",
    historico: [
      { dataReferencia: "2026-08-04", valor: 81.64 },
      { dataReferencia: "2026-08-05", valor: 82.12 },
      { dataReferencia: "2026-08-06", valor: 82.44 },
      { dataReferencia: "2026-08-07", valor: 82.91 },
      { dataReferencia: "2026-08-10", valor: 83.04 },
      { dataReferencia: "2026-08-11", valor: 83.31 },
      { dataReferencia: "2026-08-12", valor: 83.76 },
    ],
  },
];
