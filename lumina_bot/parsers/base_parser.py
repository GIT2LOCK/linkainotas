"""Base parser strategy for fiscal documents."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from abc import ABC
from dataclasses import dataclass
from typing import Any, ClassVar

from lumina_bot.core.document_detector import DocumentDetection, DocumentType
from lumina_bot.core.pdf_reader import PdfReadResult
from lumina_bot.models.nota import NotaFiscal


@dataclass(frozen=True, slots=True)
class ParseContext:
    """Input context passed to parser strategies."""

    text: str
    file_name: str
    detection: DocumentDetection
    pdf: PdfReadResult
    remote_path: str | None = None
    local_path: str | None = None
    xml_text: str | None = None
    xml_local_path: str | None = None


class BaseParser(ABC):
    """Base strategy with common extraction helpers."""

    document_type: ClassVar[DocumentType] = DocumentType.DESCONHECIDO
    parser_name: ClassVar[str] = "base"

    COMMON_LABELS: ClassVar[dict[str, tuple[str, ...]]] = {
        "numero": ("numero", "no.", "nro", "nota fiscal n"),
        "serie": ("serie", "serie da nota"),
        "modelo": ("modelo", "mod"),
        "protocolo": ("protocolo", "protocolo de autorizacao"),
        "autorizacao": ("autorizacao", "codigo de verificacao"),
        "data_emissao": ("data de emissao", "emissao", "data emissao"),
        "hora_emissao": ("hora de emissao", "hora emissao"),
        "competencia": ("competencia", "mes de competencia"),
        "razao_social": ("razao social", "nome empresarial"),
        "nome_fantasia": ("nome fantasia",),
        "cnae": ("cnae", "codigo cnae", "cnae fiscal"),
        "municipio": ("municipio", "cidade"),
        "uf": ("uf", "estado"),
        "codigo_municipio": ("codigo municipio", "cod municipio"),
        "codigo_servico": ("codigo do servico", "codigo servico", "cod servico"),
        "descricao_servico": ("descricao do servico", "descricao servico"),
        "discriminacao": ("discriminacao", "descricao dos servicos"),
        "valor_bruto": ("valor bruto", "valor dos servicos", "valor total"),
        "valor_liquido": ("valor liquido", "valor liquido da nota"),
        "base_calculo": ("base de calculo", "base calculo"),
        "aliquota": ("aliquota",),
        "iss": ("iss", "valor iss"),
        "inss": ("inss",),
        "pis": ("pis",),
        "cofins": ("cofins",),
        "csll": ("csll",),
        "irrf": ("irrf", "imposto de renda"),
        "retencoes": ("retencoes", "outras retencoes"),
        "descontos": ("descontos", "desconto"),
        "observacoes": ("observacoes", "informacoes complementares"),
    }

    MONEY_FIELDS: ClassVar[set[str]] = {
        "valor_bruto",
        "valor_liquido",
        "base_calculo",
        "aliquota",
        "iss",
        "inss",
        "pis",
        "cofins",
        "csll",
        "irrf",
        "retencoes",
        "descontos",
    }

    def parse(self, context: ParseContext) -> NotaFiscal:
        """Parse text/XML into a normalized fiscal document."""
        nota = NotaFiscal(
            tipo_documento=self.document_type.value,
            parser=self.parser_name,
            arquivo=context.file_name,
            caminho_remoto=context.remote_path,
            caminho_local=context.local_path,
            caminho_xml_local=context.xml_local_path,
            sha256=context.pdf.sha256,
            tamanho_bytes=context.pdf.size_bytes,
            quantidade_paginas=context.pdf.page_count,
            ocr_required=context.pdf.ocr_required,
            autor_pdf=context.pdf.author,
            criador_pdf=context.pdf.creator,
            producer_pdf=context.pdf.producer,
            metadados_pdf=context.pdf.metadata,
        )
        nota.outros_campos["pdf_extracao"] = {
            "paginas": context.pdf.page_count,
            "palavras_com_bbox": len(context.pdf.words),
            "camada_textual_disponivel": not context.pdf.ocr_required,
        }

        self._apply_common_fields(nota, context.text)

        if context.xml_text:
            self._apply_xml_fields(nota, context.xml_text)

        self._parse_specific(nota, context)
        return nota

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        """Hook for concrete parsers."""

    def _apply_common_fields(self, nota: NotaFiscal, text: str) -> None:
        lines = self._lines(text)

        nota.chave = self._extract_key(text)
        nota.prestador.cnpj = self._first_cnpj(text)
        nota.prestador.cpf = self._first_cpf(text)

        for field_name, labels in self.COMMON_LABELS.items():
            value = self._value_after_labels(lines, labels)

            if value is None:
                continue

            if field_name in self.MONEY_FIELDS:
                parsed_value = self._parse_decimal(value)
                self._set_money_field(nota, field_name, parsed_value)
            elif hasattr(nota, field_name):
                setattr(nota, field_name, value)
            else:
                nota.outros_campos[field_name] = value

        nota.prestador.razao_social = nota.prestador.razao_social or self._value_after_labels(
            lines,
            ("prestador", "emitente", "razao social"),
        )
        nota.tomador.razao_social = nota.tomador.razao_social or self._value_after_labels(
            lines,
            ("tomador", "destinatario", "sacado"),
        )

    def _apply_xml_fields(self, nota: NotaFiscal, xml_text: str) -> None:
        try:
            root = ET.fromstring(xml_text.encode("utf-8"))
        except ET.ParseError:
            nota.outros_campos["xml_parse_error"] = "invalid xml"
            return

        values = self._flatten_xml(root)
        nota.outros_campos["xml_campos_extraidos"] = values

        self._apply_xml_identity(nota, root, values)
        self._apply_xml_parties(nota, root)
        self._apply_xml_service(nota, root, values)
        self._apply_xml_taxes(nota, root, values)

    def _apply_xml_identity(
        self,
        nota: NotaFiscal,
        root: ET.Element,
        values: dict[str, str],
    ) -> None:
        inf_nfse = self._first_descendant(root, "InfNfse", "InfDeclaracaoPrestacaoServico")
        ide = self._first_descendant(root, "ide")

        nota.numero = nota.numero or self._first_text(
            inf_nfse,
            "Numero",
            "NumeroNfse",
        )
        nota.numero = nota.numero or self._first_text(ide, "nNF", "cNF")
        nota.numero = nota.numero or self._first_xml(values, "nnf", "numero", "nnota")
        nota.serie = nota.serie or self._first_text(ide, "serie")
        nota.serie = nota.serie or self._first_xml(values, "serie")
        nota.modelo = nota.modelo or self._first_text(ide, "mod")
        nota.modelo = nota.modelo or self._xml_document_model(root)
        nota.chave = nota.chave or self._xml_key(values, root)
        nota.protocolo = nota.protocolo or self._first_xml(values, "nprot", "protocolo")
        nota.autorizacao = nota.autorizacao or self._first_text(
            inf_nfse,
            "CodigoVerificacao",
        )
        nota.data_emissao = nota.data_emissao or self._first_text(
            ide,
            "dhEmi",
            "dEmi",
        )
        nota.data_emissao = nota.data_emissao or self._first_text(
            inf_nfse,
            "DataEmissao",
        )
        nota.data_emissao = nota.data_emissao or self._first_xml(
            values,
            "dhemi",
            "demi",
            "dataemissao",
        )
        nota.competencia = nota.competencia or self._first_text(
            inf_nfse,
            "Competencia",
        )

    def _apply_xml_parties(self, nota: NotaFiscal, root: ET.Element) -> None:
        emit = self._first_descendant(root, "emit", "rem")
        dest = self._first_descendant(root, "dest")
        prestador = self._first_descendant(root, "PrestadorServico", "Prestador")
        tomador = self._first_descendant(root, "TomadorServico", "Tomador")

        self._apply_xml_party(
            nota.prestador,
            prestador or emit,
            address_names=("Endereco", "enderEmit", "enderReme"),
        )
        self._apply_xml_party(
            nota.tomador,
            tomador or dest,
            address_names=("Endereco", "EnderecoTomador", "enderDest"),
        )

    def _apply_xml_party(
        self,
        party: Any,
        element: ET.Element | None,
        *,
        address_names: tuple[str, ...],
    ) -> None:
        if element is None:
            return

        party.cnpj = party.cnpj or self._first_text(element, "Cnpj", "CNPJ")
        party.cpf = party.cpf or self._first_text(element, "Cpf", "CPF")
        party.inscricao_municipal = party.inscricao_municipal or self._first_text(
            element,
            "InscricaoMunicipal",
            "IM",
        )
        party.inscricao_estadual = party.inscricao_estadual or self._first_text(
            element,
            "IE",
            "InscricaoEstadual",
        )
        party.razao_social = party.razao_social or self._first_text(
            element,
            "RazaoSocial",
            "xNome",
            "Nome",
        )
        party.nome_fantasia = party.nome_fantasia or self._first_text(
            element,
            "NomeFantasia",
            "xFant",
        )
        party.telefone = party.telefone or self._first_text(element, "Telefone", "fone")
        party.email = party.email or self._first_text(element, "Email", "email")

        address = self._first_descendant(element, *address_names)

        if address is None:
            return

        party.endereco.logradouro = party.endereco.logradouro or self._first_text(
            address,
            "Endereco",
            "Logradouro",
            "xLgr",
        )
        party.endereco.numero = party.endereco.numero or self._first_text(
            address,
            "Numero",
            "nro",
        )
        party.endereco.complemento = party.endereco.complemento or self._first_text(
            address,
            "Complemento",
            "xCpl",
        )
        party.endereco.bairro = party.endereco.bairro or self._first_text(
            address,
            "Bairro",
            "xBairro",
        )
        party.endereco.cidade = party.endereco.cidade or self._first_text(
            address,
            "Municipio",
            "xMun",
        )
        party.endereco.municipio = party.endereco.municipio or party.endereco.cidade
        party.endereco.uf = party.endereco.uf or self._first_text(address, "Uf", "UF")
        party.endereco.cep = party.endereco.cep or self._first_text(address, "Cep", "CEP")
        party.endereco.codigo_municipio = (
            party.endereco.codigo_municipio
            or self._first_text(address, "CodigoMunicipio", "cMun")
        )
        party.endereco.pais = party.endereco.pais or self._first_text(address, "xPais")

    def _apply_xml_service(
        self,
        nota: NotaFiscal,
        root: ET.Element,
        values: dict[str, str],
    ) -> None:
        service = self._first_descendant(root, "Servico")
        first_product = self._first_descendant(root, "prod")

        nota.codigo_municipio = nota.codigo_municipio or self._first_text(
            service,
            "CodigoMunicipio",
            "CodigoMunicipioIncidencia",
        )
        nota.codigo_servico = nota.codigo_servico or self._first_text(
            service,
            "ItemListaServico",
            "CodigoTributacaoMunicipio",
            "CodigoServico",
            "cServ",
        )
        nota.codigo_servico = nota.codigo_servico or self._first_text(
            first_product,
            "cProd",
        )
        nota.descricao_servico = nota.descricao_servico or self._first_text(
            service,
            "DescricaoServico",
            "Discriminacao",
            "xServ",
        )
        nota.descricao_servico = nota.descricao_servico or self._first_text(
            first_product,
            "xProd",
        )
        nota.discriminacao = nota.discriminacao or self._first_text(
            service,
            "Discriminacao",
        )
        nota.outros_campos["cnae"] = nota.outros_campos.get("cnae") or self._first_text(
            service,
            "CodigoCnae",
            "Cnae",
            "CNAE",
        )
        nota.outros_campos["cnae"] = nota.outros_campos.get("cnae") or self._first_xml(
            values,
            "cnae",
            "cnaefiscal",
            "codigocnae",
        )

    def _apply_xml_taxes(
        self,
        nota: NotaFiscal,
        root: ET.Element,
        values: dict[str, str],
    ) -> None:
        service_values = self._first_descendant(root, "Valores")
        icms_total = self._first_descendant(root, "ICMSTot")
        iss_total = self._first_descendant(root, "ISSQNtot")

        nota.valor_bruto = nota.valor_bruto or self._first_decimal(
            self._first_text(service_values, "ValorServicos"),
            self._first_text(iss_total, "vServ"),
            self._first_text(icms_total, "vProd"),
            self._first_xml(values, "valorservicos", "vserv", "vprod"),
        )
        nota.valor_liquido = nota.valor_liquido or self._first_decimal(
            self._first_text(service_values, "ValorLiquidoNfse", "ValorLiquido"),
            self._first_xml(values, "valorliquidonfse", "valorliquido"),
        )
        nota.valor_total = nota.valor_total or self._first_decimal(
            self._first_text(icms_total, "vNF"),
            self._first_text(service_values, "ValorServicos"),
            self._first_text(iss_total, "vServ"),
            self._first_xml(values, "vnf", "valorservicos", "vserv"),
        )
        nota.tributos.base_calculo = nota.tributos.base_calculo or self._first_decimal(
            self._first_text(service_values, "BaseCalculo"),
            self._first_text(iss_total, "vBC"),
            self._first_xml(values, "basecalculo", "vbc"),
        )
        nota.tributos.aliquota = nota.tributos.aliquota or self._first_decimal(
            self._first_text(service_values, "Aliquota"),
            self._first_text(iss_total, "vAliq"),
            self._first_xml(values, "aliquota", "valiq"),
        )
        nota.tributos.iss = nota.tributos.iss or self._first_decimal(
            self._first_text(service_values, "ValorIss", "ValorIssRetido"),
            self._first_text(iss_total, "vISS"),
            self._first_xml(values, "valoriss", "valorissretido", "viss"),
        )
        nota.tributos.inss = nota.tributos.inss or self._first_decimal(
            self._first_text(service_values, "ValorInss"),
            self._first_xml(values, "valorinss"),
        )
        nota.tributos.pis = nota.tributos.pis or self._first_decimal(
            self._first_text(service_values, "ValorPis"),
            self._first_text(iss_total, "vPIS"),
            self._first_xml(values, "valorpis", "vpis"),
        )
        nota.tributos.cofins = nota.tributos.cofins or self._first_decimal(
            self._first_text(service_values, "ValorCofins"),
            self._first_text(iss_total, "vCOFINS"),
            self._first_xml(values, "valorcofins", "vcofins"),
        )
        nota.tributos.csll = nota.tributos.csll or self._first_decimal(
            self._first_text(service_values, "ValorCsll"),
            self._first_xml(values, "valorcsll"),
        )
        nota.tributos.irrf = nota.tributos.irrf or self._first_decimal(
            self._first_text(service_values, "ValorIr"),
            self._first_xml(values, "valorir", "valorirrf"),
        )
        nota.tributos.retencoes = nota.tributos.retencoes or self._first_decimal(
            self._first_text(service_values, "OutrasRetencoes"),
            self._first_xml(values, "outrasretencoes", "retencoes"),
        )
        nota.tributos.descontos = nota.tributos.descontos or self._first_decimal(
            self._first_text(
                service_values,
                "DescontoIncondicionado",
                "DescontoCondicionado",
            ),
            self._first_text(icms_total, "vDesc"),
            self._first_xml(values, "descontoincondicionado", "descontocondicionado", "vdesc"),
        )
        nota.tributos.valor_aproximado = (
            nota.tributos.valor_aproximado
            or self._first_decimal(
                self._first_text(icms_total, "vTotTrib"),
                self._first_xml(values, "vtottrib"),
            )
        )

    def _set_money_field(
        self,
        nota: NotaFiscal,
        field_name: str,
        value: float | None,
    ) -> None:
        if value is None:
            return

        if hasattr(nota, field_name):
            setattr(nota, field_name, value)
        elif hasattr(nota.tributos, field_name):
            setattr(nota.tributos, field_name, value)

    @staticmethod
    def _lines(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _value_after_labels(
        self,
        lines: list[str],
        labels: tuple[str, ...],
    ) -> str | None:
        normalized_labels = tuple(self._normalize(label) for label in labels)

        for index, line in enumerate(lines):
            normalized_line = self._normalize(line)

            for label in normalized_labels:
                if label not in normalized_line:
                    continue

                same_line = self._after_separator(line)

                if same_line:
                    return same_line

                if index + 1 < len(lines):
                    return lines[index + 1].strip()

        return None

    @staticmethod
    def _after_separator(line: str) -> str | None:
        for separator in (":", "-", "="):
            if separator in line:
                value = line.split(separator, 1)[1].strip()
                return value or None

        return None

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = value.lower().replace("\xa0", " ")
        replacements = {
            "á": "a",
            "à": "a",
            "ã": "a",
            "â": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "õ": "o",
            "ô": "o",
            "ú": "u",
            "ç": "c",
        }

        for source, target in replacements.items():
            normalized = normalized.replace(source, target)

        return " ".join(normalized.split())

    @staticmethod
    def _first_cnpj(text: str) -> str | None:
        match = re.search(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", text)
        return match.group(0) if match else None

    @staticmethod
    def _first_cpf(text: str) -> str | None:
        match = re.search(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", text)
        return match.group(0) if match else None

    @staticmethod
    def _extract_key(text: str) -> str | None:
        compact = re.sub(r"\D", "", text)
        match = re.search(r"\d{44}", compact)
        return match.group(0) if match else None

    @staticmethod
    def _parse_decimal(value: str | None) -> float | None:
        if value is None:
            return None

        match = re.search(r"-?\d[\d.,]*", value)

        if not match:
            return None

        number = match.group(0)
        has_comma = "," in number
        has_dot = "." in number

        if has_comma and has_dot:
            if number.rfind(",") > number.rfind("."):
                number = number.replace(".", "").replace(",", ".")
            else:
                number = number.replace(",", "")
        elif has_comma:
            number = number.replace(".", "").replace(",", ".")
        elif number.count(".") > 1:
            number = number.replace(".", "")
        elif has_dot:
            integer_part, decimal_part = number.split(".", 1)

            if len(decimal_part) == 3 and 1 <= len(integer_part.lstrip("-")) <= 3:
                number = integer_part + decimal_part
        else:
            number = number.replace(".", "").replace(",", ".")

        try:
            return float(number)
        except ValueError:
            return None

    def _first_decimal(self, *values: str | None) -> float | None:
        for value in values:
            parsed = self._parse_decimal(value)

            if parsed is not None:
                return parsed

        return None

    @classmethod
    def _first_descendant(
        cls,
        parent: ET.Element | None,
        *names: str,
    ) -> ET.Element | None:
        if parent is None:
            return None

        normalized_names = {cls._normalize_xml_name(name) for name in names}

        for element in parent.iter():
            if element is parent:
                continue

            if cls._normalize_xml_name(element.tag) in normalized_names:
                return element

        return None

    @classmethod
    def _first_text(
        cls,
        parent: ET.Element | None,
        *names: str,
    ) -> str | None:
        element = cls._first_descendant(parent, *names)

        if element is None:
            return None

        text = (element.text or "").strip()
        return text or None

    @classmethod
    def _xml_document_model(cls, root: ET.Element) -> str | None:
        tag_names = {cls._normalize_xml_name(element.tag) for element in root.iter()}

        if {"nfe", "infnfe"} & tag_names:
            return "55"

        if {"nfse", "infnfse", "compnfse"} & tag_names:
            return "NFS-e"

        if {"cte", "infcte"} & tag_names:
            return "57"

        if {"mdfe", "infmdfe"} & tag_names:
            return "58"

        return None

    @staticmethod
    def _flatten_xml(root: ET.Element) -> dict[str, str]:
        values: dict[str, str] = {}

        for element in root.iter():
            tag = BaseParser._normalize_xml_name(element.tag)
            text = (element.text or "").strip()

            if text and tag not in values:
                values[tag] = text

            for attribute_name, attribute_value in element.attrib.items():
                attribute_key = f"{tag}_{attribute_name.lower()}"

                if attribute_value and attribute_key not in values:
                    values[attribute_key] = attribute_value

        return values

    @staticmethod
    def _first_xml(values: dict[str, str], *names: str) -> str | None:
        for name in names:
            value = values.get(BaseParser._normalize_xml_name(name))

            if value:
                return value

        return None

    @staticmethod
    def _xml_key(values: dict[str, str], root: ET.Element | None = None) -> str | None:
        if root is not None:
            for element in root.iter():
                identifier = element.attrib.get("Id") or element.attrib.get("id")

                if not identifier:
                    continue

                digits = re.sub(r"\D", "", identifier)

                if len(digits) >= 44:
                    return digits[:44]

        for key in ("chnfe", "chcte", "chmdfe"):
            value = values.get(key)

            if value:
                return value

        for value in values.values():
            digits = re.sub(r"\D", "", value)

            if len(digits) >= 44:
                return digits[:44]

        return None

    @staticmethod
    def _normalize_xml_name(value: str) -> str:
        return value.rsplit("}", 1)[-1].lower()
