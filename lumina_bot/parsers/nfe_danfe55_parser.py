"""Parser for one-page DANFE NF-e model 55 PDFs."""

from __future__ import annotations

import re

from lumina_bot.core.document_detector import DocumentType
from lumina_bot.models.item import Item
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.models.parcela import Parcela
from lumina_bot.parsers.base_parser import BaseParser, ParseContext
from lumina_bot.parsers.fiscal_layout_utils import (
    add_validation,
    all_cnpjs,
    all_pages,
    context_lines,
    decimal,
    digits,
    first_match,
    iso_date,
    normalize_text,
    record_field,
    value_after,
)


class NfeDanfe55Parser(BaseParser):
    """Extract the stable fields and product table from a DANFE."""

    document_type = DocumentType.NFE_DANFE_55
    parser_name = "nfe_danfe55_parser"

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        pages = all_pages(context)
        lines = pages[0] if pages else context_lines(context)
        text = "\n".join("\n".join(page) for page in pages) or context.text

        nota.tipo_documento = DocumentType.NFE_DANFE_55.value
        nota.layout = DocumentType.NFE_DANFE_55.value
        nota.modelo = "55"
        self._parse_identity(nota, lines, text)
        self._parse_parties(nota, lines, text)
        self._parse_dates_and_protocol(nota, lines, text)
        self._parse_installments(nota, lines)
        self._parse_totals(nota, lines)
        self._parse_item(nota, lines)
        self._parse_transport(nota, lines)
        self._parse_additional(nota, lines)
        self._validate(nota)
        nota.outros_campos["fonte_prioritaria"] = "xml" if context.xml_text else "pdf_text"

    def _parse_identity(self, nota: NotaFiscal, lines: list[str], text: str) -> None:
        compact_key = digits(first_match(r"(?mi)^\s*([0-9 ]{44,55})\s*$", text))
        if compact_key and len(compact_key) >= 44:
            nota.chave = compact_key[:44]
            record_field(nota, "chave", nota.chave, raw=compact_key, page=1)

        number = first_match(r"(?mi)^n[^\n\d]{0,4}([0-9]{3}\.[0-9]{3}\.[0-9]{3})$", "\n".join(lines))
        if number:
            nota.numero = number.replace(".", "")
            record_field(nota, "numero", nota.numero, raw=number, page=1)

        series = first_match(r"(?mi)^s[ée]rie\s+([0-9]+)$", "\n".join(lines))
        if series:
            nota.serie = series
        nota.outros_campos["tipo_operacao"] = value_after(lines, "0 - entrada") or value_after(lines, "natureza da operacao")
        nota.outros_campos["natureza_operacao"] = value_after(lines, "natureza da operacao")

    def _parse_parties(self, nota: NotaFiscal, lines: list[str], text: str) -> None:
        cnpjs = list(dict.fromkeys(all_cnpjs(text)))
        if cnpjs:
            nota.prestador.cnpj = cnpjs[0]
        if len(cnpjs) > 1:
            nota.tomador.cnpj = cnpjs[1]

        danfe_index = self._find(lines, "danfe")
        destination_index = self._find(lines, "destinatario remetente")
        issuer_segment = lines[danfe_index + 1:destination_index] if danfe_index is not None and destination_index is not None else lines
        issuer_name = self._first_company_name(issuer_segment)
        if issuer_name:
            nota.prestador.razao_social = issuer_name
        nota.prestador.inscricao_estadual = self._value_after_label(lines, "inscricao estadual", occurrence=0)
        nota.prestador.endereco.logradouro = self._first_address(issuer_segment)

        destination_name = self._value_after_label(lines, "nome/razao social", occurrence=0)
        if destination_name and normalize_text(destination_name) != normalize_text(nota.prestador.razao_social):
            nota.tomador.razao_social = destination_name
        nota.tomador.endereco.cep = self._value_after_label(lines, "cep", occurrence=0)
        nota.tomador.endereco.bairro = self._value_after_label(lines, "bairro / distrito", occurrence=0)
        nota.tomador.endereco.logradouro = self._value_after_label(lines, "endereco", occurrence=0)
        nota.tomador.endereco.cidade = self._value_after_label(lines, "municipio", occurrence=0)
        nota.tomador.endereco.municipio = nota.tomador.endereco.cidade
        nota.tomador.endereco.uf = self._value_after_label(lines, "uf", occurrence=0)
        nota.tomador.telefone = self._value_after_label(lines, "telefone / fax", occurrence=0)
        nota.tomador.inscricao_estadual = self._value_after_label(lines, "inscricao estadual", occurrence=1)

        for key, value in (
            ("prestador.razao_social", nota.prestador.razao_social),
            ("tomador.razao_social", nota.tomador.razao_social),
            ("tomador.endereco", nota.tomador.endereco.logradouro),
        ):
            record_field(nota, key, value, raw=value, page=1)

    def _parse_dates_and_protocol(self, nota: NotaFiscal, lines: list[str], text: str) -> None:
        emission = self._value_after_label(lines, "data da emissao")
        exit_date = self._value_after_label(lines, "data da saida")
        exit_time = self._value_after_label(lines, "hora da saida")
        nota.data_emissao = iso_date(emission)
        nota.hora_emissao = exit_time
        nota.outros_campos["data_saida"] = iso_date(exit_date)
        protocol = first_match(r"(?mi)^([0-9]{10,})\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})$", text)
        if protocol:
            nota.protocolo = protocol
        record_field(nota, "data_emissao", nota.data_emissao, raw=emission, page=1)

    def _parse_installments(self, nota: NotaFiscal, lines: list[str]) -> None:
        for index, line in enumerate(lines):
            if not re.fullmatch(r"\d{3}", line) or index + 2 >= len(lines):
                continue
            if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", lines[index + 1]):
                continue
            if decimal(lines[index + 2]) is None:
                continue
            raw = f"{line} {lines[index + 1]} {lines[index + 2]}"
            nota.parcelas.append(Parcela(numero=line, vencimento=iso_date(lines[index + 1]), valor=decimal(lines[index + 2]), raw=raw, pagina=1))

    def _parse_totals(self, nota: NotaFiscal, lines: list[str]) -> None:
        pairs = {
            "valor_bruto": ("valor total dos produtos",),
            "valor_total": ("valor total da nota",),
            "valor_aproximado": ("valor total aproximado dos impostos",),
        }
        for field, labels in pairs.items():
            raw = value_after(lines, *labels)
            if field == "valor_aproximado":
                index = self._find(lines, "valor total aproximado")
                raw = next((candidate for candidate in lines[index + 1:] if decimal(candidate) is not None), None) if index is not None else raw
            value = decimal(raw)
            if field == "valor_aproximado":
                nota.tributos.valor_aproximado = value
            elif value is not None:
                setattr(nota, field, value)
            record_field(nota, field, value, raw=raw, page=1)

        tax_pairs = {
            "icms": "valor do icms",
            "ipi": "valor do ipi",
        }
        for field, label in tax_pairs.items():
            raw = value_after(lines, label)
            setattr(nota.tributos, field, decimal(raw))
        nota.tributos.base_calculo = self._numeric_after(lines, "base de calculo do icms")
        nota.tributos.iss = decimal(value_after(lines, "valor total do issqn"))

    def _parse_item(self, nota: NotaFiscal, lines: list[str]) -> None:
        table_index = self._find(lines, "dados dos produtos servicos")
        if table_index is None:
            return
        candidate_index = None
        for index in range(table_index + 1, len(lines)):
            if re.match(r"^\d{4,8}\s+\S", lines[index]) and not re.match(r"^\d{2}/", lines[index]):
                candidate_index = index
                break
        if candidate_index is None:
            return

        product_line = lines[candidate_index]
        match = re.match(r"^(\S+)\s+(.+)$", product_line)
        if not match:
            return
        code, description = match.groups()
        tail = lines[candidate_index + 1:]
        ncm_index = next((index for index, line in enumerate(tail) if re.fullmatch(r"\d{8}", line)), None)
        if ncm_index is None:
            nota.itens.append(Item(codigo=code, descricao=description))
            return
        values = tail[ncm_index:ncm_index + 16]
        item = Item(codigo=code, descricao=description, ncm=values[0] if values else None)
        item.cst = values[1] if len(values) > 1 and re.fullmatch(r"\d{2,3}", values[1]) else None
        item.cfop = values[2] if len(values) > 2 and re.fullmatch(r"\d{4}", values[2]) else None
        unit_index = next((index for index, value in enumerate(values) if normalize_text(value) in {"un", "kg", "pc", "m", "mt"}), None)
        if unit_index is not None:
            item.unidade = values[unit_index]
            numbers = values[unit_index + 1:]
            item.quantidade = decimal(numbers[0]) if len(numbers) > 0 else None
            item.valor_unitario = decimal(numbers[1]) if len(numbers) > 1 else None
            item.valor_desconto = decimal(numbers[2]) if len(numbers) > 2 else None
            item.valor_total = decimal(numbers[3]) if len(numbers) > 3 else None
            item.base_calculo_icms = decimal(numbers[4]) if len(numbers) > 4 else None
            item.valor_icms = decimal(numbers[5]) if len(numbers) > 5 else None
            item.valor_ipi = decimal(numbers[6]) if len(numbers) > 6 else None
            item.aliquota_icms = decimal(numbers[7]) if len(numbers) > 7 else None
            item.aliquota_ipi = decimal(numbers[8]) if len(numbers) > 8 else None
            item.valor_total_tributos = decimal(numbers[10]) if len(numbers) > 10 else None
        item.outros_campos = {"marca": tail[0] if tail else None, "raw_linhas": tail[:16]}
        nota.itens.append(item)

    def _parse_transport(self, nota: NotaFiscal, lines: list[str]) -> None:
        transport_index = self._find(lines, "transportador volumes transportados")
        if transport_index is None:
            return
        segment = lines[transport_index:]
        nota.outros_campos["transportador"] = {
            "cnpj": next(iter(re.findall(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", "\n".join(segment))), None),
            "frete_por_conta": value_after(segment, "frete por conta"),
            "razao_social": value_after(segment, "nome/razao social"),
        }

    def _parse_additional(self, nota: NotaFiscal, lines: list[str]) -> None:
        value = value_after(lines, "informacoes complementares")
        if value:
            nota.observacoes = value
        nota.outros_campos["issqn"] = {
            "inscricao_municipal": value_after(lines, "inscricao municipal"),
            "valor_total_servicos": decimal(value_after(lines, "valor total dos servicos")),
            "base_calculo": decimal(value_after(lines, "base de calculo do issqn")),
            "valor_total": decimal(value_after(lines, "valor total do issqn")),
        }

    def _validate(self, nota: NotaFiscal) -> None:
        if nota.chave:
            add_validation(nota, "nfe.chave_44_digitos", "ok" if len(nota.chave) == 44 else "error", extracted=nota.chave)
        if nota.itens and nota.valor_bruto is not None:
            item_total = round(sum(item.valor_total or 0 for item in nota.itens), 2)
            status = "ok" if abs(item_total - nota.valor_bruto) <= 0.01 else "warning"
            add_validation(nota, "nfe.itens_somam_produtos", status, extracted=nota.valor_bruto, calculated=item_total)
        if nota.parcelas and nota.valor_total is not None:
            parcel_total = round(sum(item.valor or 0 for item in nota.parcelas), 2)
            status = "ok" if abs(parcel_total - nota.valor_total) <= 0.01 else "warning"
            add_validation(nota, "nfe.parcelas_somam_total_nota", status, extracted=nota.valor_total, calculated=parcel_total)

    @staticmethod
    def _find(lines: list[str], label: str) -> int | None:
        if normalize_text(label) == "danfe":
            return next((index for index, line in enumerate(lines) if re.search(r"(?i)\bdanfe\b", normalize_text(line))), None)
        wanted = re.sub(r"[^a-z0-9]", "", normalize_text(label))
        for index, line in enumerate(lines):
            if wanted in re.sub(r"[^a-z0-9]", "", normalize_text(line)):
                return index
        return None

    @classmethod
    def _value_after_label(cls, lines: list[str], label: str, occurrence: int = 0) -> str | None:
        wanted = normalize_text(label)
        compact_wanted = re.sub(r"[^a-z0-9]", "", wanted)
        seen = 0
        for index, line in enumerate(lines):
            normalized_line = normalize_text(line)
            if wanted not in normalized_line and compact_wanted not in re.sub(r"[^a-z0-9]", "", normalized_line):
                continue
            if seen == occurrence:
                if index + 1 < len(lines):
                    return lines[index + 1]
                return None
            seen += 1
        return None

    @classmethod
    def _numeric_after(cls, lines: list[str], label: str) -> float | None:
        index = cls._find(lines, label)
        if index is None:
            return None
        for line in lines[index + 1:]:
            value = decimal(line)
            if value is not None:
                return value
        return None

    @staticmethod
    def _first_company_name(lines: list[str]) -> str | None:
        for line in lines:
            normalized = normalize_text(line)
            if "documento auxiliar" in normalized or "danfe" in normalized:
                continue
            if len(line) > 6 and not re.search(r"\d{2}/\d{2}/\d{4}|cep|fone|cnpj|inscricao|protocolo", normalized):
                return line
        return None

    @staticmethod
    def _first_address(lines: list[str]) -> str | None:
        for line in lines:
            normalized = normalize_text(line)
            if any(token in normalized for token in ("avenida ", "av ", "rua ", "rodovia ")):
                return line
        return None
