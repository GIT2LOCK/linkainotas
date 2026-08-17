"""Small, deterministic helpers shared by the supported fiscal layouts."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from typing import Any

from lumina_bot.models.nota import NotaFiscal
from lumina_bot.models.validation import ValidationResult
from lumina_bot.parsers.base_parser import ParseContext


def normalize_text(value: str | None) -> str:
    """Normalize labels while tolerating replacement characters in PDF text."""
    if not value:
        return ""

    value = value.replace("\xa0", " ").replace("�", "")
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^a-z0-9%/.,:+#-]+", " ", value).split())


def compact(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", normalize_text(value))


def context_lines(context: ParseContext, page: int | None = None) -> list[str]:
    """Return non-empty lines, preferably preserving the original page split."""
    if page is not None and context.pdf.pages and 1 <= page <= len(context.pdf.pages):
        source = context.pdf.pages[page - 1]
    else:
        source = context.text

    return [line.strip() for line in source.splitlines() if line.strip()]


def all_pages(context: ParseContext) -> list[list[str]]:
    if context.pdf.pages:
        return [context_lines(context, index) for index in range(1, len(context.pdf.pages) + 1)]
    return [context_lines(context)]


def find_index(lines: Sequence[str], *labels: str, start: int = 0) -> int | None:
    wanted = [compact(label) for label in labels]
    for index in range(start, len(lines)):
        line = compact(lines[index])
        if any(label and label in line for label in wanted):
            return index
    return None


def value_after(
    lines: Sequence[str],
    *labels: str,
    start: int = 0,
    skip: Iterable[str] = (),
) -> str | None:
    """Read a label's same-line value or the next meaningful line."""
    index = find_index(lines, *labels, start=start)
    if index is None:
        return None

    line = lines[index]
    normalized = normalize_text(line)
    for label in labels:
        normalized_label = normalize_text(label)
        position = normalized.find(normalized_label)
        if position >= 0:
            suffix = normalized[position + len(normalized_label):].strip(" :;-=")
            if suffix:
                return suffix

    blocked = {compact(item) for item in skip}
    for candidate in lines[index + 1:]:
        if compact(candidate) in blocked:
            continue
        return candidate.strip()
    return None


def values_after(lines: Sequence[str], index: int, count: int) -> list[str]:
    """Return the next numeric-looking values after a grouped label block."""
    values: list[str] = []
    for candidate in lines[index + 1:]:
        if re.search(r"-?\d[\d.,]*", candidate):
            values.append(candidate.strip())
        if len(values) >= count:
            break
    return values


def first_match(pattern: str, text: str, flags: int = re.IGNORECASE | re.MULTILINE) -> str | None:
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def digits(value: str | None) -> str | None:
    if not value:
        return None
    result = re.sub(r"\D", "", value)
    return result or None


def decimal(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"-?\d[\d.,]*", value)
    if not match:
        return None

    number = match.group(0)
    if "," in number and "." in number:
        number = number.replace(".", "").replace(",", ".") if number.rfind(",") > number.rfind(".") else number.replace(",", "")
    elif "," in number:
        number = number.replace(".", "").replace(",", ".")
    elif number.count(".") > 1:
        number = number.replace(".", "")
    elif "." in number:
        integer, fraction = number.split(".", 1)
        if len(fraction) == 3 and len(integer.lstrip("-")) <= 3:
            number = integer + fraction

    try:
        return float(number)
    except ValueError:
        return None


def iso_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", value)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    return value.strip()


def first_cnpj(text: str) -> str | None:
    match = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", text)
    return match.group(0) if match else None


def all_cnpjs(text: str) -> list[str]:
    return re.findall(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", text)


def record_field(
    nota: NotaFiscal,
    name: str,
    value: Any,
    *,
    raw: str | None = None,
    page: int | None = None,
    confidence: float = 1.0,
) -> None:
    """Keep provenance beside the normalized value without changing the public model."""
    sources = nota.outros_campos.setdefault("fontes", {})
    if not isinstance(sources, dict):
        sources = {}
        nota.outros_campos["fontes"] = sources
    sources[name] = {
        "raw": raw if raw is not None else value,
        "pagina": page,
        "confidence": confidence,
    }


def add_validation(
    nota: NotaFiscal,
    regra: str,
    status: str,
    *,
    extracted: Any = None,
    calculated: Any = None,
    message: str | None = None,
) -> None:
    nota.validacoes.append(
        ValidationResult(
            regra=regra,
            status=status,
            valor_extraido=extracted,
            valor_calculado=calculated,
            mensagem=message,
        )
    )
