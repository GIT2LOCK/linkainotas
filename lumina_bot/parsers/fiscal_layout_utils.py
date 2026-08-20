"""Small, deterministic helpers shared by the supported fiscal layouts."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from difflib import SequenceMatcher
from typing import Any

from lumina_bot.models.nota import NotaFiscal
from lumina_bot.models.validation import ValidationResult
from lumina_bot.parsers.base_parser import ParseContext
from lumina_bot.core.pdf_reader import PdfWord


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
    if nota.ocr_used and confidence >= 1.0:
        # OCR fields remain medium confidence until a format or consistency
        # rule confirms them; recognition alone is never high confidence.
        confidence = 0.65
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


def word_value_after_label(
    words: Sequence[PdfWord],
    label: str,
    *,
    min_y: float = 0,
    max_y: float | None = None,
    occurrence: int = 0,
    join_same_row: bool = False,
    prefer_numeric: bool = True,
) -> str | None:
    """Read a value aligned below a PDF label using word coordinates.

    PDF text extraction commonly emits all labels first and all values later.
    This helper avoids using global line order for those tables.
    """
    wanted = [compact(token) for token in normalize_text(label).split()]
    if not wanted:
        return None
    normalized_words = [compact(word.text) for word in words]
    matches: list[tuple[int, int]] = []
    match_indexes: dict[tuple[int, int], list[int]] = {}
    for index, value in enumerate(normalized_words):
        if value != wanted[0]:
            continue
        if len(wanted) == 1:
            match = (index, index)
            matches.append(match)
            match_indexes[match] = [index]
            continue
        end_index = index
        for offset, expected in enumerate(wanted[1:], start=1):
            next_index = index + offset
            if next_index >= len(words):
                break
            if words[next_index].page != words[index].page:
                break
            if abs(words[next_index].y0 - words[index].y0) > 4:
                break
            if normalized_words[next_index] != expected:
                break
            end_index = next_index
        else:
            match = (index, end_index)
            matches.append(match)
            match_indexes[match] = list(range(index, end_index + 1))
    if not matches:
        # The first token of a label can be joined to punctuation by a PDF
        # extractor; retry using the complete normalized row text.
        rows: dict[tuple[int, int], list[int]] = {}
        for index, word in enumerate(words):
            rows.setdefault((word.page, round(word.y0 / 3)), []).append(index)
        for indexes in rows.values():
            indexes.sort(key=lambda item: words[item].x0)
            target = compact(label)
            for start_position, start_item in enumerate(indexes):
                prefix = ""
                label_end = start_item
                for item in indexes[start_position:]:
                    prefix += compact(words[item].text)
                    label_end = item
                    candidate = prefix[: len(target) + 3]
                    if target in prefix or (
                        len(prefix) >= max(4, len(target) - 2)
                        and SequenceMatcher(None, target, candidate).ratio() >= 0.78
                    ):
                        match = (start_item, label_end)
                        matches.append(match)
                        match_indexes[match] = list(indexes[start_position:indexes.index(item) + 1])
                        break
    if not matches:
        return None

    filtered = [match for match in matches if words[match[0]].y0 >= min_y and (max_y is None or words[match[0]].y0 <= max_y)]
    if not filtered:
        return None
    start, end = filtered[min(occurrence, len(filtered) - 1)]
    selected_indexes = match_indexes.get((start, end), list(range(min(start, end), max(start, end) + 1)))
    label_words = tuple(words[index] for index in selected_indexes)
    label_indexes = set(selected_indexes)
    anchor_index = selected_indexes[0]
    label_center = (min(word.x0 for word in label_words) + max(word.x1 for word in label_words)) / 2
    label_bottom = max(word.y1 for word in label_words)
    label_right = max(word.x1 for word in label_words)
    noise_tokens = {
        "", "r", "rs", "r$", "valor", "vlr", "base", "aliquota", "iss",
        "ibs", "cbs", "inss", "irrf", "cofins", "pis", "retido", "nota",
        "calculo", "clculo", "do", "de", "alquota", "lquido", "liquido", "da",
        "csll", "outras", "retencoes", "substituio", "substituicao", "icms", "ipi", "total", "seguro",
        "desconto", "despesas", "acessrias", "acessorias", "cdigo", "codigo", "antt", "espcie", "especie", "marca",
        "numerao", "numeracao", "placa", "pso", "peso", "bruto", "veiculo", "(r$)", "(%)",
    }

    # Some municipal layouts print the value on the same baseline, while
    # columnar tables print it immediately below the header. Prefer the
    # same-row value when it is clearly to the right of the label.
    same_row = [
        (index, word)
        for index, word in enumerate(words)
        if index not in label_indexes
        and word.page == words[anchor_index].page
        and abs(word.y0 - words[anchor_index].y0) <= 3
        and word.x0 >= label_right - 1
        and word.x0 <= label_right + 180
        and compact(word.text) not in noise_tokens
        and not word.text.strip().startswith(("=", "(", ")"))
    ]
    if same_row:
        same_row.sort(key=lambda pair: (abs(pair[1].x0 - label_right), pair[1].x0))
        if join_same_row:
            same_row.sort(key=lambda pair: pair[1].x0)
            return " ".join(pair[1].text.strip() for pair in same_row)
        return same_row[0][1].text.strip()

    candidates = [
        word for index, word in enumerate(words)
        if index not in label_indexes
        and word.page == words[anchor_index].page
        and word.y0 >= label_bottom - 1
        and word.y0 <= label_bottom + 32
        and abs(((word.x0 + word.x1) / 2) - label_center) <= 125
    ]
    if not candidates:
        return None
    numeric_candidates = [word for word in candidates if re.search(r"\d", word.text)]
    aligned_numeric = [word for word in numeric_candidates if abs(word.x0 - label_right) <= 12]
    label_compact = compact(label)
    right_numeric = [word for word in numeric_candidates if word.x0 >= label_right - 1]
    if not prefer_numeric:
        pass
    elif label_compact.startswith(("valortotaldosprodutos", "valortotaldanota")) and numeric_candidates:
        candidates = [max(numeric_candidates, key=lambda word: word.x0)]
    elif label_compact.startswith("vlr") and right_numeric:
        candidates = right_numeric
    elif aligned_numeric:
        candidates = aligned_numeric
    elif numeric_candidates:
        candidates = numeric_candidates
    candidates.sort(key=lambda word: (word.y0, abs(((word.x0 + word.x1) / 2) - label_center)))
    return candidates[0].text.strip()
