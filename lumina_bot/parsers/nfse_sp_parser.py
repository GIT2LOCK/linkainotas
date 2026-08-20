"""Parser for the São Paulo municipal NFS-e layout."""

from __future__ import annotations

import re

from lumina_bot.core.document_detector import DocumentType
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.parsers.base_parser import BaseParser, ParseContext
from lumina_bot.parsers.fiscal_layout_utils import (
    add_validation,
    all_pages,
    context_lines,
    decimal,
    digits,
    first_match,
    iso_date,
    normalize_text,
    record_field,
    value_after,
    values_after,
)


class NfseSpParser(BaseParser):
    """Extract the two-page NFSe SP PDF without confusing it with a DANFE."""

    document_type = DocumentType.NFSE_SP
    parser_name = "nfse_sp_parser"

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        pages = all_pages(context)
        page_one = pages[0] if pages else context_lines(context)
        text = "\n".join("\n".join(page) for page in pages) or context.text

        nota.tipo_documento = DocumentType.NFSE_SP.value
        nota.layout = DocumentType.NFSE_SP.value
        nota.sub_layout = "SP_2P"
        nota.modelo = "NFS-e"
        nota.municipio_emissor_nfse = "São Paulo"
        nota.municipio = "São Paulo"
        nota.uf = "SP"
        nota.prestador.cnpj = self._cnpj_in_section(page_one, "prestador de servicos", "tomador de servicos") or nota.prestador.cnpj
        nota.tomador.cnpj = self._cnpj_in_section(page_one, "tomador de servicos", "intermediario de servicos")
        self._parse_header(nota, page_one, text)
        self._parse_parties(nota, page_one)
        self._parse_service(nota, page_one)
        self._parse_taxes(nota, page_one)
        self._parse_page_two(nota, pages[1] if len(pages) > 1 else [], text)
        self._validate(nota)
        nota.outros_campos["fonte_prioritaria"] = "xml" if context.xml_text else "pdf_text"

    def _parse_header(self, nota: NotaFiscal, lines: list[str], text: str) -> None:
        number = first_match(r"(?m)^(\d{8})$", "\n".join(lines))
        if number:
            nota.numero = number
            record_field(nota, "numero", number, raw=number, page=1)

        date_line = next((line for line in lines if re.match(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}$", line)), None)
        if date_line:
            date_match = re.search(r"\d{2}/\d{2}/\d{4}", date_line)
            time_match = re.search(r"\d{2}:\d{2}:\d{2}", date_line)
            emission_date = iso_date(date_match.group(0)) if date_match else None
            nota.hora_emissao = time_match.group(0) if time_match else nota.hora_emissao
            nota.data_emissao = f"{emission_date}T{nota.hora_emissao}" if emission_date and nota.hora_emissao else emission_date
            record_field(nota, "data_emissao", nota.data_emissao, raw=date_line, page=1)

        verification = first_match(r"(?m)^([A-Z0-9]{4}-[A-Z0-9]{4})$", "\n".join(lines))
        if verification:
            nota.autorizacao = verification
            record_field(nota, "codigo_verificacao", verification, raw=verification, page=1)

        identifier = first_match(r"(?mi)identificador nacional\s*:?\s*([0-9]{44,60})", text)
        identifier = identifier or first_match(r"(?m)^([0-9]{44,60})$", text)
        if identifier:
            nota.outros_campos["identificador_nacional"] = identifier
            nota.chave = identifier
            nota.chave_acesso_raw = identifier
            record_field(nota, "identificador_nacional", identifier, raw=identifier, page=1)

        rps_match = re.search(r"(?mi)^rps\s+n[^0-9]*([0-9]+)\s+s[^a-z0-9]+([^,\n]+)", "\n".join(lines))
        if rps_match:
            nota.rps_numero = rps_match.group(1).strip()
            nota.outros_campos["rps_numero"] = nota.rps_numero
            nota.outros_campos["rps_serie"] = rps_match.group(2).strip() or "NFSE"
            nota.serie = nota.outros_campos["rps_serie"]
        rps_date = first_match(r"(?mi)^rps.*emitido em\s+([0-9]{2}/[0-9]{2}/[0-9]{4})", "\n".join(lines))
        if rps_date:
            nota.outros_campos["rps_data_emissao"] = iso_date(rps_date)

    def _parse_parties(self, nota: NotaFiscal, lines: list[str]) -> None:
        prestador_start = self._find(lines, "prestador de servicos")
        tomador_start = self._find(lines, "tomador de servicos")
        intermediary_start = self._find(lines, "intermediario de servicos")
        service_start = self._find(lines, "discriminacao de servicos")
        prestador_lines = lines[prestador_start:tomador_start] if prestador_start is not None and tomador_start is not None else []
        tomador_end = intermediary_start or service_start or len(lines)
        tomador_lines = lines[tomador_start:tomador_end] if tomador_start is not None else []
        self._party(nota.prestador, prestador_lines, "prestador", nota)
        self._party(nota.tomador, tomador_lines, "tomador", nota)

        if intermediary_start is not None:
            intermediary_lines = lines[intermediary_start:service_start or len(lines)]
            nota.intermediario = self._real_value(value_after(intermediary_lines, "nome/razao social"))

    def _party(self, party: object, lines: list[str], prefix: str, nota: NotaFiscal) -> None:
        if not lines:
            return
        cnpj = self._first_cnpj("\n".join(lines))
        if cnpj:
            party.cnpj = cnpj  # type: ignore[attr-defined]
        labels = [
            "nome/razao social",
            "cpf/cnpj",
            "inscricao municipal",
            "endereco",
            "municipio",
            "uf",
            "e-mail",
        ]
        label_indexes = {label: self._find(lines, label) for label in labels}
        if prefix == "prestador":
            value_labels = labels[:4]
        else:
            value_labels = labels
        ordered_indexes = [label_indexes[label] for label in value_labels if label_indexes[label] is not None]
        value_start = max(ordered_indexes) + 1 if ordered_indexes else 0
        values = lines[value_start:value_start + len(ordered_indexes)]
        # The municipal PDF emits all labels first and all values afterwards.
        present_labels = sorted(
            (label for label in value_labels if label_indexes[label] is not None),
            key=lambda label: label_indexes[label] or 0,
        )
        by_label = dict(zip(present_labels, values, strict=False))
        party.inscricao_municipal = self._real_value(by_label.get("inscricao municipal"))  # type: ignore[attr-defined]
        party.razao_social = self._real_value(by_label.get("nome/razao social"))  # type: ignore[attr-defined]
        address = self._real_value(by_label.get("endereco"))
        municipality = self._real_value(by_label.get("municipio"))
        uf = self._real_value(by_label.get("uf"))
        if municipality is None:
            municipality = self._real_value(self._same_line_value(lines, "municipio"))
        if uf is None:
            uf = self._real_value(self._same_line_value(lines, "uf"))
        party.endereco.logradouro = address  # type: ignore[attr-defined]
        party.endereco.cidade = municipality  # type: ignore[attr-defined]
        party.endereco.municipio = municipality  # type: ignore[attr-defined]
        party.endereco.uf = uf  # type: ignore[attr-defined]
        record_field(nota, f"{prefix}.cnpj", party.cnpj, raw=party.cnpj, page=1)  # type: ignore[attr-defined]
        record_field(nota, f"{prefix}.razao_social", party.razao_social, raw=party.razao_social, page=1)  # type: ignore[attr-defined]
        record_field(nota, f"{prefix}.endereco", address, raw=address, page=1)

    def _parse_service(self, nota: NotaFiscal, lines: list[str]) -> None:
        service_start = self._find(lines, "discriminacao de servicos")
        total_start = self._find(lines, "valor total do servico")
        if service_start is not None:
            service_lines = lines[service_start + 1:total_start or len(lines)]
            service_lines = [line for line in service_lines if normalize_text(line) not in {"-", "--"}]
            nota.discriminacao = " ".join(service_lines).strip() or None
            nota.descricao_servico = nota.discriminacao
            record_field(nota, "discriminacao", nota.discriminacao, raw="\n".join(service_lines), page=1)

        if total_start is not None:
            nota.valor_bruto = decimal(value_after(lines, "valor total do servico", start=total_start))
            nota.valor_total = nota.valor_bruto
            nota.valor_liquido = nota.valor_bruto
            record_field(nota, "valor_total", nota.valor_total, raw=value_after(lines, "valor total do servico", start=total_start), page=1)

        code_index = self._find(lines, "codigo do servico")
        if code_index is not None:
            for candidate in lines[code_index + 1:]:
                match = re.match(r"^\s*([0-9]{4,5})\s*-\s*(.+)$", candidate)
                if match:
                    nota.codigo_servico = match.group(1)
                    nota.descricao_servico = nota.descricao_servico or match.group(2).strip()
                    nota.outros_campos["descricao_codigo_servico"] = match.group(2).strip()
                    break

    def _parse_taxes(self, nota: NotaFiscal, lines: list[str]) -> None:
        contribution_index = self._find(lines, "contribuicao previdenciaria")
        if contribution_index is not None:
            values = values_after(lines, contribution_index, 5)
            for field, raw in zip(("inss", "irrf", "cofins", "pis", "ipi"), values, strict=False):
                if field == "ipi":
                    nota.tributos.outros["ipi"] = decimal(raw)
                else:
                    setattr(nota.tributos, field, decimal(raw))

        mapping = {
            "base_calculo": "base de calculo",
            "aliquota": "aliquota",
            "iss": "valor do iss",
            "descontos": "valor total das deducoes",
        }
        for field, label in mapping.items():
            raw = value_after(lines, label)
            parsed = decimal(raw)
            if field in {"base_calculo", "aliquota", "iss", "descontos"} and parsed is not None:
                setattr(nota.tributos, field, parsed)
                record_field(nota, f"tributos.{field}", parsed, raw=raw, page=1)

        deductions_index = self._find(lines, "valor total das deducoes")
        if deductions_index is not None:
            values = values_after(lines, deductions_index, 5)
            if len(values) >= 5:
                nota.tributos.descontos = decimal(values[0])
                nota.tributos.base_calculo = decimal(values[1])
                nota.tributos.aliquota = decimal(values[2])
                nota.tributos.iss = decimal(values[3])
                nota.outros_campos["credito_programa_nfp"] = decimal(values[4])

        approximate_index = self._find(lines, "valor aproximado dos tributos")
        if approximate_index is not None:
            approximate = next((candidate for candidate in lines[approximate_index + 1:] if "r$" in candidate.lower()), None)
            if approximate:
                nota.tributos.valor_aproximado = decimal(approximate)
                nota.outros_campos["valor_aproximado_raw"] = approximate
                nota.valor_aproximado_tributos_raw = approximate

    def _parse_page_two(self, nota: NotaFiscal, lines: list[str], text: str) -> None:
        if not lines:
            return
        normalized_text = "\n".join(lines)
        identifier = first_match(r"(?mi)identificador\s*:?\s*([0-9]{44,60})", normalized_text)
        purchaser_start = self._find(lines, "adquirente")
        service_start = self._find(lines, "servico prestado")
        purchaser = lines[purchaser_start + 1:service_start] if purchaser_start is not None and service_start is not None else []
        cep_indexes = [index for index, line in enumerate(purchaser) if normalize_text(line) == "cep:"]
        purchaser_value_start = (cep_indexes[-1] + 1) if cep_indexes else len(purchaser)
        purchaser_values = purchaser[purchaser_value_start:purchaser_value_start + 8]
        classification_start = self._find(lines, "classificacao tributaria")
        service_lines = lines[service_start + 1:classification_start] if service_start is not None and classification_start is not None else []
        service_label_indexes = [index for index, line in enumerate(service_lines) if ":" in line]
        service_values = service_lines[service_label_indexes[-1] + 1:service_label_indexes[-1] + 6] if service_label_indexes else []
        nbs_value = next((line for line in lines if re.match(r"^\d{9}\s*-", line)), None)
        nota.outros_campos["ibs_cbs"] = {
            "identificador": identifier,
            "fornecedor_cnpj": self._first_cnpj(normalized_text),
            "valor_servicos_antes_tributos": self._numeric_after(lines, "valor dos servicos antes dos tributos"),
            "valor_total_cobrado": decimal(value_after(lines, "valor total cobrado")),
            "nbs": nbs_value,
            "situacao_tributaria": value_after(lines, "situacao tributaria"),
        }
        nota.codigo_nbs = digits(nbs_value)
        if purchaser_values:
            nota.outros_campos["ibs_cbs"]["adquirente"] = {
                "cnpj": purchaser_values[0] if len(purchaser_values) > 0 else None,
                "razao_social": purchaser_values[1] if len(purchaser_values) > 1 else None,
                "logradouro": purchaser_values[2] if len(purchaser_values) > 2 else None,
                "numero": purchaser_values[3] if len(purchaser_values) > 3 else None,
                "bairro": purchaser_values[4] if len(purchaser_values) > 4 else None,
                "email": purchaser_values[5] if len(purchaser_values) > 5 else None,
                "municipio": purchaser_values[6] if len(purchaser_values) > 6 else None,
                "cep": purchaser_values[7] if len(purchaser_values) > 7 else None,
            }
        nota.outros_campos["ibs_cbs"]["servico"] = dict(zip(
            ("local_prestacao", "codigo_indicador_operacao", "localidade_incidencia", "tipo_operacao", "operacao_uso"),
            service_values,
            strict=False,
        ))
        ibs_start = self._find(lines, "valor do ibs")
        ibs_values = [decimal(line) for line in lines[ibs_start + 1:ibs_start + 8]] if ibs_start is not None else []
        cbs_start = self._find(lines, "valor da cbs")
        cbs_values = [decimal(line) for line in lines[cbs_start + 1:cbs_start + 7]] if cbs_start is not None else []
        nota.tributos.ibs = max((value for value in ibs_values if value is not None), default=None)
        nota.tributos.cbs = max((value for value in cbs_values if value is not None and value <= 100), default=None)
        nota.outros_campos["ibs_cbs"]["valor_ibs"] = nota.tributos.ibs
        nota.outros_campos["ibs_cbs"]["valor_cbs"] = nota.tributos.cbs
        nota.outros_campos["nfse"] = {
            "identificador_nacional": identifier,
            "rps_numero": nota.rps_numero,
            "municipio_emissor": nota.municipio_emissor_nfse,
        }

    def _validate(self, nota: NotaFiscal) -> None:
        if nota.valor_total is not None and nota.valor_bruto is not None:
            status = "ok" if abs(nota.valor_total - nota.valor_bruto) <= 0.01 else "warning"
            add_validation(nota, "nfse.valor_total_igual_valor_servico", status, extracted=nota.valor_total, calculated=nota.valor_bruto)
        if nota.tributos.base_calculo is not None and nota.valor_total is not None:
            status = "ok" if nota.tributos.base_calculo <= nota.valor_total + 0.01 else "error"
            add_validation(nota, "nfse.base_calculo_nao_supera_total", status, extracted=nota.tributos.base_calculo, calculated=nota.valor_total)
        if nota.tributos.iss is not None and nota.tributos.base_calculo is not None and nota.tributos.aliquota is not None:
            expected = round(nota.tributos.base_calculo * nota.tributos.aliquota / 100, 2)
            status = "ok" if abs(nota.tributos.iss - expected) <= 0.02 else "warning"
            add_validation(nota, "nfse.iss_compativel_com_base_e_aliquota", status, extracted=nota.tributos.iss, calculated=expected)
        identifier = nota.outros_campos.get("identificador_nacional")
        if identifier:
            add_validation(nota, "nfse.identificador_nacional_completo", "ok" if len(digits(identifier) or "") >= 44 else "error", extracted=identifier)

    @staticmethod
    def _find(lines: list[str], label: str) -> int | None:
        wanted = normalize_text(label)
        for index, line in enumerate(lines):
            if wanted in normalize_text(line):
                return index
        return None

    @staticmethod
    def _same_line_value(lines: list[str], label: str) -> str | None:
        wanted = normalize_text(label)
        for line in lines:
            normalized = normalize_text(line)
            if wanted not in normalized:
                continue
            if ":" in line:
                suffix = line.split(":", 1)[1].strip()
            else:
                suffix = normalized.split(wanted, 1)[1].strip(" :;-=")
            if suffix:
                return suffix
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
    def _first_cnpj(text: str) -> str | None:
        match = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", text)
        return match.group(0) if match else None

    @classmethod
    def _cnpj_in_section(cls, lines: list[str], start_label: str, end_label: str) -> str | None:
        start = cls._find(lines, start_label)
        end = cls._find(lines, end_label, ) if start is None else None
        if start is None:
            return None
        segment = lines[start:]
        end_relative = cls._find(segment[1:], end_label)
        if end_relative is not None:
            segment = segment[:end_relative + 1]
        return cls._first_cnpj("\n".join(segment))

    @staticmethod
    def _real_value(value: str | None) -> str | None:
        if not value or normalize_text(value) in {"-", "--", "nao informado", "nao informado"}:
            return None
        return value.strip()
