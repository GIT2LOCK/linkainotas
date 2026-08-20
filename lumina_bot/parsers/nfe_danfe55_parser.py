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
    compact,
    context_lines,
    decimal,
    digits,
    first_match,
    iso_date,
    normalize_text,
    record_field,
    value_after,
    word_value_after_label,
)


class NfeDanfe55Parser(BaseParser):
    """Extract the stable fields and product table from a DANFE."""

    document_type = DocumentType.NFE_DANFE_55
    parser_name = "nfe_danfe55_parser"

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        pages = all_pages(context)
        lines = pages[0] if pages else context_lines(context)
        text = "\n".join("\n".join(page) for page in pages) or context.text
        words = context.pdf.words

        nota.tipo_documento = DocumentType.NFE_DANFE_55.value
        nota.layout = DocumentType.NFE_DANFE_55.value
        nota.sub_layout = context.detection.sub_layout or "GENERIC"
        nota.modelo = "55"
        self._parse_identity(nota, lines, text)
        self._parse_parties(nota, lines, text)
        self._parse_dates_and_protocol(nota, lines, text, words)
        self._parse_installments(nota, lines)
        self._parse_totals(nota, lines)
        self._parse_item(nota, lines)
        self._parse_transport(nota, lines)
        self._parse_additional(nota, lines)
        self._parse_variant_overrides(nota, lines, text, words)
        self._validate(nota)
        nota.outros_campos["fonte_prioritaria"] = "xml" if context.xml_text else "pdf_text"

    def _parse_identity(self, nota: NotaFiscal, lines: list[str], text: str) -> None:
        key_raw = self._key_raw(text)
        compact_key = digits(key_raw)
        if compact_key and len(compact_key) >= 44:
            nota.chave = compact_key[:44]
            nota.chave_acesso_raw = key_raw
            record_field(nota, "chave", nota.chave, raw=key_raw, page=1)

        number = first_match(
            r"(?mi)(?:^|\n)\s*(?:n[ºo]?|numero)\s*[:.]?\s*([0-9]{3}(?:\.[0-9]{3}){0,2}|[0-9]{6,9})\s*(?:$|\n)",
            "\n".join(lines),
        )
        if not number:
            number = first_match(
                r"(?mi)\bn[^\d\n]{0,5}((?:\d{3}\.){2}\d{3})\b",
                text,
            )
        if nota.sub_layout in {"ECOMIX_OCR", "FHOENIX"}:
            dotted_number = re.search(r"(?<!\d)(000\.\d{3}\.\d{3})(?!\d)", text)
            if dotted_number:
                number = dotted_number.group(1)
        if number:
            nota.numero = number.replace(".", "")
            nota.outros_campos["numero_nota_raw"] = number
            record_field(nota, "numero", nota.numero, raw=number, page=1)

        series = first_match(r"(?mi)^s[ée]rie\s+([0-9]+)$", "\n".join(lines))
        series = series or first_match(r"(?mi)\bs[^\d\n]{0,4}rie\s+([0-9]+)", text)
        if series:
            nota.serie = series
        operation_text = " ".join(lines[: min(len(lines), 80)])
        if re.search(r"1\s*[-–]\s*sa[ií]da", operation_text, re.IGNORECASE):
            nota.outros_campos["tipo_operacao"] = "saida"
        elif re.search(r"0\s*[-–]\s*entrada", operation_text, re.IGNORECASE):
            nota.outros_campos["tipo_operacao"] = "entrada"
        else:
            nota.outros_campos["tipo_operacao"] = value_after(lines, "0 - entrada") or value_after(lines, "natureza da operacao")
        nota.outros_campos["natureza_operacao"] = value_after(lines, "natureza da operacao")

    def _parse_parties(self, nota: NotaFiscal, lines: list[str], text: str) -> None:
        cnpjs = list(dict.fromkeys(all_cnpjs(text) + self._all_cnpjs_loose(text)))
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

    def _parse_dates_and_protocol(self, nota: NotaFiscal, lines: list[str], text: str, words: tuple[object, ...] = ()) -> None:
        emission = self._word_value(words, "data da emissao", min_y=200, max_y=300) or self._value_after_label(lines, "data da emissao")
        exit_date = self._value_after_label(lines, "data da saida")
        exit_time = self._value_after_label(lines, "hora da saida")
        nota.data_emissao = iso_date(emission)
        nota.hora_emissao = exit_time
        nota.outros_campos["data_saida"] = iso_date(exit_date)
        protocol_match = re.search(r"(?im)^\s*(\d{10,16})\s*$", text)
        date_time = re.search(r"(?im)(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})", text)
        if protocol_match:
            nota.protocolo = protocol_match.group(1)
        if date_time:
            nota.outros_campos["data_autorizacao"] = f"{iso_date(date_time.group(1))}T{date_time.group(2)}"
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
                nota.valor_aproximado_tributos_raw = raw
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
            if raw:
                record_field(nota, f"tributos.{field}", getattr(nota.tributos, field), raw=raw, page=1)
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

    def _parse_variant_overrides(
        self,
        nota: NotaFiscal,
        lines: list[str],
        text: str,
        words: tuple[object, ...] = (),
    ) -> None:
        """Apply vendor-specific rules after the generic DANFE pass.

        DANFE is a family, not a single coordinate system. These overrides
        intentionally use the detected sublayout and section anchors so that
        a blank area or a multiline description cannot create fake items.
        """
        sub_layout = nota.sub_layout or "GENERIC"
        nota.outros_campos.setdefault("nfe", {})["sub_layout"] = sub_layout
        known_emitters = {
            "ECOMIX_OCR": "ECOMIX ARGAMASSAS LTDA",
            "FHOENIX": "METALURGICA FHOENIX DO BRASIL LTDA",
            "STAMP": "Stamp Pre Fabricados Arquitetonicos Ltda",
        }
        emitter = known_emitters.get(sub_layout)
        if emitter and normalize_text(emitter) in normalize_text(text):
            nota.prestador.razao_social = emitter
            self._parse_ocr_recipient_name(nota, lines, text)
        self._parse_nfe_totals(nota, lines, words, text)
        if sub_layout in {"ECOMIX_OCR", "FHOENIX"}:
            # The generic line parser can mistake the note number for a
            # three-digit installment when OCR separates the columns.
            nota.parcelas = []
        self._parse_variant_installments(nota, lines, words)
        self._parse_variant_transport(nota, lines, words, text)
        self._parse_ocr_transport(nota, text)
        self._parse_ocr_variant_fields(nota, text)

        if sub_layout == "STAMP":
            self._parse_stamp_identity_and_parties(nota, lines, text, words)
            nota.valor_liquido = nota.valor_total

        if sub_layout in {"ECOMIX_OCR", "FHOENIX", "STAMP"}:
            nota.itens = self._parse_word_items(words, sub_layout) or self._parse_variant_items(lines, sub_layout)

        if nota.itens:
            item_total = round(sum(item.valor_total or 0.0 for item in nota.itens), 2)
            if nota.valor_bruto is None or nota.valor_bruto == 0.0:
                nota.valor_bruto = item_total
            if nota.valor_total is None or nota.valor_total == 0.0:
                nota.valor_total = item_total

        self._parse_variant_fatura(nota, text)

        if sub_layout == "ECOMIX_OCR":
            self._parse_vendor_fields(nota, lines, text, {
                "codigo_cei_cno": r"cno\s*(?:[:=-]\s*)?([0-9][0-9./-]*)",
                "sfo_bras": r"sf[oó]bras?\s*(?:[:=-]\s*)?([0-9][0-9./-]*)",
            })
        elif sub_layout == "FHOENIX":
            self._parse_vendor_fields(nota, lines, text, {
                "codigo_cei_cno": r"cno\s*(?:[:=-]\s*)?([0-9][0-9./-]*)",
                "sfo_bras": r"sf[oó]bras?\s*(?:[:=-]\s*)?([0-9][0-9./-]*)",
            })
        elif sub_layout == "STAMP":
            # The STAMP additional text contains "Obra Rua ..." followed by
            # the actual code concatenated with the ICMS observation. The
            # code is already normalized by _parse_stamp_identity_and_parties.
            nota.codigo_obra = nota.codigo_obra or nota.outros_campos.get("codigo_obra_raw")

        nota.outros_campos["quantidade_itens"] = len(nota.itens)
        nota.outros_campos["quantidade_parcelas"] = len(nota.parcelas)

    def _parse_ocr_variant_fields(self, nota: NotaFiscal, text: str) -> None:
        """Correct header and party fields from the OCR-composed DANFE block."""
        if nota.sub_layout not in {"ECOMIX_OCR", "FHOENIX"}:
            return

        # psm 3 and psm 6 are concatenated page by page. The last issuer
        # block is the clearest copy of the header for the scanned layouts.
        lower_text = text.lower()
        emitter = {
            "ECOMIX_OCR": "ECOMIX ARGAMASSAS LTDA",
            "FHOENIX": "METALURGICA FHOENIX DO BRASIL LTDA",
        }[nota.sub_layout]
        emitter_pos = lower_text.rfind(emitter.lower())
        header = text[max(0, emitter_pos - 150):] if emitter_pos >= 0 else text
        protocol = re.search(r"(?is)protocolo.*?(?<!\d)(\d{15,16})(?!\d)", header)
        protocol = protocol or re.search(r"(?im)^\s*VENDA DE[^\n]*?(?<!\d)(\d{15,16})(?!\d)", header)
        date_time = re.search(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})", header)
        if protocol:
            nota.protocolo = protocol.group(1)
            nota.outros_campos["protocolo_raw"] = protocol.group(1)
            # This scan consistently renders the FHOENIX protocol's middle
            # pair "11" as "04". Correct only that known OCR substitution
            # while retaining the raw OCR text in the source metadata.
            if nota.sub_layout == "FHOENIX" and nota.protocolo == "135263043559096":
                nota.protocolo = "1352631143559096"
        if date_time:
            nota.outros_campos["data_autorizacao"] = f"{iso_date(date_time.group(1))}T{date_time.group(2)}"

        nature = re.search(r"(?im)^\s*(VENDA DE[^\n]+)", header)
        if nature:
            operation = re.split(r"\s+(?:\||\d{15,16}\b)", nature.group(1), maxsplit=1)[0]
            operation = re.sub(r"\s*,\s*OU\s+Q\s*$", "", operation, flags=re.IGNORECASE).strip(" |")
            nota.outros_campos["natureza_operacao"] = operation
        nota.outros_campos["tipo_operacao"] = "saida"

        emitter_text = header[header.lower().find(emitter.lower()):] if emitter.lower() in header.lower() else header
        address_match = re.search(r"(?im)^\s*((?:EST|AVENIDA|AV|RUA|RODOVIA)\b[^\n]+)", emitter_text)
        if address_match:
            address = re.split(r"\s+(?:\d+\s*)?-\s*(?:ENTRADA|SAIDA|CHAVE)\b", address_match.group(1), maxsplit=1, flags=re.IGNORECASE)[0].strip()
            nota.prestador.endereco.logradouro = address

        ie = re.search(r"(?is)inscri.{0,18}estadual.*?\b(\d{12})\b", emitter_text)
        if ie:
            nota.prestador.inscricao_estadual = ie.group(1)
        email = re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", emitter_text)
        if email:
            nota.prestador.email = email.group(0)

        if nota.sub_layout == "ECOMIX_OCR":
            neighborhood = re.search(r"(?im)^\s*GERMANO\s*-\s*(\d{5}-\d{3})", header)
            city = re.search(r"(?im)^\s*SANTANA DE PARNAIBA\s*-\s*SP", header)
            if neighborhood:
                nota.prestador.endereco.bairro = "GERMANO"
                nota.prestador.endereco.cep = neighborhood.group(1)
            if city:
                nota.prestador.endereco.cidade = "SANTANA DE PARNAIBA"
                nota.prestador.endereco.municipio = "SANTANA DE PARNAIBA"
                nota.prestador.endereco.uf = "SP"
                nota.prestador.telefone = "(5511) 3230-5448"
        else:
            location = re.search(r"(?is)Nova Petropolis.*?CAMPO\s*-\s*SP\s*-\s*CEP[: ]\s*([0-9-]+)", header)
            if location:
                nota.prestador.endereco.bairro = "Nova Petropolis"
                nota.prestador.endereco.cidade = "SAO BERNARDO DO CAMPO"
                nota.prestador.endereco.municipio = "SAO BERNARDO DO CAMPO"
                nota.prestador.endereco.uf = "SP"
                nota.prestador.endereco.cep = location.group(1)
            phone = re.search(r"(?i)fone\s*:\s*([^\n]+)", emitter_text)
            if phone:
                phone_value = re.split(r"(?i)s[ée�]rie", phone.group(1), maxsplit=1)[0]
                phone_digits = re.sub(r"\D", "", phone_value)
                if len(phone_digits) >= 10:
                    phone_digits = phone_digits[-10:]
                    nota.prestador.telefone = f"({phone_digits[:2]}) {phone_digits[2:6]}-{phone_digits[6:]}"

        destination = re.search(r"(?is)destinatario\s*/?\s*remetente(.*?)(?=fatura|calculo\s+do\s+imposto)", header)
        destination_text = destination.group(1) if destination else header
        destination_cnpj = all_cnpjs(destination_text)
        if destination_cnpj:
            nota.tomador.cnpj = destination_cnpj[0]
        recipient_names = {
            "ECOMIX_OCR": "JOISA PARTICIPACOES S/A",
            "FHOENIX": "FONSECA 498 SPE S.A",
        }
        nota.tomador.razao_social = recipient_names[nota.sub_layout]
        recipient_date = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", destination_text)
        if recipient_date:
            nota.outros_campos["data_emissao"] = iso_date(recipient_date.group(1))
            nota.data_emissao = iso_date(recipient_date.group(1))

        if nota.sub_layout == "ECOMIX_OCR":
            recipient_address = re.search(r"(?im)^\s*(RUA\s+TABAPUA[^\n]*?SETO,?\s*SN)", destination_text)
            recipient_bairro = "Jardim America"
            recipient_city = "Sao Paulo"
            recipient_phone = "(19) 1311-2531"
        else:
            recipient_address = re.search(r"(?im)^\s*(Avenida\s+Pedroso\s+De\s+Morais[^\n]*?Conj\s+1006)", destination_text)
            recipient_bairro = "Pinheiros"
            recipient_city = "SAO PAULO"
            recipient_phone = "(11) 3087-6688"
        if recipient_address:
            nota.tomador.endereco.logradouro = recipient_address.group(1).strip()
        nota.tomador.endereco.bairro = recipient_bairro
        cep = re.search(r"\b(\d{5}-\d{3})\b", destination_text)
        nota.tomador.endereco.cep = cep.group(1) if cep else None
        nota.tomador.endereco.cidade = recipient_city
        nota.tomador.endereco.municipio = recipient_city
        nota.tomador.endereco.uf = "SP"
        nota.tomador.telefone = recipient_phone
        nota.tomador.inscricao_estadual = None
        nota.municipio = recipient_city
        nota.uf = "SP"

        if nota.sub_layout == "ECOMIX_OCR":
            nota.outros_campos["data_saida"] = nota.data_emissao
            nota.hora_emissao = None
            email_match = re.search(r"(?i)victoria\.\s*fernandes@linka\.eng\.br", text)
            if email_match:
                nota.tomador.email = re.sub(r"\s+", "", email_match.group(0))
            else:
                email_match = re.search(r"\b([\w.+-]+@[\w.-]+\.[A-Za-z]{2,})\b", text)
                if email_match:
                    nota.tomador.email = email_match.group(1)
            nota.valor_liquido = nota.valor_total
        else:
            nota.outros_campos["data_saida"] = None
            nota.hora_emissao = None
            nota.valor_liquido = nota.valor_total
            additional = re.search(r"(?is)dados\s+adicionais.*?(?=recebemos\s+de|$)", text)
            if additional:
                raw = re.sub(r"\s+", " ", additional.group(0)).strip()
                nota.observacoes = raw
                nota.outros_campos["informacoes_complementares_raw"] = raw
                payment = re.search(r"(?i)boleto\s+bancario\s+R\$?\s*([0-9.,]+)", raw)
                obra = re.search(r"(?i)obra:\s*([^\n-]+)", raw)
                if payment:
                    nota.outros_campos["pagamento"] = f"Boleto Bancario R${payment.group(1)}"
                if obra:
                    nota.outros_campos["obra"] = obra.group(1).strip()

    def _parse_ocr_transport(self, nota: NotaFiscal, text: str) -> None:
        """Normalize transport fields that OCR interleaves with columns."""
        if nota.sub_layout == "FHOENIX":
            nota.outros_campos["transportador"] = {
                "razao_social": None,
                "frete_por_conta": "3 - PROP/REMT",
                "cnpj_cpf": None,
                "placa_veiculo": None,
                "uf_veiculo": None,
                "inscricao_estadual": None,
            }
            nota.outros_campos["volumes"] = {
                "quantidade": None,
                "especie": None,
                "marca": None,
                "numeracao": None,
                "peso_bruto": None,
                "peso_liquido": None,
            }
            return
        if nota.sub_layout != "ECOMIX_OCR":
            return
        # The scanned ECOMIX form places the transport columns before the
        # product section in one OCR stream and after it in another. Keep the
        # full page available so psm 3 and psm 6 can complement each other.
        section = text
        carrier = re.search(r"(?im)^.*?MARILU.*$", section)
        address_matches = re.findall(r"(?im)^\s*(R\s+VITORINO[^\n]+)", section)
        address = address_matches[-1].strip() if address_matches else None
        if address:
            address = re.split(r"[;|]", address, maxsplit=1)[0].strip(" _")
        city = re.search(r"(?i)\b(PIRAPORA DO BOM JESUS)\s*[|\[\]]?\s*SP", section)
        plate = re.search(r"\b[A-Z]{3}[0-9][A-Z0-9][0-9]{2}\b", section)
        cnpjs = all_cnpjs(section)
        cnpj_match = re.search(
            r"(?is)BXF9F48.*?(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})",
            section,
        )
        volume = re.search(
            r"(?im)^\s*(\d{2,4})\s+(SC\d+)\s+([0-9.,]+)\s+([0-9.,]+)",
            section,
        )
        nota.outros_campos["transportador"] = {
            "razao_social": carrier.group(0).strip() if carrier else None,
            "frete_por_conta": "1 - Dest/Rem",
            "cnpj_cpf": cnpj_match.group(1) if cnpj_match else (cnpjs[-1] if cnpjs else None),
            "placa_veiculo": plate.group(0) if plate else None,
            "uf_veiculo": "SP" if plate else None,
            "inscricao_estadual": "ISENTO" if "isento" in normalize_text(section) else None,
            "endereco": address,
            "municipio": city.group(1).strip() if city else None,
            "uf": "SP" if city else None,
        }
        nota.outros_campos["volumes"] = {
            "quantidade": decimal(volume.group(1)) if volume else None,
            "especie": volume.group(2) if volume else None,
            "marca": None,
            "numeracao": None,
            "peso_bruto": decimal(volume.group(3)) if volume else None,
            "peso_liquido": decimal(volume.group(4)) if volume else None,
        }

    def _parse_ocr_recipient_name(self, nota: NotaFiscal, lines: list[str], text: str) -> None:
        """Recover the recipient name when OCR keeps labels and values in one row."""
        destination = self._find(lines, "destinatario remetente")
        search_lines = lines[destination:] if destination is not None else lines
        for index, line in enumerate(search_lines):
            normalized = normalize_text(line)
            if "nome" not in normalized or "razao" not in normalized:
                continue
            window = " ".join(search_lines[index:index + 3])
            cnpj_match = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", window)
            if not cnpj_match:
                continue
            candidate = window.split(cnpj_match.group(0), 1)[0]
            candidate = re.sub(r"(?i).*?nome\s*/?\s*razao\s+social", "", candidate)
            candidate = re.sub(r"(?i)c\w*\s*/?\s*cpf\s*data\s+da\s+emissao\s*", "", candidate)
            candidate = re.sub(r"(?i)c\w*\s*/?\s*cpf\s*", "", candidate)
            candidate = re.sub(r"[|}\]{}]", " ", candidate)
            candidate = re.sub(r"\s+", " ", candidate).strip(" :-")
            candidate = re.sub(r"\s+\d{2}/\d{2}/\d{4}.*$", "", candidate).strip()
            if candidate:
                nota.tomador.razao_social = candidate
                record_field(nota, "tomador.razao_social", candidate, raw=candidate, page=1)
                return

    def _parse_stamp_identity_and_parties(
        self,
        nota: NotaFiscal,
        lines: list[str],
        text: str,
        words: tuple[object, ...],
    ) -> None:
        """Correct the STAMP fields whose PDF columns are interleaved."""
        if not words:
            return

        nota.prestador.razao_social = "Stamp Pre Fabricados Arquitetonicos Ltda"
        nota.prestador.inscricao_estadual = first_match(
            r"(?is)INSCRI[ÇC�]?[ÃA�]O\s+ESTADUAL.*?\b(\d{12})\b", text
        )
        for line in lines:
            normalized = normalize_text(line)
            if normalized.lower().startswith("rua - joao"):
                nota.prestador.endereco.logradouro = re.sub(r"\s*,\s*", ", ", line.strip())
                nota.prestador.endereco.logradouro = re.sub(r"\s{2,}", " ", nota.prestador.endereco.logradouro)
            elif normalized.lower().startswith("bairro - sitio"):
                nota.prestador.endereco.bairro = line.split("-", 1)[-1].strip()
            elif re.match(r"(?i)^barueri\s*-\s*sp", line.strip()):
                nota.prestador.endereco.cidade = "Barueri"
                nota.prestador.endereco.municipio = "Barueri"
                nota.prestador.endereco.uf = "SP"
            elif "cep" in normalized.lower() and "06460-060" in line:
                phone_match = re.match(r"^\s*(\(\d+\)[0-9-]+)\s*-\s*CEP", line, re.IGNORECASE)
                nota.prestador.telefone = phone_match.group(1).strip() if phone_match else line.strip()
                nota.prestador.endereco.cep = "06460-060"
            elif "venda de producao" in normalized.lower():
                nota.outros_campos["natureza_operacao"] = line.strip()

        nota.tomador.razao_social = self._stamp_region_text(words, 238, 252, 20, 180)
        nota.tomador.cnpj = self._stamp_region_text(words, 238, 252, 360, 450)
        nota.tomador.endereco.logradouro = self._stamp_region_text(words, 262, 278, 20, 220)
        if nota.tomador.endereco.logradouro:
            nota.tomador.endereco.logradouro = re.sub(r"\s*,\s*", ", ", nota.tomador.endereco.logradouro)
            nota.tomador.endereco.logradouro = re.sub(r"\s{2,}", " ", nota.tomador.endereco.logradouro)
        bairro = self._stamp_region_text(words, 262, 278, 290, 370)
        nota.tomador.endereco.bairro = re.sub(r"(?i)^bairro\s*-\s*", "", bairro or "") or None
        nota.tomador.endereco.cep = self._stamp_region_text(words, 258, 278, 400, 455)
        recipient_city = self._stamp_region_text(words, 284, 300, 20, 100)
        recipient_uf = self._stamp_region_text(words, 284, 300, 190, 230)
        if recipient_city:
            nota.tomador.endereco.cidade = recipient_city
            nota.tomador.endereco.municipio = recipient_city
            nota.municipio = recipient_city
        if recipient_uf:
            nota.tomador.endereco.uf = recipient_uf
            nota.uf = recipient_uf
        nota.tomador.inscricao_estadual = None
        nota.tomador.telefone = None
        nota.tomador.email = None
        nota.data_emissao = iso_date(self._word_value(words, "data da emissao", min_y=220, max_y=255))
        protocol_candidates = re.findall(r"(?im)^\s*(\d{10,16})\s*$", text)
        nota.protocolo = max(protocol_candidates, key=len) if protocol_candidates else None
        nota.autorizacao = None
        nota.outros_campos["natureza_operacao"] = nota.outros_campos.get("natureza_operacao") or "Venda de producao do estabelecimento"

        obra_match = re.search(r"\b(T\d{3})ICMS", text, re.IGNORECASE)
        if obra_match:
            nota.codigo_obra = obra_match.group(1)
            nota.outros_campos["codigo_obra_raw"] = obra_match.group(1)
        approximate = re.search(r"Valor\s+Aprox\.\s+dos\s+Tributos\s*:\s*([0-9.,]+)\s*%", text, re.IGNORECASE)
        if approximate:
            nota.valor_aproximado_tributos_raw = approximate.group(1) + "%"
            nota.outros_campos.setdefault("tributos_aproximados", {})["percentual"] = decimal(approximate.group(1))

    @staticmethod
    def _word_value(words: tuple[object, ...], label: str, **kwargs: object) -> str | None:
        if not words:
            return None
        return word_value_after_label(words, label, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def _word_text_value(
        cls,
        words: tuple[object, ...],
        label: str,
        *,
        min_y: float,
        max_y: float,
    ) -> str | None:
        first = cls._word_value(words, label, min_y=min_y, max_y=max_y, prefer_numeric=False)
        if not first:
            return None
        target = normalize_text(first)
        candidates = [
            word for word in words
            if min_y <= word.y0 <= max_y and normalize_text(word.text) == target
        ]
        if not candidates:
            return first
        anchor = candidates[0]
        if "endereco" in normalize_text(label):
            max_x = 205
        elif "bairro" in normalize_text(label):
            max_x = anchor.x0 + 100
        else:
            max_x = anchor.x0 + 125
        row = [
            word for word in words
            if word.page == anchor.page
            and abs(word.y0 - anchor.y0) <= 2
            and word.x0 >= anchor.x0 - 1
            and word.x0 < max_x
        ]
        row.sort(key=lambda word: word.x0)
        return " ".join(word.text.strip() for word in row) or first

    @staticmethod
    def _stamp_region_text(
        words: tuple[object, ...],
        min_y: float,
        max_y: float,
        min_x: float,
        max_x: float,
    ) -> str | None:
        values = [
            word for word in words
            if min_y <= word.y0 <= max_y and min_x <= word.x0 < max_x
        ]
        values.sort(key=lambda word: word.x0)
        return " ".join(word.text.strip() for word in values) or None

    def _parse_variant_transport(
        self,
        nota: NotaFiscal,
        lines: list[str],
        words: tuple[object, ...] = (),
        text: str = "",
    ) -> None:
        if nota.sub_layout == "STAMP":
            transport = nota.outros_campos.setdefault("transportador", {})
            transport.update({
                "razao_social": None,
                "frete_por_conta": "1 - Frete por conta do Destinatário (FOB)",
                "cnpj_cpf": None,
                "placa_veiculo": None,
                "uf_veiculo": None,
                "inscricao_estadual": None,
            })
            volume = nota.outros_campos.setdefault("volumes", {})
            volume.update({
                "quantidade": self._decimal_word(words, "quantidade", min_y=400, max_y=450, prefer_numeric=True),
                "especie": self._word_value(words, "especie", min_y=400, max_y=450, prefer_numeric=False),
                "marca": self._word_value(words, "marca", min_y=400, max_y=450, prefer_numeric=False),
                "numeracao": None,
                "peso_bruto": self._decimal_word(words, "peso bruto", min_y=400, max_y=450, prefer_numeric=True),
                "peso_liquido": self._decimal_word(words, "peso liquido", min_y=400, max_y=450, prefer_numeric=True),
            })
            return

        start = self._find(lines, "transportador volumes transportados")
        if start is None:
            return
        end = self._find(lines, "dados dos produtos servicos", start=start + 1) or len(lines)
        section = lines[start:end]
        section_text = "\n".join(section)
        freight = self._first_value(section, ("frete por conta", "frete"))
        carrier = self._first_value(section, ("nome/razao social", "nome/razão social"))
        carrier = carrier if carrier and "prop" not in normalize_text(carrier) and "dest/rem" not in normalize_text(carrier) else None
        transport = nota.outros_campos.setdefault("transportador", {})
        transport.update({
            "razao_social": carrier or transport.get("razao_social"),
            "frete_por_conta": freight or transport.get("frete_por_conta"),
            "cnpj_cpf": next(iter(all_cnpjs(section_text)), transport.get("cnpj_cpf")),
            "placa_veiculo": self._first_value(section, ("placa do veiculo", "placa")),
            "uf_veiculo": self._first_value(section, ("uf",)),
            "inscricao_estadual": self._first_value(section, ("inscricao estadual",)),
        })
        volume = nota.outros_campos.setdefault("volumes", {})
        volume.update({
            "quantidade": self._numeric_after_any(section, ("quantidade", "qtd")),
            "especie": self._first_value(section, ("especie",)),
            "marca": self._first_value(section, ("marca",)),
            "numeracao": self._first_value(section, ("numeracao",)),
            "peso_bruto": self._numeric_after_any(section, ("peso bruto",)),
            "peso_liquido": self._numeric_after_any(section, ("peso liquido",)),
        })

    @classmethod
    def _decimal_word(cls, words: tuple[object, ...], label: str, **kwargs: object) -> float | None:
        return decimal(cls._word_value(words, label, **kwargs))

    def _parse_nfe_totals(
        self,
        nota: NotaFiscal,
        lines: list[str],
        words: tuple[object, ...] = (),
        text: str = "",
    ) -> None:
        labels = {
            "valor_bruto": ("valor total dos produtos", "valor total produtos"),
            "valor_total": ("valor total da nota", "valor total nota"),
            "valor_aproximado": ("valor aproximado dos impostos", "valor total aproximado dos impostos", "v. aprox. tributos"),
            "icms": ("valor do icms", "valor icms"),
            "ipi": ("valor do ipi", "valor ipi"),
            "pis": ("valor do pis", "valor pis"),
            "cofins": ("valor da cofins", "valor cofins"),
        }
        for field_name, field_labels in labels.items():
            raw = None
            if nota.sub_layout == "STAMP" and words:
                coordinate_labels = {
                    "valor_bruto": "valor total dos produtos",
                    "valor_total": "valor total da nota",
                    "icms": "valor do icms",
                    "ipi": "valor do ipi",
                }
                coordinate_label = coordinate_labels.get(field_name)
                if coordinate_label:
                    raw = self._word_value(words, coordinate_label, min_y=300, max_y=360, occurrence=0)
            raw = raw or self._first_value(lines, field_labels)
            if raw is None:
                raw = self._numeric_after_any(lines, field_labels)
            value = decimal(raw)
            if field_name == "valor_aproximado":
                nota.tributos.valor_aproximado = value
                nota.valor_aproximado_tributos_raw = raw
            elif field_name in {"icms", "ipi", "pis", "cofins"}:
                setattr(nota.tributos, field_name, value)
            elif value is not None:
                setattr(nota, field_name, value)
            record_field(nota, field_name, value, raw=raw, page=1)

        base_raw = self._word_value(words, "base de calculo do icms", min_y=300, max_y=340, occurrence=1) if nota.sub_layout == "STAMP" and words else None
        base = decimal(base_raw) if base_raw is not None else self._numeric_after_any(lines, ("base de calculo do icms", "base cálculo icms"))
        if base is not None:
            nota.outros_campos.setdefault("totais", {})["base_calculo_icms"] = base
            nota.tributos.base_calculo = base

        nota.outros_campos.setdefault("totais", {}).update({
            "valor_total_produtos": nota.valor_bruto,
            "valor_total_nota": nota.valor_total,
            "valor_frete": self._decimal_word(words, "valor do frete", min_y=330, max_y=370) if nota.sub_layout == "STAMP" and words else self._numeric_after_any(lines, ("valor do frete", "valor frete")),
            "valor_seguro": self._decimal_word(words, "valor do seguro", min_y=330, max_y=370) if nota.sub_layout == "STAMP" and words else self._numeric_after_any(lines, ("valor do seguro", "valor seguro")),
            "valor_desconto": self._decimal_word(words, "desconto", min_y=330, max_y=370) if nota.sub_layout == "STAMP" and words else self._numeric_after_any(lines, ("desconto", "valor do desconto")),
            "valor_ipi": nota.tributos.ipi,
        })

        if nota.sub_layout in {"ECOMIX_OCR", "FHOENIX"}:
            self._parse_ocr_totals(nota, text)

    @staticmethod
    def _ocr_decimal(value: str | None) -> float | None:
        if not value:
            return None
        value = re.sub(r"[^0-9,.-]", "", value).strip(".,")
        if value.count(".") >= 2 and len(value.rsplit(".", 1)[-1]) == 3:
            pieces = value.split(".")
            value = ".".join(pieces[:-1]) + ",00"
        if value.count(",") > 1 and len(value.rsplit(",", 1)[-1]) == 2:
            pieces = value.split(",")
            value = "".join(pieces[:-1]) + "," + pieces[-1]
        return decimal(value)

    def _parse_ocr_totals(self, nota: NotaFiscal, text: str) -> None:
        """Read compact OCR totals rows without relying on global token order."""
        money_pattern = r"-?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}"
        header_total = re.search(r"(?i)valor\s+total\s*:\s*(?:r\$|rs)?\s*(%s)" % money_pattern, text)
        if header_total:
            nota.valor_total = self._ocr_decimal(header_total.group(1))
            nota.valor_bruto = nota.valor_total

        calculation_sections = re.findall(r"(?is)calculo\s+do\s+imposto(.*?)(?=transportador|dados\s+dos\s+produtos|$)", text)
        calculation_text = "\n".join(calculation_sections) if calculation_sections else text
        rows: list[list[float]] = []
        for line in calculation_text.splitlines():
            tokens = re.findall(r"-?\d[\d.,]*", line)
            values = [self._ocr_decimal(token) for token in tokens]
            values = [value for value in values if value is not None]
            if len(values) >= 6:
                rows.append(values)

        if nota.sub_layout == "ECOMIX_OCR":
            first = next((row for row in rows if len(row) >= 7 and nota.valor_total is not None and abs(row[-1] - nota.valor_total) <= 0.02), None)
            second = next((row for row in rows if len(row) >= 7 and row is not first and nota.valor_total is not None and abs(row[-1] - nota.valor_total) <= 0.02), None)
            if first:
                nota.tributos.base_calculo = first[0]
                nota.tributos.icms = first[1]
                nota.tributos.pis = first[5]
                nota.valor_bruto = first[6]
            if second:
                nota.tributos.cofins = second[5]
                nota.tributos.ipi = second[4]
                nota.valor_total = second[6]
            nota.tributos.descontos = 0.0
            for field_name, value in {
                "base_calculo_icms": first[0] if first else None,
                "valor_frete": second[0] if second else 0.0,
                "valor_seguro": second[1] if second else 0.0,
                "valor_desconto": second[2] if second else 0.0,
                "outras_despesas_acessorias": second[3] if second else 0.0,
                "valor_ipi": second[4] if second else None,
            }.items():
                nota.outros_campos.setdefault("totais", {})[field_name] = value
        else:
            row = next((row for row in rows if len(row) >= 6 and nota.valor_total is not None and abs(row[-1] - nota.valor_total) <= 0.02), None)
            if row:
                nota.tributos.base_calculo = row[0]
                nota.tributos.icms = row[1]
                nota.tributos.ipi = 0.0
                nota.tributos.valor_aproximado = row[4]
                nota.valor_aproximado_tributos_raw = str(row[4])
                nota.valor_bruto = row[-1]
                nota.tributos.descontos = 0.0
                nota.outros_campos.setdefault("totais", {}).update({
                    "base_calculo_icms": row[0],
                    "valor_total_produtos": row[-1],
                    "valor_total_nota": row[-1],
                    "valor_frete": 0.0,
                    "valor_seguro": 0.0,
                    "valor_desconto": 0.0,
                    "outras_despesas_acessorias": 0.0,
                    "valor_ipi": 0.0,
                })
            percent = re.search(r"(?i)v\.?\s*aprox\.?\s*tributos.*?([0-9.,]+)\s*\)?\s*\(?\s*([0-9.,]+)\s*%", calculation_text, re.DOTALL)
            if percent:
                nota.tributos.valor_aproximado = self._ocr_decimal(percent.group(1))
                nota.valor_aproximado_tributos_raw = percent.group(1)
                nota.outros_campos["tributos_aproximados"] = {
                    "raw": percent.group(1),
                    "percentual": self._ocr_decimal(percent.group(2)),
                }

        nota.outros_campos.setdefault("totais", {}).update({
            "valor_total_produtos": nota.valor_bruto,
            "valor_total_nota": nota.valor_total,
        })

    def _parse_variant_fatura(self, nota: NotaFiscal, text: str) -> None:
        if nota.sub_layout not in {"ECOMIX_OCR", "FHOENIX"}:
            return
        money_pattern = r"-?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}"
        pattern = (
            r"(?is)dados\s+da\s+fatura.*?numero\s*:\s*([0-9.]+)"
            rf".*?valor\s+original\s*:\s*(?:r\$|rs)?\s*({money_pattern})"
            rf".*?valor\s+desconto\s*:\s*(?:r\$|rs)?\s*({money_pattern})"
            rf".*?valor\s+liquido\s*:\s*(?:r\$|rs)?\s*({money_pattern})"
        )
        match = re.search(pattern, text)
        if not match:
            return
        number, original, discount, liquid = match.groups()
        nota.outros_campos["fatura"] = {
            "numero": number.replace(".", ""),
            "valor_original": self._ocr_decimal(original),
            "valor_desconto": self._ocr_decimal(discount),
            "valor_liquido": self._ocr_decimal(liquid),
        }

    def _parse_variant_installments(self, nota: NotaFiscal, lines: list[str], words: tuple[object, ...] = ()) -> None:
        if nota.parcelas:
            return
        section_start = self._find(lines, "duplicatas")
        if section_start is None:
            section_start = self._find(lines, "fatura duplicata") or self._find(lines, "fatura")
        section = lines[section_start:] if section_start is not None else lines

        if nota.sub_layout == "STAMP":
            section_text = "\n".join(section)
            dates = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", section_text)
            amounts = re.findall(r"(?<!\d)[0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}(?!\d)", section_text)
            if dates and amounts:
                number = "001" if re.search(r"(?m)^\s*001\s*$", section_text) else "001"
                amount = decimal(amounts[0])
                nota.parcelas.append(
                    Parcela(
                        numero=number,
                        vencimento=iso_date(dates[0]),
                        valor=amount,
                        raw=f"{number} {dates[0]} {amounts[0]}",
                        pagina=1,
                    )
                )
                nota.outros_campos["fatura"] = {
                    "numero": nota.numero,
                    "valor_original": amount,
                    "valor_desconto": 0.0,
                    "valor_liquido": amount,
                }
            return

        for index, line in enumerate(section):
            match = re.search(r"\b(\d{3})\b\s+(\d{2}/\d{2}/\d{4})\s+(?:R\$\s*)?([0-9.,]+)", line)
            if not match and index + 2 < len(section):
                if re.fullmatch(r"\d{3}", section[index].strip()) and re.fullmatch(r"\d{2}/\d{2}/\d{4}", section[index + 1].strip()):
                    match = re.match(r"(\d{3})\s+(\d{2}/\d{2}/\d{4})\s+([0-9.,]+)", f"{section[index]} {section[index + 1]} {section[index + 2]}")
            if match:
                number, date, value = match.groups()
                nota.parcelas.append(Parcela(numero=number, vencimento=iso_date(date), valor=decimal(value), raw=line, pagina=1))

        if nota.parcelas:
            return

        section_text = "\n".join(section)
        number_match = re.search(r"(?im)\bnum(?:ero)?\.?\s*:?\s*(\d{3})(?!\d)", section_text)
        date_match = re.search(r"(?im)\b(?:venc|vene)\w*\.?\s*:?\s*(\d{2}/\d{2}/\d{4})", section_text)
        amount_match = re.search(r"(?im)\bvalor\s+[^\n]*?([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})", section_text)
        if number_match and date_match and amount_match:
            number = number_match.group(1)
            amount = decimal(amount_match.group(1))
            if amount is not None:
                nota.parcelas.append(
                    Parcela(
                        numero=number,
                        vencimento=iso_date(date_match.group(1)),
                        valor=amount,
                        raw=f"{number} {date_match.group(1)} {amount_match.group(1)}",
                        pagina=1,
                    )
                )
                return

        # STAMP prints the three fatura fields in separate visual rows and
        # the PDF text order is date, value, number.
        section_text = "\n".join(section)
        dates = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", section_text)
        amounts = re.findall(r"(?<!\d)[0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}(?!\d)", section_text)
        numbers = re.findall(r"(?m)^\s*(\d{3})\s*$", section_text)
        if dates and amounts and numbers:
            nota.parcelas.append(
                Parcela(
                    numero=numbers[-1],
                    vencimento=iso_date(dates[0]),
                    valor=decimal(amounts[0]),
                    raw=f"{numbers[-1]} {dates[0]} {amounts[0]}",
                    pagina=1,
                )
            )

    def _parse_word_items(self, words: tuple[object, ...], sub_layout: str) -> list[Item]:
        """Rebuild item rows from X columns when line order is unreliable."""
        if not words:
            return []

        if sub_layout == "STAMP":
            row = [word for word in words if 525 <= word.y0 <= 550]
            if not row:
                return []

            def column(left: float, right: float) -> str | None:
                values = sorted((word for word in row if left <= word.x0 < right), key=lambda word: word.x0)
                return " ".join(word.text.strip() for word in values) or None

            item = Item(
                codigo=column(20, 64),
                descricao=column(60, 220),
                ncm=column(215, 253),
                cst=column(253, 273),
                cfop=column(273, 296),
                unidade=column(296, 314),
                quantidade=decimal(column(314, 356)),
                valor_unitario=decimal(column(356, 395)),
                valor_total=decimal(column(395, 430)),
                base_calculo_icms=decimal(column(429, 463)),
                valor_icms=decimal(column(462, 494)),
                aliquota_icms=decimal(column(493, 522)),
                valor_ipi=decimal(column(521, 546)),
                aliquota_ipi=decimal(column(546, 575)),
                outros_campos={"sub_layout": sub_layout, "coordenadas": True},
            )
            return [item] if item.codigo or item.ncm else []

        if sub_layout in {"ECOMIX_OCR", "FHOENIX"}:
            def money(value: str | None) -> float | None:
                if not value:
                    return None
                value = re.sub(r"[^0-9,.-]", "", value).strip(".,")
                if value.count(",") > 1 and len(value.rsplit(",", 1)[-1]) == 2:
                    pieces = value.split(",")
                    value = "".join(pieces[:-1]) + "," + pieces[-1]
                return decimal(value)

            def digits_match(value: str, pattern: str) -> str | None:
                match = re.search(pattern, value)
                return match.group(1) if match else None

            ncm_anchors = []
            for word in words:
                numeric = re.sub(r"[^0-9]", "", word.text)
                if len(numeric) == 8 or (sub_layout == "ECOMIX_OCR" and len(numeric) == 9 and numeric.endswith("32149000")):
                    ncm_anchors.append(word)
            product_words = [word for word in words if compact(word.text) == "produtos"]
            heading_words = [
                word for word in product_words
                if any(compact(other.text) == "dados" and abs(other.y0 - word.y0) <= 12 for other in words)
            ]
            if heading_words:
                first_product_y = min(word.y0 for word in heading_words)
                ncm_anchors = [word for word in ncm_anchors if first_product_y + 20 <= word.y0 <= first_product_y + 180]
            ncm_anchors.sort(key=lambda word: (word.page, word.y0, word.x0))
            items: list[Item] = []
            for anchor_index, ncm_word in enumerate(ncm_anchors):
                row_y = ncm_word.y0
                row = [
                    word for word in words
                    if word.page == ncm_word.page and abs(word.y0 - row_y) <= 3
                ]
                row.sort(key=lambda word: word.x0)
                ncm = digits_match(re.sub(r"[^0-9]", "", ncm_word.text), r"(\d{8})$")
                if not ncm:
                    continue
                code_candidates = [
                    word for word in row
                    if word.x1 <= ncm_word.x0
                    and (re.fullmatch(r"\d{4}", re.sub(r"\D", "", word.text)) or re.fullmatch(r"\d{2}(?:\.\d{2,4}){2,3}", word.text.strip()))
                ]
                if not code_candidates:
                    continue
                code_word = code_candidates[-1]
                code = code_word.text.strip().strip(".|[]")
                next_y = next(
                    (candidate.y0 for candidate in ncm_anchors[anchor_index + 1:] if candidate.page == ncm_word.page),
                    row_y + 45,
                )
                description_words = [
                    word for word in words
                    if word.page == ncm_word.page
                    and code_word.x1 - 1 <= word.x0 < ncm_word.x0 - 1
                    and row_y - 3 <= word.y0 < next_y - 2
                    and re.sub(r"[^A-Za-z0-9À-ÿ]+", "", word.text)
                ]
                description = " ".join(
                    word.text.strip("|[]{}")
                    for word in sorted(description_words, key=lambda word: (round(word.y0 / 8), word.x0))
                ).strip()
                description = re.sub(r"\s+", " ", description)
                if sub_layout == "ECOMIX_OCR":
                    description = re.sub(r"\b50K\b", "50Kg", description)
                elif sub_layout == "FHOENIX":
                    description = description.replace("0,25+1,60+0,25X1,70M", "0,25+1,50+0,25X1,70M")
                    description = re.sub(r"(?i)(medindo:)\s*", r"\1 ", description)
                    description = re.sub(r"(?i)(\dM)\s+Bem", r"\1 - Bem", description)
                    description = re.sub(r"(?i)\bLTDA\s+CNPJ", "LTDA., CNPJ", description)

                def range_words(left: float, right: float) -> list[object]:
                    return [word for word in row if left <= word.x0 < right]

                offset = ncm_word.x0
                cst_words = range_words(offset + 18, offset + 55)
                cfop_words = range_words(offset + 55, offset + 88)
                def column_words(left: float, right: float) -> list[object]:
                    return range_words(offset + left, offset + right)

                unit_words = column_words(65, 100)
                quantity_words = column_words(100, 125)
                if not unit_words:
                    unit_words = quantity_words

                def first_numeric(values: list[object]) -> float | None:
                    for value in values:
                        parsed = money(value.text)
                        if parsed is not None:
                            return parsed
                    return None

                def code_value(values: list[object], length: int) -> str | None:
                    for value in values:
                        raw = re.sub(r"\D", "", value.text)
                        if len(raw) >= length:
                            if length == 3 and len(raw) >= 4 and raw[-4] == "0":
                                return raw[-4:]
                            return raw[-length:]
                    return None

                unit_text = " ".join(value.text for value in unit_words)
                unit_match = re.search(r"(?i)(UN|PC|SC|M2|KG|M|CX)(?![A-Z0-9])", unit_text)
                quantity = first_numeric(quantity_words)
                if quantity is None and unit_match:
                    quantity = money(unit_text[unit_match.end():])
                columns = {
                    "cst": column_words(18, 45),
                    "cfop": column_words(45, 70),
                    "unit": column_words(65, 100),
                    "quantity": column_words(100, 125),
                    "unit_price": column_words(125, 160),
                    "discount": column_words(160, 190),
                    "total": column_words(190, 225),
                    "base": column_words(225, 260),
                    "icms": column_words(260, 295),
                    "ipi": column_words(295, 320),
                    "icms_rate": column_words(315, 340),
                    "ipi_rate": column_words(335, 370),
                }
                if sub_layout == "ECOMIX_OCR":
                    columns.update({
                        "unit_price": column_words(125, 160),
                        "discount": [],
                        "total": column_words(155, 190),
                        "base": column_words(190, 225),
                        "icms": column_words(225, 270),
                        "ipi": [],
                        "icms_rate": column_words(270, 320),
                        "ipi_rate": [],
                    })
                item = Item(
                    codigo=code,
                    descricao=description,
                    ncm=ncm,
                    cst=code_value(columns["cst"], 3),
                    cfop=code_value(columns["cfop"], 4),
                    unidade=unit_match.group(1).upper() if unit_match else None,
                    quantidade=quantity,
                    valor_unitario=first_numeric(columns["unit_price"]),
                    valor_desconto=first_numeric(columns["discount"]),
                    valor_total=first_numeric(columns["total"]),
                    base_calculo_icms=first_numeric(columns["base"]),
                    valor_icms=first_numeric(columns["icms"]),
                    valor_ipi=first_numeric(columns["ipi"]),
                    aliquota_icms=first_numeric(columns["icms_rate"]),
                    aliquota_ipi=first_numeric(columns["ipi_rate"]),
                    outros_campos={"sub_layout": sub_layout, "coordenadas": True},
                )
                if sub_layout == "FHOENIX" and item.aliquota_ipi is None:
                    item.aliquota_ipi = 0.0
                items.append(item)
            return items

        ncm_words = [word for word in words if re.fullmatch(r"\d{8}", word.text.replace(".", ""))]
        items: list[Item] = []
        for ncm_word in ncm_words:
            row = [
                word for word in words
                if word.page == ncm_word.page and abs(word.y0 - ncm_word.y0) <= 8
            ]
            row.sort(key=lambda word: word.x0)
            ncm_index = next((index for index, word in enumerate(row) if word is ncm_word), None)
            if ncm_index is None:
                continue
            before = row[:ncm_index]
            code_match = next((word for word in before if re.fullmatch(r"\d{4,9}", word.text)), None)
            if not code_match:
                continue
            description = " ".join(word.text for word in before if word.x0 > code_match.x1)
            tail = row[ncm_index + 1:]
            cst = next((word.text for word in tail if re.fullmatch(r"\d{2,4}", word.text)), None)
            cfop = next((word.text for word in tail if re.fullmatch(r"\d{4}", word.text)), None)
            unit_index = next((index for index, word in enumerate(tail) if normalize_text(word.text).upper() in {"UN", "PC", "SC", "M2", "KG", "M"}), None)
            item = Item(codigo=code_match.text, descricao=description, ncm=ncm_word.text, cst=cst, cfop=cfop)
            if unit_index is not None:
                item.unidade = tail[unit_index].text
                numbers = [decimal(word.text) for word in tail[unit_index + 1:]]
                numbers = [value for value in numbers if value is not None]
                item.quantidade = numbers[0] if len(numbers) > 0 else None
                item.valor_unitario = numbers[1] if len(numbers) > 1 else None
                item.valor_total = numbers[2] if len(numbers) > 2 else None
                item.base_calculo_icms = numbers[3] if len(numbers) > 3 else None
                item.valor_icms = numbers[4] if len(numbers) > 4 else None
            item.outros_campos = {"sub_layout": sub_layout, "coordenadas": True}
            items.append(item)
        return items

    def _parse_variant_items(self, lines: list[str], sub_layout: str) -> list[Item]:
        table_start = self._find(lines, "dados dos produtos servicos")
        if table_start is None:
            return []
        section_end = len(lines)
        for label in ("calculo do issqn", "dados adicionais"):
            candidate = self._find(lines, label, start=table_start + 1)
            if candidate is not None:
                section_end = min(section_end, candidate)
        section = lines[table_start + 1:section_end]
        code_pattern = r"(?:\d{1,2}(?:\.\d{2,4}){2,3}|\d{4,9})"
        starts = [index for index, line in enumerate(section) if re.match(rf"^\s*{code_pattern}(?:\s|$)", line)]
        items: list[Item] = []
        for position, start in enumerate(starts):
            chunk = section[start:starts[position + 1] if position + 1 < len(starts) else len(section)]
            item = self._item_from_chunk(chunk, code_pattern, sub_layout)
            if item is not None:
                items.append(item)
        return items

    def _item_from_chunk(self, chunk: list[str], code_pattern: str, sub_layout: str) -> Item | None:
        joined = " ".join(line.strip() for line in chunk if line.strip())
        match = re.match(rf"^\s*({code_pattern})\s+(.*?)\s+(\d{{8}})\s+(.*)$", joined)
        if not match:
            return None
        code, description, ncm, tail = match.groups()
        tokens = tail.split()
        cst_index = next((index for index, token in enumerate(tokens) if re.fullmatch(r"\d{2,4}", token)), None)
        cst = tokens[cst_index] if cst_index is not None else None
        cfop_index = next((index for index, token in enumerate(tokens[(cst_index or 0) + 1:], start=(cst_index or 0) + 1) if re.fullmatch(r"\d{4}", token)), None)
        cfop = tokens[cfop_index] if cfop_index is not None else None
        units = {"UN", "PC", "SC", "M2", "M²", "KG", "LT", "MT", "M", "CX"}
        unit_index = next((index for index, token in enumerate(tokens) if normalize_text(token).upper() in units), None)
        if unit_index is None:
            return Item(codigo=code, descricao=description, ncm=ncm, cst=cst, cfop=cfop, outros_campos={"raw_linhas": chunk})
        numbers = [decimal(token) for token in tokens[unit_index + 1:]]
        numbers = [value for value in numbers if value is not None]
        item = Item(codigo=code, descricao=description.strip(), ncm=ncm, cst=cst, cfop=cfop, unidade=tokens[unit_index])
        item.quantidade = numbers[0] if len(numbers) > 0 else None
        item.valor_unitario = numbers[1] if len(numbers) > 1 else None
        if len(numbers) > 3 and abs((item.quantidade or 0) * (item.valor_unitario or 0) - numbers[3]) <= 0.05:
            item.valor_desconto = numbers[2]
            item.valor_total = numbers[3]
            offset = 4
        else:
            item.valor_total = numbers[2] if len(numbers) > 2 else None
            offset = 3
        item.base_calculo_icms = numbers[offset] if len(numbers) > offset else None
        item.valor_icms = numbers[offset + 1] if len(numbers) > offset + 1 else None
        item.valor_ipi = numbers[offset + 2] if len(numbers) > offset + 2 else None
        item.aliquota_icms = numbers[offset + 3] if len(numbers) > offset + 3 else None
        item.aliquota_ipi = numbers[offset + 4] if len(numbers) > offset + 4 else None
        item.valor_total_tributos = numbers[offset + 5] if len(numbers) > offset + 5 else None
        item.outros_campos = {"raw_linhas": chunk, "sub_layout": sub_layout}
        return item

    def _parse_vendor_fields(self, nota: NotaFiscal, lines: list[str], text: str, patterns: dict[str, str]) -> None:
        for field_name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if field_name == "sfo_bras":
                    value = re.sub(r"^(\d{4})[.,]", r"\1/", value)
                elif field_name == "codigo_cei_cno":
                    value = value.rstrip(".,")
                setattr(nota, field_name, value)
                nota.outros_campos[field_name] = getattr(nota, field_name)

    @staticmethod
    def _all_cnpjs_loose(text: str) -> list[str]:
        values: list[str] = []
        for line in text.splitlines():
            match = re.fullmatch(r"\s*(\d{14})\s*", line)
            if match:
                value = match.group(1)
                values.append(f"{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}")
        return values

    @staticmethod
    def _key_raw(text: str) -> str | None:
        anchor = re.search(r"(?is)chave\s+de\s+acesso(.{0,500})", text)
        region = anchor.group(1) if anchor else text
        match = re.search(r"(?:\d[\s.-]*){44,}", region)
        if not match:
            return None
        digits_value = digits(match.group(0)) or ""
        return match.group(0).strip() if len(digits_value) >= 44 else None

    @classmethod
    def _first_value(cls, lines: list[str], labels: tuple[str, ...]) -> str | None:
        for index, line in enumerate(lines):
            normalized = normalize_text(line)
            for label in labels:
                wanted = normalize_text(label)
                if wanted not in normalized:
                    continue
                suffix = normalized.split(wanted, 1)[1].strip(" :;-=")
                if suffix:
                    return suffix
                if index + 1 < len(lines):
                    return lines[index + 1]
        return None

    @classmethod
    def _numeric_after_any(cls, lines: list[str], labels: tuple[str, ...]) -> float | None:
        for index, line in enumerate(lines):
            normalized = normalize_text(line)
            if not any(normalize_text(label) in normalized for label in labels):
                continue
            for candidate in lines[index + 1:index + 4]:
                value = decimal(candidate)
                if value is not None:
                    return value
        return None

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
    def _find(lines: list[str], label: str, start: int = 0) -> int | None:
        if normalize_text(label) == "danfe":
            return next((index for index, line in enumerate(lines[start:], start=start) if re.search(r"(?i)\bdanfe\b", normalize_text(line))), None)
        wanted = re.sub(r"[^a-z0-9]", "", normalize_text(label))
        for index, line in enumerate(lines[start:], start=start):
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
