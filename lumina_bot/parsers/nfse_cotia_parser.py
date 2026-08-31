"""Parser for the one-page Cotia municipal NFS-e layout."""

from __future__ import annotations

import re

from lumina_bot.core.document_detector import DocumentType
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.parsers.base_parser import BaseParser, ParseContext
from lumina_bot.parsers.fiscal_layout_utils import (
    add_validation,
    all_pages,
    decimal,
    digits,
    iso_date,
    normalize_text,
    record_field,
    word_value_after_label,
)


class NfseCotiaParser(BaseParser):
    """Extract Cotia's one-page NFS-e without requiring São Paulo page two."""

    document_type = DocumentType.NFSE_COTIA_1P
    parser_name = "nfse_cotia_1p_parser"

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        pages = all_pages(context)
        lines = pages[0] if pages else self._lines(context.text)
        text = "\n".join("\n".join(page) for page in pages) or context.text
        words = context.pdf.words

        nota.tipo_documento = DocumentType.NFSE_COTIA_1P.value
        nota.layout = DocumentType.NFSE_COTIA_1P.value
        nota.sub_layout = "COTIA_1P"
        nota.modelo = "NFS-e"
        nota.municipio_emissor_nfse = "Cotia"
        nota.municipio = "Cotia"
        nota.uf = "SP"
        # The generic text-order pass can confuse the liquid value or the
        # following work-code line with ``outras retenções`` on this layout.
        nota.tributos.retencoes = None

        self._parse_header(nota, lines, text, words)
        self._parse_party(nota.prestador, nota, lines, "prestador de servicos", "tomador de servicos", "prestador", words)
        self._parse_party(nota.tomador, nota, lines, "tomador de servicos", "discriminacao dos servicos", "tomador", words)
        self._parse_service(nota, lines)
        self._parse_totals_and_taxes(nota, lines, text, words)
        self._parse_additional(nota, lines, text)
        self._validate(nota)
        nota.outros_campos["fonte_prioritaria"] = "xml" if context.xml_text else "pdf_text"

    def _parse_header(self, nota: NotaFiscal, lines: list[str], text: str, words: tuple[object, ...] = ()) -> None:
        number = self._word_value(words, "n nota") or self._value(lines, "n nota", "nº nota", "numero da nota")
        if number is None:
            number = self._first_match(text, r"(?im)(?:n[ºo]?\s*nota|numero da nota)\s*[:#-]?\s*([0-9]{3,})")
        nota.numero = self._real_value(number)
        record_field(nota, "numero", nota.numero, raw=number, page=1)

        rps = self._word_value(words, "rps") or self._value(lines, "rps") or self._first_match(text, r"(?im)\brps\s*(?:n[ºo]?\s*)?[:#-]?\s*([0-9]{3,})")
        nota.rps_numero = self._real_value(rps)
        nota.outros_campos["rps_numero"] = nota.rps_numero
        record_field(nota, "rps_numero", nota.rps_numero, raw=rps, page=1)

        date_raw = self._word_value(words, "data de emissao") or self._value(lines, "data de emissao", "data de emissão")
        date_raw = date_raw or self._first_match(text, r"(?im)data de emiss[aã]o\s*[:\-]?\s*([^\n]+)")
        nota.data_emissao = self._iso_date_pt(date_raw)
        record_field(nota, "data_emissao", nota.data_emissao, raw=date_raw, page=1)

        competencia_raw = self._word_value(words, "competencia") or self._value(lines, "competencia")
        competencia_raw = competencia_raw or self._first_match(text, r"(?im)compet[eê]ncia\s*[:\-]?\s*([^\n]+)")
        nota.competencia = self._competencia(competencia_raw)
        record_field(nota, "competencia", nota.competencia, raw=competencia_raw, page=1)

        verification_values: list[str] = []
        for index, line in enumerate(lines):
            if "codigo de verificacao" not in normalize_text(line):
                continue
            for candidate in lines[index + 1:index + 10]:
                compact_candidate = re.sub(r"\s+", "", candidate).strip(" :;-= ")
                if re.fullmatch(r"(?=.*[0-9])(?=.*[A-Za-z])[A-Za-z0-9-]{6,}", compact_candidate):
                    verification_values.append(compact_candidate)
        verification = self._real_value(
            self._word_value(words, "codigo de verificacao")
            or (verification_values[0] if verification_values else None)
            or self._value(lines, "codigo de verificacao", "código de verificação")
        )
        nota.autorizacao = verification
        nota.outros_campos["codigo_verificacao"] = verification
        if len(verification_values) > 1:
            nota.outros_campos["codigo_verificacao_rodape"] = verification_values[-1]
        record_field(nota, "codigo_verificacao", verification, raw=verification, page=1)

    def _parse_party(
        self,
        party: object,
        nota: NotaFiscal,
        lines: list[str],
        start_label: str,
        end_label: str,
        prefix: str,
        words: tuple[object, ...] = (),
    ) -> None:
        occurrence = 0 if prefix == "prestador" else 1
        section = self._party_section(lines, occurrence, prefix)
        if not section:
            return
        text = "\n".join(section)
        cnpj = self._word_value(words, "cnpj cpf", occurrence=occurrence, min_y=100, max_y=280) or self._first_cnpj(text)
        if cnpj:
            party.cnpj = cnpj  # type: ignore[attr-defined]

        fields = {
            "razao_social": ("nome/razao social", "nome/razão social", "razao social", "razo social nome"),
            "inscricao_municipal": ("inscricao municipal", "inscrição municipal"),
            "inscricao_estadual": ("inscricao estadual", "inscrição estadual"),
            "logradouro": ("endereco", "endereço"),
            "complemento": ("complemento",),
            "bairro": ("bairro",),
            "cidade": ("municipio", "município", "cidade"),
            "uf": ("uf",),
            "cep": ("cep",),
            "pais": ("pais", "país"),
            "email": ("e-mail", "email"),
            "telefone": ("telefone",),
        }
        for field_name, labels in fields.items():
            value = next(
                (
                    self._real_value(self._word_value(words, label, occurrence=occurrence, min_y=100, max_y=280, join_same_row=True))
                    for label in labels
                    if self._word_value(words, label, occurrence=occurrence, min_y=100, max_y=280, join_same_row=True)
                ),
                None,
            )
            if not words:
                value = value or self._real_value(self._value(section, *labels))
            if normalize_text(value).strip(" :.-") in {"ie", "i e", "i.e", "inscricao municipal", "inscricao estadual", "bairro", "uf", "pais", "email", "e mail"}:
                value = None
            if field_name == "inscricao_municipal" and value:
                value = re.split(r"(?i)\s+i\.?\s*e\.?\s*:", value, maxsplit=1)[0].strip() or None
            if field_name == "uf" and value:
                uf_match = re.search(r"\b([A-Z]{2})\b", value.upper())
                value = uf_match.group(1) if uf_match else value
            if field_name == "pais" and value:
                value = re.sub(r"(?i)^pais\s*:\s*", "", value).strip() or None
            if field_name in {"cidade"}:
                party.endereco.cidade = value  # type: ignore[attr-defined]
                party.endereco.municipio = value  # type: ignore[attr-defined]
            elif field_name in {"logradouro", "complemento", "bairro", "uf", "cep", "pais"}:
                setattr(party.endereco, field_name, value)  # type: ignore[attr-defined]
            else:
                setattr(party, field_name, value)  # type: ignore[attr-defined]

        record_field(nota, f"{prefix}.cnpj", party.cnpj, raw=party.cnpj, page=1)  # type: ignore[attr-defined]
        record_field(nota, f"{prefix}.razao_social", party.razao_social, raw=party.razao_social, page=1)  # type: ignore[attr-defined]

    def _parse_service(self, nota: NotaFiscal, lines: list[str]) -> None:
        service_start = next(
            (
                index for index, line in enumerate(lines)
                if "concretagem" in normalize_text(line) and "issqn" not in normalize_text(line)
            ),
            None,
        )
        if service_start is not None:
            service_end = next(
                (
                    index for index in range(service_start + 1, len(lines))
                    if any(anchor in normalize_text(lines[index]) for anchor in ("valor liquido da nota", "vlr outras retencoes", "valor total da nota"))
                ),
                len(lines),
            )
            section = lines[service_start:service_end]
        else:
            section = self._section(lines, "discriminacao dos servicos", "informacoes complementares")
        if not section:
            section = self._section(lines, "discriminacao dos servicos", "outras informacoes")
        raw_lines = [line for line in section if normalize_text(line) not in {"-", "--", "----"}]
        raw = "\n".join(raw_lines).strip()
        normalized = " ".join(raw_lines).strip() or None
        nota.discriminacao = normalized

        first_line = raw_lines[0] if raw_lines else ""
        service_description = re.split(
            r"\s+-\s+local\s+da\s+obra\s*:",
            first_line,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        nota.descricao_servico = service_description or normalized
        local_obra = self._match_value(
            raw,
            r"local\s+da\s+obra\s*:\s*(.*?)(?=\s+codigo\s+cei\s*:|\s+cno\s*/?\s*cei\s*:|$)",
        )
        codigo_cei = self._match_value(raw, r"codigo\s+cei\s*[:=-]?\s*([0-9]+)")
        cno_cei = self._match_value(
            raw,
            r"(?:cno\s*/?\s*cei|cei\s*/?\s*cno)\s*[:=-]?\s*([0-9./-]+)",
        )
        cno_cei = cno_cei or self._match_value(raw, r"cno\s*[:=-]?\s*([0-9./-]+)")
        sfo_bras = self._match_value(raw, r"sf[oó]bras?\s*[:=-]?\s*([A-Z0-9./-]+)")
        nota.outros_campos.setdefault("nfse", {})
        nota.outros_campos["nfse"].update({
            "discriminacao_servicos_raw": raw or None,
            "discriminacao_servicos": normalized,
            "descricao_linhas": raw_lines,
            "servico_descricao": nota.descricao_servico,
            "local_obra": local_obra,
            "codigo_cei": codigo_cei,
            "cno_cei": cno_cei,
            "sfo_bras": sfo_bras,
        })
        nota.codigo_cei_cno = cno_cei
        nota.codigo_cei_cno = nota.codigo_cei_cno or self._match_value(raw, r"codigo\s+cei\s*[:=-]?\s*([0-9./-]+)")
        nota.codigo_obra = self._match_value(raw, r"(?:c[oó]digo da obra)\s*[:=-]?\s*([A-Z0-9./-]+)")
        nota.sfo_bras = sfo_bras
        approximate = self._match_value(raw, r"valor aproximado dos tributos?\s*[:=-]?\s*(?:(?:R\$|RS)\s*)?([0-9.,]+)")
        percentage = self._match_value(raw, r"valor aproximado dos tributos?.*?\(?\s*([0-9]+[,.][0-9]+)\s*%\)?")
        nota.tributos.valor_aproximado = decimal(approximate)
        nota.valor_aproximado_tributos_raw = approximate
        nota.outros_campos["tributos_aproximados"] = {"raw": approximate, "percentual": decimal(percentage)}
        nota.outros_campos["nfse"]["percentual_aproximado_tributos"] = decimal(percentage)

    def _parse_totals_and_taxes(
        self,
        nota: NotaFiscal,
        lines: list[str],
        text: str,
        words: tuple[object, ...] = (),
    ) -> None:
        total_raw = self._word_value(words, "valor total da nota", min_y=500) or self._value(lines, "valor total da nota", "valor total nota", "valor total")
        nota.valor_total = decimal(total_raw)
        nota.valor_total = nota.valor_total or decimal(self._number_after(lines, "valor total da nota"))
        nota.valor_bruto = nota.valor_total
        liquid_raw = self._word_value(words, "valor liquido da nota", min_y=580) or self._value(lines, "valor liquido da nota", "valor líquido da nota", "valor liquido")
        nota.valor_liquido = decimal(liquid_raw)

        tax_labels = {
            "base_calculo": ("base de calculo do iss", "base de cálculo do iss"),
            "aliquota": ("aliquota", "aliquota do iss", "alíquota do iss", "aliquota iss", "alíquota iss"),
            "iss": ("valor do iss", "valor iss"),
            "inss": ("vlr inss retido", "inss retido", "inss"),
            "irrf": ("vlr irrf retido", "irrf retido", "irrf"),
            "csll": ("vlr csll retido", "csll retido", "csll"),
            "pis": ("vlr pis retido", "pis retido", "pis"),
            "cofins": ("vlr cofins retido", "cofins retido", "cofins"),
            "retencoes": ("outras retencoes", "outras retenções"),
            "ibs": ("vlr ibs", "valor do ibs", "valor ibs", "ibs"),
            "cbs": ("vlr cbs", "valor da cbs", "valor cbs", "cbs"),
        }
        for field_name, labels in tax_labels.items():
            raw = next((self._word_value(words, label, min_y=580) for label in labels if self._word_value(words, label, min_y=580)), None)
            # In this layout the label is followed by the next section's
            # ``C�d. Obra`` line in the text layer, so a line-order fallback
            # would turn the work code into a retention amount.
            if field_name != "retencoes":
                raw = raw or self._value(lines, *labels)
            value = decimal(raw)
            # The Cotia PDF places the liquid amount near the last retention
            # label. Do not let the coordinate fallback duplicate it as a tax.
            if field_name == "retencoes" and value is not None and nota.valor_liquido is not None and abs(value - nota.valor_liquido) <= 0.01:
                value = None
            if value is not None:
                setattr(nota.tributos, field_name, value)
            record_field(nota, f"tributos.{field_name}", value, raw=raw, page=1)

        if nota.tributos.retencoes is None and nota.valor_total is not None and nota.valor_liquido is not None and nota.tributos.iss is not None:
            # This is also a useful consistency check: the amount left after
            # ISS tells us whether an unlabelled extra retention exists.
            derived = round(nota.valor_total - nota.tributos.iss - nota.valor_liquido, 2)
            nota.tributos.retencoes = 0.0 if abs(derived) <= 0.005 else derived
            record_field(
                nota,
                "tributos.retencoes",
                nota.tributos.retencoes,
                raw="valor_total - iss - valor_liquido",
                page=1,
            )

        municipality_match = re.search(r"(?im)Munic[^\n]*Incid[^\n]*ISS\s*:\s*([^\n]+)", text)
        municipality = municipality_match.group(1).strip() if municipality_match else None
        cnae_match = re.search(r"(?im)CNAE\s*:\s*([0-9]+)", text)
        service_match = re.search(r"(?im)Servi[^:]*:\s*([0-9]+)", text)
        nbs_raw = next((self._word_value(words, label, min_y=500) for label in ("codigo nbs", "código nbs") if self._word_value(words, label, min_y=500)), None)
        obra_match = next(
            (
                re.search(r"c.{0,5}d\s*\.?\s*obra\s*:\s*([A-Z0-9./-]+)", line, re.IGNORECASE)
                for line in lines
                if re.search(r"c.{0,5}d\s*\.?\s*obra\s*:\s*([A-Z0-9./-]+)", line, re.IGNORECASE)
            ),
            None,
        )
        extras = nota.outros_campos.setdefault("nfse", {})
        extras.update({
            "municipio_incidencia_iss": municipality,
            "codigo_servico_municipal": service_match.group(1) if service_match else self._real_value(self._value(lines, "codigo de servico municipal", "código de serviço municipal")),
            "cnae_descricao": self._value(lines, "cnae"),
            "nbs_descricao": self._value(lines, "nbs"),
        })
        nota.codigo_servico = extras["codigo_servico_municipal"]
        nota.municipio_incidencia_iss = extras["municipio_incidencia_iss"]
        nota.codigo_nbs = self._digits_or_text(nbs_raw or self._value(lines, "codigo nbs", "código nbs"))
        nota.cnae = cnae_match.group(1) if cnae_match else self._digits_or_text(self._value(lines, "cnae codigo", "cnae código", "cnae"))
        nota.codigo_obra = nota.codigo_obra or (obra_match.group(1) if obra_match else self._digits_or_text(self._value(lines, "codigo da obra", "código da obra")))
        nota.outros_campos["cnae"] = nota.cnae
        nota.outros_campos["codigo_obra"] = nota.codigo_obra

        nota.valor_liquido = nota.valor_liquido or (round(nota.valor_total - nota.tributos.iss, 2) if nota.valor_total is not None and nota.tributos.iss is not None else None)
        record_field(nota, "valor_total", nota.valor_total, raw=total_raw, page=1)
        record_field(nota, "valor_liquido", nota.valor_liquido, raw=liquid_raw, page=1)

    def _parse_additional(self, nota: NotaFiscal, lines: list[str], text: str) -> None:
        # Cotia's PDF text order places the visual footer sections after the
        # tax table. Use the nearby section anchors instead of consuming the
        # entire remainder of the page as one block.
        discrimination_index = self._find(lines, "discriminacao dos servicos")
        complement_index = self._find(
            lines,
            "informacoes complementares",
            start=(discrimination_index + 1) if discrimination_index is not None else 0,
        )
        tax_index = self._find(
            lines,
            "vlr outras retencoes",
            start=(complement_index + 1) if complement_index is not None else 0,
        )
        if discrimination_index is not None and complement_index is not None and complement_index > discrimination_index:
            other = lines[discrimination_index + 1:complement_index]
        else:
            other = self._section(lines, "outras informacoes", None)
        if complement_index is not None:
            complement_end = tax_index if tax_index is not None and tax_index > complement_index else len(lines)
            complement = lines[complement_index + 1:complement_end]
        else:
            complement = self._section(lines, "informacoes complementares", "outras informacoes")
        nota.outros_campos["dados_adicionais"] = {
            "informacoes_complementares_raw": "\n".join(complement) or None,
            "outras_informacoes_raw": "\n".join(other) or None,
        }
        nota.observacoes = "\n".join(other or complement).strip() or None

        raw_key = self._first_match(text, r"(?im)chave\s*(?:de)?\s*acesso\s*:\s*([^\n]+)")
        if raw_key and normalize_text(raw_key) not in {"-", "--", "----"}:
            if len(digits(raw_key) or "") == 44:
                nota.chave = digits(raw_key)
            else:
                nota.chave = None
            nota.chave_acesso_raw = raw_key.strip()
        elif "aguardando retorno do ambiente nacional" in normalize_text(text):
            nota.chave = None
            nota.chave_acesso_raw = "Aguardando retorno do Ambiente Nacional"
            add_validation(nota, "chave_nao_disponivel_ambiente_nacional", "warning", extracted=nota.chave_acesso_raw)

    def _validate(self, nota: NotaFiscal) -> None:
        if nota.tributos.base_calculo is not None and nota.tributos.aliquota is not None and nota.tributos.iss is not None:
            expected = round(nota.tributos.base_calculo * nota.tributos.aliquota / 100, 2)
            add_validation(
                nota,
                "nfse.iss_compativel_com_base_e_aliquota",
                "ok" if abs(expected - nota.tributos.iss) <= 0.02 else "warning",
                extracted=nota.tributos.iss,
                calculated=expected,
            )
        if nota.valor_total is not None and nota.valor_liquido is not None and nota.tributos.iss is not None:
            expected = round(nota.valor_total - nota.tributos.iss, 2)
            add_validation(
                nota,
                "nfse.valor_liquido_igual_total_menos_iss",
                "ok" if abs(expected - nota.valor_liquido) <= 0.02 else "warning",
                extracted=nota.valor_liquido,
                calculated=expected,
            )
        if nota.outros_campos.get("codigo_verificacao") and nota.outros_campos.get("codigo_verificacao_rodape"):
            first = normalize_text(str(nota.outros_campos["codigo_verificacao"]))
            last = normalize_text(str(nota.outros_campos["codigo_verificacao_rodape"]))
            add_validation(nota, "nfse.codigo_verificacao_repetido_coincide", "ok" if first == last else "error", extracted=last, calculated=first)

    @classmethod
    def _party_section(cls, lines: list[str], occurrence: int, prefix: str) -> list[str]:
        if prefix == "prestador":
            start = cls._find(lines, "prestador de servicos")
            end = cls._find(lines, "tomador de servicos", start=(start or 0) + 1) if start is not None else None
            return lines[(start or 0) + 1:(end if end is not None else len(lines))]

        # Cotia prints the tomador's fields before its title. Select the
        # second Razao Social/CNPJ block instead of starting at the title.
        starts = [
            index for index, line in enumerate(lines)
            if "razao" in normalize_text(line) or "razo" in normalize_text(line)
        ]
        start = starts[1] if len(starts) > 1 else cls._find(lines, "tomador de servicos")
        end = cls._find(lines, "discriminacao dos servicos", start=(start or 0) + 1) if start is not None else None
        return lines[start:(end if end is not None else len(lines))] if start is not None else []

    @staticmethod
    def _word_value(words: tuple[object, ...], label: str, **kwargs: object) -> str | None:
        if not words:
            return None
        return word_value_after_label(words, label, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def _section(cls, lines: list[str], start_label: str, end_label: str | None) -> list[str]:
        start = cls._find(lines, start_label)
        if start is None:
            return []
        end = cls._find(lines, end_label, start=start + 1) if end_label else None
        return lines[start + 1:(end if end is not None else len(lines))]

    @staticmethod
    def _find(lines: list[str], label: str, start: int = 0) -> int | None:
        wanted = normalize_text(label)
        compact_wanted = re.sub(r"[^a-z0-9]", "", wanted)
        for index in range(start, len(lines)):
            normalized = normalize_text(lines[index])
            if wanted in normalized or compact_wanted in re.sub(r"[^a-z0-9]", "", normalized):
                return index
        return None

    @classmethod
    def _value(cls, lines: list[str], *labels: str) -> str | None:
        indexes = [cls._find(lines, label) for label in labels]
        index = next((item for item in indexes if item is not None), None)
        if index is None:
            return None
        line = lines[index]
        normalized = normalize_text(line)
        for label in labels:
            wanted = normalize_text(label)
            position = normalized.find(wanted)
            if position >= 0:
                suffix = normalized[position + len(wanted):].strip(" :;-=")
                if suffix:
                    return suffix
        if index + 1 < len(lines):
            return lines[index + 1].strip()
        return None

    @classmethod
    def _number_after(cls, lines: list[str], label: str) -> str | None:
        index = cls._find(lines, label)
        if index is None:
            return None
        for line in lines[index + 1:]:
            if decimal(line) is not None:
                return line
        return None

    @staticmethod
    def _first_cnpj(text: str) -> str | None:
        match = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", text)
        return match.group(0) if match else None

    @classmethod
    def _match_value(cls, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None

    @staticmethod
    def _first_match(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else None

    @staticmethod
    def _real_value(value: str | None) -> str | None:
        if not value or normalize_text(value) in {"-", "--", "----", "nao informado"}:
            return None
        return value.strip()

    @staticmethod
    def _iso_date_pt(value: str | None) -> str | None:
        if not value:
            return None
        months = {"JAN": "01", "FEV": "02", "MAR": "03", "ABR": "04", "MAI": "05", "JUN": "06", "JUL": "07", "AGO": "08", "SET": "09", "OUT": "10", "NOV": "11", "DEZ": "12"}
        match = re.search(r"(\d{1,2})\s*/\s*([A-Za-z]{3,})\s*/\s*(\d{4})", value)
        if match:
            day, month, year = match.groups()
            return f"{year}-{months.get(month.upper()[:3], month):0>2}-{int(day):02d}" if month.upper()[:3] in months else value.strip()
        return iso_date(value)

    @staticmethod
    def _competencia(value: str | None) -> str | None:
        if not value:
            return None
        match = re.search(r"(\d{1,2})\s*/\s*(\d{4})", value)
        return f"{match.group(2)}-{int(match.group(1)):02d}" if match else value.strip()

    @staticmethod
    def _digits_or_text(value: str | None) -> str | None:
        value = NfseCotiaParser._real_value(value)
        if not value:
            return None
        return value.split("-", 1)[0].strip()
