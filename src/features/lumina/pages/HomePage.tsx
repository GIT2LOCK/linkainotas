import {
  ArrowUpRight,
  Building2,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  LineChart as LineChartIcon,
  Loader2,
  Newspaper,
  TrendingDown,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { SectionHeader } from "../components/SectionHeader";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { callBackend } from "../services/backend";
import type { IndicadorConstrucao, NoticiaConstrucao, PainelIndicadores } from "../types/backend";

const EMPTY_NEWS: NoticiaConstrucao[] = [];

export function HomePage() {
  const newsAction = useAsyncAction(() =>
    callBackend<NoticiaConstrucao[]>("noticias.recentes", { limite: 18 }),
  );
  const indicatorsAction = useAsyncAction(() =>
    callBackend<PainelIndicadores>("indicadores.painel"),
  );
  const { run: loadNews } = newsAction;
  const { run: loadIndicators } = indicatorsAction;

  const loadInsights = useCallback(async () => {
    await Promise.allSettled([loadNews(), loadIndicators()]);
  }, [loadIndicators, loadNews]);

  useEffect(() => {
    loadInsights().catch(() => undefined);
    const interval = window.setInterval(
      () => {
        loadInsights().catch(() => undefined);
      },
      24 * 60 * 60 * 1000,
    );

    return () => window.clearInterval(interval);
  }, [loadInsights]);

  const news = newsAction.data ?? EMPTY_NEWS;
  const indicators = indicatorsAction.data?.indicadores ?? [];
  const featuredNews = useMemo(() => {
    return news.filter((item) => item.fonte === "Linka Engenharia").slice(0, 5);
  }, [news]);
  const listedNews = useMemo(() => {
    const featuredUrls = new Set(featuredNews.map((item) => item.url));
    return news.filter((item) => !featuredUrls.has(item.url));
  }, [featuredNews, news]);

  return (
    <div className="page-stack insights-page">
      <SectionHeader
        eyebrow="Início"
        title="Notícias e indicadores"
        description="Notícias setoriais e cotações relevantes para a construção civil."
      />

      {featuredNews.length > 0 ? (
        <section
          className="insights-section insights-carousel-section"
          aria-labelledby="featured-heading"
        >
          <InsightsHeading
            description="Obras em andamento e projetos da Linka Engenharia."
            icon={Building2}
            id="featured-heading"
            title="Linka em destaque"
          />
          <NewsCarousel items={featuredNews} />
        </section>
      ) : null}

      <div className="insights-layout">
        <section className="insights-section" aria-labelledby="news-heading">
          <InsightsHeading
            description="Boas notícias e oportunidades relevantes para construção."
            icon={Newspaper}
            id="news-heading"
            title="Construção civil em movimento"
          />

          {newsAction.error ? <div className="alert danger">{newsAction.error}</div> : null}

          {newsAction.loading && news.length === 0 ? (
            <LoadingState label="Carregando notícias recentes" />
          ) : listedNews.length === 0 ? (
            <EmptyState label="Nenhuma notícia disponível no momento." />
          ) : (
            <div className="news-grid">
              {listedNews.map((item) => (
                <NewsCard item={item} key={item.url} />
              ))}
            </div>
          )}
        </section>

        <section className="insights-section" aria-labelledby="indicators-heading">
          <InsightsHeading
            description="Dólar, índices, juros e insumos acompanhados diariamente."
            icon={LineChartIcon}
            id="indicators-heading"
            title="Indicadores de mercado"
          />

          {indicatorsAction.error ? (
            <div className="alert danger">{indicatorsAction.error}</div>
          ) : null}

          {indicatorsAction.loading && indicators.length === 0 ? (
            <LoadingState label="Carregando indicadores" />
          ) : indicators.length === 0 ? (
            <EmptyState label="Nenhum indicador disponível no momento." />
          ) : (
            <div className="indicators-grid">
              {indicators.map((item) => (
                <IndicatorCard indicator={item} key={item.codigo} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

interface InsightsHeadingProps {
  description: string;
  icon: LucideIcon;
  id: string;
  title: string;
}

function InsightsHeading({ description, icon: Icon, id, title }: InsightsHeadingProps) {
  return (
    <div className="insights-heading">
      <span className="insights-heading-icon" aria-hidden="true">
        <Icon size={17} />
      </span>
      <div>
        <h3 id={id}>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

function NewsCarousel({ items }: { items: NoticiaConstrucao[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const activeItem = items[activeIndex] ?? items[0];
  const hasMultipleItems = items.length > 1;
  const previewItems = useMemo(() => {
    if (items.length <= 1) {
      return [];
    }

    return Array.from({ length: Math.min(items.length - 1, 3) }, (_, index) => {
      return items[(activeIndex + index + 1) % items.length];
    }).filter((item): item is (typeof items)[number] => Boolean(item));
  }, [activeIndex, items]);

  useEffect(() => {
    setActiveIndex(0);
  }, [items.length]);

  useEffect(() => {
    if (items.length < 2) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % items.length);
    }, 6200);

    return () => window.clearInterval(interval);
  }, [items.length]);

  if (!activeItem) {
    return null;
  }

  const goToPrevious = () => {
    setActiveIndex((current) => (current - 1 + items.length) % items.length);
  };

  const goToNext = () => {
    setActiveIndex((current) => (current + 1) % items.length);
  };

  return (
    <div
      className={previewItems.length > 0 ? "news-carousel" : "news-carousel is-single"}
      aria-label="Destaques em movimento"
    >
      <FeaturedNewsCard item={activeItem} />

      {previewItems.length > 0 ? (
        <div className="news-carousel-aside" aria-label="Próximos destaques">
          {previewItems.map((item) => (
            <button
              className="featured-news-preview"
              key={item.url}
              onClick={() => {
                const nextIndex = items.findIndex((candidate) => candidate.url === item.url);
                if (nextIndex >= 0) {
                  setActiveIndex(nextIndex);
                }
              }}
              type="button"
            >
              <span className="news-source">{item.fonte}</span>
              <strong>{item.titulo}</strong>
              {item.resumo ? <small>{compactProjectSummary(item.resumo)}</small> : null}
            </button>
          ))}
        </div>
      ) : null}

      <div className="news-carousel-footer">
        <button
          aria-label="Destaque anterior"
          className="news-carousel-step"
          disabled={!hasMultipleItems}
          onClick={goToPrevious}
          type="button"
        >
          <ChevronLeft size={14} />
        </button>
        <div className="news-carousel-dots" aria-label="Selecionar destaque">
          {items.map((item, index) => (
            <button
              aria-label={`Selecionar destaque: ${item.titulo}`}
              aria-current={index === activeIndex ? "true" : undefined}
              className={index === activeIndex ? "is-active" : ""}
              key={item.url}
              onClick={() => setActiveIndex(index)}
              type="button"
            />
          ))}
        </div>
        <button
          aria-label="Próximo destaque"
          className="news-carousel-step"
          disabled={!hasMultipleItems}
          onClick={goToNext}
          type="button"
        >
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

function FeaturedNewsCard({ item }: { item: NoticiaConstrucao }) {
  return (
    <a
      aria-label={`${item.titulo} - abrir destaque em nova guia`}
      className="featured-news-card"
      href={item.url}
      rel="noreferrer"
      target="_blank"
    >
      <div className="news-meta">
        <span className="news-source">{item.fonte}</span>
        <span>
          <CalendarDays size={12} />
          {formatDate(item.dataPublicacao)}
        </span>
      </div>
      <h3>{item.titulo}</h3>
      {item.fonte === "Linka Engenharia" && item.resumo ? (
        <ProjectDetails summary={item.resumo} />
      ) : item.resumo ? (
        <p>{item.resumo}</p>
      ) : null}
      <span className="news-link">
        Ver destaque
        <ArrowUpRight size={14} />
      </span>
    </a>
  );
}

function ProjectDetails({ summary }: { summary: string }) {
  const details = projectSummaryParts(summary);

  if (details.length === 0) {
    return <p>{summary}</p>;
  }

  return (
    <dl className="featured-project-details">
      {details.map((detail) => (
        <div key={detail.label}>
          <dt>{detail.label}</dt>
          <dd>{detail.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function NewsCard({ item }: { item: NoticiaConstrucao }) {
  return (
    <a
      aria-label={`${item.titulo} - abrir notícia em nova guia`}
      className="news-card"
      href={item.url}
      rel="noreferrer"
      target="_blank"
    >
      <div className="news-meta">
        <span className="news-source">{item.fonte}</span>
        <span>
          <CalendarDays size={12} />
          {formatDate(item.dataPublicacao)}
        </span>
      </div>
      <h3>{item.titulo}</h3>
      {item.resumo ? <p>{item.resumo}</p> : null}
      <span className="news-link">
        Ler notícia
        <ArrowUpRight size={14} />
      </span>
    </a>
  );
}

function IndicatorCard({ indicator }: { indicator: IndicadorConstrucao }) {
  const positive = (indicator.variacao ?? 0) >= 0;
  const hasVariation = indicator.variacao !== null && indicator.variacaoSufixo !== null;
  const trendClass = hasVariation ? (positive ? "is-positive" : "is-negative") : "is-neutral";

  return (
    <article className="indicator-card">
      <div className="indicator-card-heading">
        <span>{indicator.nome}</span>
        <small>{formatReferenceDate(indicator.dataReferencia)}</small>
      </div>
      <strong className="indicator-value">{formatValue(indicator.valor, indicator.unidade)}</strong>
      <div className={`indicator-change ${trendClass}`}>
        {hasVariation ? positive ? <TrendingUp size={14} /> : <TrendingDown size={14} /> : null}
        <span>{formatVariation(indicator.variacao, indicator.variacaoSufixo)}</span>
      </div>
      <MiniChart indicator={indicator} />
      <span className="indicator-source">{indicator.fonte}</span>
    </article>
  );
}

function MiniChart({ indicator }: { indicator: IndicadorConstrucao }) {
  const path = createSparklinePath(indicator.historico.map((point) => point.valor));

  if (!path) {
    return <span className="indicator-chart-empty">Série histórica indisponível</span>;
  }

  const positive = (indicator.variacao ?? 0) >= 0;

  return (
    <div className="indicator-chart" aria-hidden="true">
      <svg focusable="false" preserveAspectRatio="none" viewBox="0 0 120 38">
        <path className={positive ? "is-positive" : "is-negative"} d={path} />
      </svg>
    </div>
  );
}

function createSparklinePath(values: number[]) {
  const finiteValues = values.filter(Number.isFinite);
  if (finiteValues.length < 2) {
    return null;
  }

  const width = 120;
  const height = 38;
  const padding = 2;
  const minimum = Math.min(...finiteValues);
  const maximum = Math.max(...finiteValues);
  const range = maximum - minimum;

  return finiteValues
    .map((value, index) => {
      const x = padding + (index / (finiteValues.length - 1)) * (width - padding * 2);
      const y =
        range === 0 ? height / 2 : padding + ((maximum - value) / range) * (height - padding * 2);

      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");
}

function LoadingState({ label }: { label: string }) {
  return (
    <div className="insights-state" role="status">
      <Loader2 className="spin" size={17} />
      <span>{label}</span>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return <div className="insights-state">{label}</div>;
}

function projectSummaryParts(summary: string) {
  const matches = Array.from(
    summary.matchAll(
      /(Incorporação|Construção|Arquitetura):\s*(.*?)(?=\s(?:Incorporação|Construção|Arquitetura):|$)/g,
    ),
  );

  return matches
    .map((match) => ({
      label: match[1] ?? "",
      value: (match[2] ?? "").trim(),
    }))
    .filter((detail) => detail.label && detail.value);
}

function compactProjectSummary(summary: string) {
  const details = projectSummaryParts(summary);
  const architecture = details.find((detail) => detail.label === "Arquitetura");
  const incorporation = details.find((detail) => detail.label === "Incorporação");
  const selected = architecture ?? incorporation;

  return selected ? `${selected.label}: ${selected.value}` : summary;
}

function formatDate(value: string | null) {
  if (!value) {
    return "Destaque";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Destaque";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function formatReferenceDate(value: string | null) {
  if (!value) {
    return "Sem referência";
  }

  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    month: "short",
    year: "numeric",
  }).format(date);
}

function formatValue(value: number, unit: string | null) {
  if (unit === "R$") {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  }

  const formatted = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);

  if (!unit) {
    return formatted;
  }

  return unit.startsWith("%") ? `${formatted}${unit}` : `${formatted} ${unit}`;
}

function formatVariation(value: number | null, suffix: string | null) {
  if (value === null || suffix === null) {
    return "Sem histórico suficiente";
  }

  const formatted = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: "exceptZero",
  }).format(value);

  return `${formatted} ${suffix}`;
}
