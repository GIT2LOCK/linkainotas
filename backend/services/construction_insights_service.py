"""Construction news and market indicators for the LinkAI home page."""

from __future__ import annotations

import gzip
import html
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from threading import RLock
from time import monotonic
from typing import Any, ClassVar
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from lumina_bot.core.logger import get_logger


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    value: Any
    expires_at: float


class _PlainTextParser(HTMLParser):
    """Extract readable text from RSS and article snippets."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return " ".join(" ".join(self.parts).split())


class ConstructionInsightsService:
    """Load daily construction-sector news, indicators, and market quotes."""

    _CBIC_FEED_URL = "https://cbic.org.br/feed/"
    _INFOMONEY_COMMODITIES_FEED_URL = "https://www.infomoney.com.br/tudo-sobre/commodities/feed/"
    _LINKA_OBRAS_URL = "https://linka.eng.br/obras/"
    _JORNAL_CONSTRUCAO_URL = "https://jornaldaconstrucaocivil.com.br/"
    _SGS_URL_TEMPLATE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{limit}?formato=json"
    _YAHOO_CHART_URL_TEMPLATE = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=1d"
    _CACHE_SECONDS = 24 * 60 * 60
    _TONS_PER_POUND = 2204.62262185
    _NEWS_SOURCE_QUOTAS: ClassVar[tuple[tuple[str, int], ...]] = (
        ("Linka Engenharia", 4),
        ("Jornal da Construção Civil", 3),
        ("CBIC", 3),
        ("InfoMoney (Commodities)", 2),
    )
    _CONSTRUCTION_MARKET_TERMS: ClassVar[tuple[str, ...]] = (
        "alumínio",
        "aluminio",
        "aço",
        "aco",
        "brent",
        "cimento",
        "cobre",
        "commodit",
        "constru",
        "dólar",
        "dolar",
        "energia",
        "ferro",
        "imóvel",
        "imovel",
        "infraestrutura",
        "minério",
        "minerio",
        "obra",
        "petróleo",
        "petroleo",
    )
    _POSITIVE_NEWS_TERMS: ClassVar[tuple[str, ...]] = (
        "abre inscrições",
        "alta",
        "amplia",
        "avanço",
        "avanca",
        "capacitação",
        "capacitacao",
        "cresce",
        "crescimento",
        "desenvolvimento",
        "eficiência",
        "eficiencia",
        "estágio",
        "estagio",
        "evolução",
        "evolucao",
        "expansão",
        "expansao",
        "habitação",
        "habitacao",
        "iniciativa",
        "inovação",
        "inovacao",
        "investimento",
        "modernização",
        "modernizacao",
        "oportunidade",
        "parceria",
        "planejamento",
        "promove",
        "projeto",
        "qualidade",
        "segurança",
        "seguranca",
        "sustentabilidade",
        "tecnologia",
        "trilhas profissionais",
        "vagas",
    )
    _NEGATIVE_NEWS_TERMS: ClassVar[tuple[str, ...]] = (
        "acidente",
        "assusta",
        "atraso",
        "calote",
        "crise",
        "desabamento",
        "desastre",
        "despenca",
        "escassez",
        "fechado",
        "fechamento",
        "guerra",
        "incêndio",
        "incendio",
        "irã",
        "ira",
        "morte",
        "pesadelo",
        "queda",
        "preocup",
        "recua",
        "recuo",
        "restring",
        "risco",
        "violência",
        "violencia",
    )
    _cache: ClassVar[dict[str, _CacheEntry]] = {}
    _cache_lock: ClassVar[RLock] = RLock()

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)

    def recent_news(self, limit: int = 6, *, force: bool = False) -> list[dict[str, Any]]:
        """Return daily news from the visible construction/market source groups."""
        safe_limit = max(1, min(limit, 20))
        news = self._cached_or_load("construction-news-daily", self._fetch_news, force=force)
        return [dict(item) for item in news[:safe_limit]]

    def indicator_panel(self, *, force: bool = False) -> dict[str, Any]:
        """Return current market indicators and quotes used by construction teams."""
        panel = self._cached_or_load(
            "construction-indicators-daily",
            self._fetch_indicator_panel,
            force=force,
        )
        return dict(panel)

    def _cached_or_load(
        self,
        key: str,
        loader: Callable[[], Any],
        *,
        force: bool,
    ) -> Any:
        now = monotonic()

        with self._cache_lock:
            cached = self._cache.get(key)

        if cached and not force and cached.expires_at > now:
            return cached.value

        try:
            value = loader()
        except Exception as exc:
            if cached:
                self._logger.warning("Unable to refresh %s; using stale cache: %s", key, exc)
                return cached.value
            self._logger.warning("Unable to load %s: %s", key, exc)
            raise RuntimeError("Não foi possível atualizar os dados externos.") from exc

        with self._cache_lock:
            self._cache[key] = _CacheEntry(
                value=value,
                expires_at=now + self._CACHE_SECONDS,
            )

        return value

    def _fetch_news(self) -> list[dict[str, Any]]:
        sources: tuple[tuple[str, Callable[[], list[dict[str, Any]]]], ...] = (
            (
                "Linka Engenharia",
                lambda: self._fetch_linka_obras(limit=8),
            ),
            (
                "InfoMoney (Commodities)",
                lambda: self._fetch_rss_news(
                    self._INFOMONEY_COMMODITIES_FEED_URL,
                    "InfoMoney (Commodities)",
                    limit=8,
                    prefer_relevant=True,
                ),
            ),
            (
                "CBIC",
                lambda: self._fetch_rss_news(self._CBIC_FEED_URL, "CBIC", limit=8),
            ),
            (
                "Jornal da Construção Civil",
                lambda: self._fetch_jornal_construcao_news(limit=8),
            ),
        )
        by_source: dict[str, list[dict[str, Any]]] = {}

        for source, loader in sources:
            try:
                by_source[source] = loader()
            except Exception as exc:
                self._logger.warning("Unable to load news from %s: %s", source, exc)
                by_source[source] = []

        selected: list[dict[str, Any]] = []
        selected_urls: set[str] = set()

        for source, quota in self._NEWS_SOURCE_QUOTAS:
            for item in by_source.get(source, [])[:quota]:
                url = str(item.get("url") or "")
                if url and url not in selected_urls:
                    selected.append(item)
                    selected_urls.add(url)

        remaining = [
            item
            for items in by_source.values()
            for item in items
            if str(item.get("url") or "") not in selected_urls
        ]
        remaining.sort(key=self._news_sort_key, reverse=True)

        if not selected:
            raise RuntimeError("As fontes de notícias não retornaram publicações.")

        return (selected + remaining)[:20]

    def _fetch_rss_news(
        self,
        url: str,
        source: str,
        *,
        limit: int,
        prefer_relevant: bool = False,
    ) -> list[dict[str, Any]]:
        root = ElementTree.fromstring(self._fetch_bytes(url, "application/rss+xml"))
        all_items: list[dict[str, Any]] = []
        relevant_items: list[dict[str, Any]] = []

        for item in root.findall("./channel/item"):
            title = self._item_text(item, "title")
            link = self._item_text(item, "link")

            if not title or not link:
                continue

            description = self._item_text(item, "description") or self._child_text_by_suffix(item, "encoded")
            summary = self._summary(description)
            if self._is_negative_news(f"{title} {summary or ''}"):
                continue

            news_item = {
                "titulo": title,
                "resumo": summary,
                "fonte": source,
                "url": link,
                "dataPublicacao": self._published_at(self._item_text(item, "pubDate")),
            }
            all_items.append(news_item)

            if self._is_construction_market_relevant(f"{title} {summary or ''}"):
                relevant_items.append(news_item)

            if len(all_items) >= limit * 2:
                break

        if prefer_relevant and not relevant_items:
            return []

        items = relevant_items if prefer_relevant else all_items
        positive_items = [
            item
            for item in items
            if self._is_positive_news(f"{item.get('titulo') or ''} {item.get('resumo') or ''}")
        ]
        if positive_items:
            items = positive_items

        return items[:limit]

    def _fetch_linka_obras(self, *, limit: int) -> list[dict[str, Any]]:
        page = self._fetch_text(self._LINKA_OBRAS_URL, "text/html")
        ctas = re.findall(
            r"<a\s+class=\"elementor-cta\"\s+href=\"([^\"]+)\".*?"
            r"<h3[^>]*class=\"[^\"]*elementor-cta__title[^\"]*\"[^>]*>(.*?)</h3>.*?"
            r"<div[^>]*class=\"[^\"]*elementor-cta__description[^\"]*\"[^>]*>(.*?)</div>",
            page,
            flags=re.IGNORECASE | re.DOTALL,
        )
        news: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for raw_url, raw_title, raw_description in ctas:
            item_url = html.unescape(raw_url).strip()
            title = self._html_text(raw_title)
            summary = self._summary(raw_description)

            if not item_url or item_url in seen_urls or not title:
                continue

            news.append(
                {
                    "titulo": title,
                    "resumo": summary,
                    "fonte": "Linka Engenharia",
                    "url": item_url,
                    "dataPublicacao": None,
                }
            )
            seen_urls.add(item_url)

            if len(news) >= limit:
                break

        if not news:
            raise RuntimeError("A página de obras da Linka não retornou destaques.")

        return news

    def _fetch_jornal_construcao_news(self, *, limit: int) -> list[dict[str, Any]]:
        page = self._fetch_text(self._JORNAL_CONSTRUCAO_URL, "text/html")
        articles = re.findall(r"<article\b.*?</article>", page, flags=re.IGNORECASE | re.DOTALL)
        news: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for article in articles:
            title_match = re.search(
                r"<h[1-3][^>]*>.*?<a\s+href=\"([^\"]+)\"[^>]*>(.*?)</a>",
                article,
                flags=re.IGNORECASE | re.DOTALL,
            )

            if not title_match:
                title_match = re.search(
                    r"<a[^>]+aria-label=\"([^\"]+)\"[^>]+href=\"([^\"]+)\"",
                    article,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                if not title_match:
                    continue
                raw_title, raw_url = title_match.group(1), title_match.group(2)
            else:
                raw_url, raw_title = title_match.group(1), title_match.group(2)

            title = self._html_text(raw_title)
            item_url = html.unescape(raw_url).strip()

            if not title or not item_url or item_url in seen_urls:
                continue

            summary_match = re.search(
                r"<div[^>]+class=\"[^\"]*ct-dynamic-data[^\"]*\"[^>]*>\s*<p>(.*?)</p>",
                article,
                flags=re.IGNORECASE | re.DOTALL,
            )
            date_match = re.search(
                r"<time[^>]+datetime=\"([^\"]+)\"",
                article,
                flags=re.IGNORECASE | re.DOTALL,
            )
            summary = self._summary(summary_match.group(1) if summary_match else "")

            if self._is_negative_news(f"{title} {summary or ''}"):
                continue

            news.append(
                {
                    "titulo": title,
                    "resumo": summary,
                    "fonte": "Jornal da Construção Civil",
                    "url": item_url,
                    "dataPublicacao": self._iso_datetime(date_match.group(1) if date_match else ""),
                }
            )
            seen_urls.add(item_url)

            if len(news) >= limit:
                break

        if not news:
            raise RuntimeError("A página do Jornal da Construção Civil não retornou publicações.")

        return news

    def _fetch_indicator_panel(self) -> dict[str, Any]:
        indicator_loaders: tuple[Callable[[], dict[str, Any]], ...] = (
            self._dollar_ptax_indicator,
            self._incc_monthly_indicator,
            self._incc_twelve_month_indicator,
            self._igpm_monthly_indicator,
            self._ipca_monthly_indicator,
            self._aluminum_quote_indicator,
            self._copper_quote_indicator,
            self._cdi_annualized_indicator,
            self._brent_quote_indicator,
        )
        indicators: list[dict[str, Any]] = []

        for loader in indicator_loaders:
            try:
                indicators.append(loader())
            except Exception as exc:
                self._logger.warning("Unable to load indicator %s: %s", loader.__name__, exc)

        if not indicators:
            raise RuntimeError("Nenhum indicador de mercado foi retornado.")

        return {
            "indicadores": indicators,
            "atualizadoEm": datetime.now(UTC).isoformat(),
        }

    def _dollar_ptax_indicator(self) -> dict[str, Any]:
        return self._series_indicator(
            code="dolar-ptax",
            name="Dólar (PTAX)",
            unit="R$",
            source="BCB SGS",
            values=self._fetch_sgs_series(1, 10),
            change_mode="percent",
        )

    def _incc_monthly_indicator(self) -> dict[str, Any]:
        return self._series_indicator(
            code="incc-di-mensal",
            name="INCC-DI (variação mensal)",
            unit="% a.m.",
            source="BCB / FGV",
            values=self._fetch_sgs_series(192, 18),
            change_mode="delta",
        )

    def _incc_twelve_month_indicator(self) -> dict[str, Any]:
        values = self._rolling_compounded_percent(self._fetch_sgs_series(192, 18), window=12)
        return self._series_indicator(
            code="incc-di-12m",
            name="INCC-DI (acumulado 12 meses)",
            unit="% 12m",
            source="BCB / FGV",
            values=values,
            change_mode="delta",
        )

    def _igpm_monthly_indicator(self) -> dict[str, Any]:
        return self._series_indicator(
            code="igp-m-mensal",
            name="IGP-M (variação mensal)",
            unit="% a.m.",
            source="BCB / FGV",
            values=self._fetch_sgs_series(189, 18),
            change_mode="delta",
        )

    def _ipca_monthly_indicator(self) -> dict[str, Any]:
        return self._series_indicator(
            code="ipca-mensal",
            name="IPCA (variação mensal)",
            unit="% a.m.",
            source="BCB / IBGE",
            values=self._fetch_sgs_series(433, 18),
            change_mode="delta",
        )

    def _aluminum_quote_indicator(self) -> dict[str, Any]:
        return self._quote_indicator(
            code="aluminio",
            name="Alumínio",
            unit="USD/tonelada",
            source="Yahoo Finance / COMEX",
            values=self._fetch_yahoo_history("ALI=F"),
        )

    def _copper_quote_indicator(self) -> dict[str, Any]:
        return self._quote_indicator(
            code="cobre",
            name="Cobre",
            unit="USD/tonelada",
            source="Yahoo Finance / COMEX",
            values=self._fetch_yahoo_history(
                "HG=F",
                transform=lambda value: value * self._TONS_PER_POUND,
            ),
        )

    def _cdi_annualized_indicator(self) -> dict[str, Any]:
        return self._series_indicator(
            code="cdi-anualizado",
            name="CDI (anualizado)",
            unit="% a.a.",
            source="BCB SGS",
            values=self._fetch_sgs_series(4389, 10),
            change_mode="delta",
        )

    def _brent_quote_indicator(self) -> dict[str, Any]:
        return self._quote_indicator(
            code="petroleo-brent",
            name="Petróleo (Brent)",
            unit="USD/barril",
            source="Yahoo Finance / NYMEX",
            values=self._fetch_yahoo_history("BZ=F"),
        )

    def _fetch_sgs_series(self, code: int, limit: int) -> list[tuple[str, float]]:
        url = self._SGS_URL_TEMPLATE.format(code=code, limit=limit)
        payload = json.loads(self._fetch_bytes(url, "application/json"))

        if not isinstance(payload, list):
            raise RuntimeError(f"Série SGS {code} retornou formato inesperado.")

        values: list[tuple[str, float]] = []
        for point in payload:
            if not isinstance(point, dict):
                continue

            try:
                date = datetime.strptime(str(point["data"]), "%d/%m/%Y").date().isoformat()
                value = float(str(point["valor"]).replace(",", "."))
            except (KeyError, TypeError, ValueError):
                continue

            values.append((date, value))

        values.sort(key=lambda item: item[0])

        if len(values) < 2:
            raise RuntimeError(f"Série SGS {code} sem histórico suficiente.")

        return values

    def _fetch_yahoo_history(
        self,
        symbol: str,
        *,
        transform: Callable[[float], float] | None = None,
    ) -> list[tuple[str, float]]:
        url = self._YAHOO_CHART_URL_TEMPLATE.format(symbol=quote(symbol, safe=""))
        payload = json.loads(self._fetch_bytes(url, "application/json"))

        result = payload.get("chart", {}).get("result")
        if not isinstance(result, list) or not result:
            raise RuntimeError(f"Cotação {symbol} não retornou histórico.")

        first_result = result[0]
        timestamps = first_result.get("timestamp")
        quotes = first_result.get("indicators", {}).get("quote")

        if not isinstance(timestamps, list) or not isinstance(quotes, list) or not quotes:
            raise RuntimeError(f"Cotação {symbol} retornou formato inesperado.")

        closes = quotes[0].get("close")
        if not isinstance(closes, list):
            raise RuntimeError(f"Cotação {symbol} sem série de fechamento.")

        values: list[tuple[str, float]] = []
        for timestamp, close in zip(timestamps, closes, strict=False):
            if close is None:
                continue

            try:
                date = datetime.fromtimestamp(int(timestamp), UTC).date().isoformat()
                value = float(close)
            except (TypeError, ValueError, OSError):
                continue

            if transform:
                value = transform(value)

            values.append((date, value))

        values.sort(key=lambda item: item[0])

        if len(values) < 2:
            raise RuntimeError(f"Cotação {symbol} sem histórico suficiente.")

        return values

    def _series_indicator(
        self,
        *,
        code: str,
        name: str,
        unit: str,
        source: str,
        values: list[tuple[str, float]],
        change_mode: str,
    ) -> dict[str, Any]:
        change = self._latest_delta(values) if change_mode == "delta" else self._latest_percent(values)
        suffix = "p.p." if change_mode == "delta" else "%"
        return self._indicator(
            code=code,
            name=name,
            unit=unit,
            values=values,
            source=source,
            change=change,
            change_suffix=suffix,
        )

    def _quote_indicator(
        self,
        *,
        code: str,
        name: str,
        unit: str,
        source: str,
        values: list[tuple[str, float]],
    ) -> dict[str, Any]:
        return self._indicator(
            code=code,
            name=name,
            unit=unit,
            values=values,
            source=source,
            change=self._latest_percent(values),
            change_suffix="%",
        )

    @staticmethod
    def _indicator(
        *,
        code: str,
        name: str,
        unit: str,
        values: list[tuple[str, float]],
        source: str,
        change: float | None,
        change_suffix: str,
    ) -> dict[str, Any]:
        latest_period, latest_value = values[-1]
        return {
            "codigo": code,
            "nome": name,
            "valor": round(latest_value, 2),
            "unidade": unit,
            "dataReferencia": latest_period,
            "fonte": source,
            "variacao": round(change, 2) if change is not None else None,
            "variacaoSufixo": change_suffix,
            "historico": [
                {
                    "valor": round(value, 2),
                    "dataReferencia": period,
                }
                for period, value in values[-18:]
            ],
        }

    @staticmethod
    def _rolling_compounded_percent(
        values: list[tuple[str, float]],
        *,
        window: int,
    ) -> list[tuple[str, float]]:
        if len(values) < window:
            raise RuntimeError("Histórico insuficiente para acumulado em 12 meses.")

        rolling: list[tuple[str, float]] = []
        for index in range(window - 1, len(values)):
            compound = 1.0
            for _, value in values[index - window + 1 : index + 1]:
                compound *= 1 + value / 100

            rolling.append((values[index][0], (compound - 1) * 100))

        return rolling

    @staticmethod
    def _latest_delta(values: list[tuple[str, float]]) -> float | None:
        if len(values) < 2:
            return None
        return values[-1][1] - values[-2][1]

    @staticmethod
    def _latest_percent(values: list[tuple[str, float]]) -> float | None:
        if len(values) < 2 or values[-2][1] == 0:
            return None
        return ((values[-1][1] - values[-2][1]) / abs(values[-2][1])) * 100

    @staticmethod
    def _news_sort_key(item: dict[str, Any]) -> str:
        return str(item.get("dataPublicacao") or "")

    @classmethod
    def _is_construction_market_relevant(cls, value: str) -> bool:
        normalized = value.casefold()
        return any(term in normalized for term in cls._CONSTRUCTION_MARKET_TERMS)

    @classmethod
    def _is_positive_news(cls, value: str) -> bool:
        normalized = value.casefold()
        return any(term in normalized for term in cls._POSITIVE_NEWS_TERMS)

    @classmethod
    def _is_negative_news(cls, value: str) -> bool:
        normalized = value.casefold()
        return any(term in normalized for term in cls._NEGATIVE_NEWS_TERMS)

    @staticmethod
    def _item_text(item: ElementTree.Element, tag: str) -> str:
        return " ".join((item.findtext(tag) or "").split())

    @staticmethod
    def _child_text_by_suffix(item: ElementTree.Element, suffix: str) -> str:
        for child in item:
            if child.tag.casefold().endswith(suffix.casefold()):
                return " ".join((child.text or "").split())
        return ""

    @classmethod
    def _summary(cls, raw_html: str) -> str | None:
        if not raw_html:
            return None

        text = cls._html_text(raw_html)

        if not text:
            return None

        normalized = text.casefold()
        if normalized.startswith("the post ") and " appeared first on " in normalized:
            return None

        if len(text) <= 180:
            return text

        shortened = text[:177].rsplit(" ", 1)[0]
        return f"{shortened}..."

    @staticmethod
    def _html_text(raw_html: str) -> str:
        parser = _PlainTextParser()
        parser.feed(html.unescape(raw_html))
        return (
            parser.text()
            .replace("\u200b", "")
            .replace("\u200c", "")
            .replace("\u200d", "")
            .replace("\xa0", " ")
        )

    @staticmethod
    def _published_at(value: str) -> str | None:
        if not value:
            return None

        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC).isoformat()

    @staticmethod
    def _iso_datetime(value: str) -> str | None:
        if not value:
            return None

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC).isoformat()

    @classmethod
    def _fetch_text(cls, url: str, accept: str) -> str:
        return cls._fetch_bytes(url, accept).decode("utf-8", errors="replace")

    @staticmethod
    def _fetch_bytes(url: str, accept: str) -> bytes:
        request = Request(
            url,
            headers={
                "Accept": accept,
                "Accept-Encoding": "gzip",
                "User-Agent": "LinkAI/0.3 Mozilla/5.0",
            },
        )

        with urlopen(request, timeout=12) as response:
            payload = response.read()
            content_encoding = response.headers.get("Content-Encoding", "").lower()

        if content_encoding == "gzip" or payload.startswith(b"\x1f\x8b"):
            return gzip.decompress(payload)

        return payload
