"""Excel output writer for processed fiscal documents."""

from __future__ import annotations

import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from lumina_bot.core.logger import get_logger
from lumina_bot.models.nota import NotaFiscal


ExcelOutputMode = Literal["single_sheet", "multi_sheet", "one_file_per_pdf"]


class ExcelWriter:
    """Write fiscal document rows to Excel workbooks."""

    SUMMARY_COLUMNS = [
        "Arquivo",
        "Tipo Documento",
        "Parser",
        "Sub Layout",
        "OCR Usado",
        "Número",
        "Série",
        "Modelo",
        "Chave",
        "Chave Acesso Raw",
        "Data Emissão",
        "Competência",
        "RPS Número",
        "Município Emissor NFS-e",
        "Município Incidência ISS",
        "Código NBS",
        "Código Obra",
        "Código CEI/CNO",
        "SFOBRAS",
        "Valor Aproximado Tributos Raw",
        "CNPJ Prestador",
        "CPF Prestador",
        "Razão Social Prestador",
        "Nome Fantasia Prestador",
        "CNAE",
        "Inscrição Municipal Prestador",
        "Inscrição Estadual Prestador",
        "Cidade Prestador",
        "UF Prestador",
        "CNPJ Tomador",
        "CPF Tomador",
        "Razão Social Tomador",
        "Nome Fantasia Tomador",
        "Cidade Tomador",
        "UF Tomador",
        "Código Serviço",
        "Descrição Serviço",
        "Discriminação",
        "Valor Bruto",
        "Valor Líquido",
        "Valor Total",
        "Base Cálculo",
        "Alíquota",
        "ISS",
        "INSS",
        "PIS",
        "COFINS",
        "CSLL",
        "IRRF",
        "Retenções",
        "Descontos",
        "Observações",
        "Status",
        "Erro",
        "SHA256",
        "Caminho Local",
        "Caminho Remoto",
    ]

    MONEY_KEYWORDS = (
        "valor",
        "iss",
        "inss",
        "pis",
        "cofins",
        "csll",
        "irrf",
        "retencoes",
        "descontos",
        "base_calculo",
        "aliquota",
    )
    DATE_KEYWORDS = ("data", "competencia")

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path
        self._logger = get_logger(self.__class__.__name__)

    def append(self, notas: Iterable[NotaFiscal]) -> None:
        """Append rows to a single-sheet workbook without dropping existing rows."""
        self.write(notas, mode="single_sheet")

    def write(
        self,
        notas: Iterable[NotaFiscal],
        *,
        mode: ExcelOutputMode = "single_sheet",
    ) -> None:
        """Write notes using the selected Excel output mode."""
        rows = list(notas)

        if not rows:
            return

        if mode == "multi_sheet":
            self.write_multi_sheet(rows)
            return

        if mode == "one_file_per_pdf":
            self.write_one_file_per_pdf(rows)
            return

        self.write_structured(rows)

    def write_structured(self, notas: Iterable[NotaFiscal]) -> None:
        """Write the canonical workbook tabs without flattening child records."""
        rows = list(notas)
        if not rows:
            return

        documents = [self._summary_row(nota) | {
            "Layout": nota.layout,
            "Parcelas": len(nota.parcelas),
            "Validações": len(nota.validacoes),
        } for nota in rows]
        items: list[dict[str, Any]] = []
        installments: list[dict[str, Any]] = []
        taxes: list[dict[str, Any]] = []
        validations: list[dict[str, Any]] = []

        for nota in rows:
            identity = {
                "Arquivo": nota.arquivo,
                "Tipo Documento": nota.tipo_documento,
                "Layout": nota.layout,
                "Número": nota.numero,
                "Chave": nota.chave,
            }
            for item_index, item in enumerate(nota.itens, start=1):
                items.append(identity | {"Item": item_index} | item.to_dict())
            for parcela in nota.parcelas:
                installments.append(identity | parcela.to_dict())
            for name, value in nota.tributos.to_dict().items():
                if isinstance(value, dict):
                    for child_name, child_value in value.items():
                        taxes.append(identity | {"Tributo": f"{name}.{child_name}", "Valor": child_value})
                else:
                    taxes.append(identity | {"Tributo": name, "Valor": value})
            for validation in nota.validacoes:
                validations.append(identity | validation.to_dict())

        frames = {
            "documentos": pd.DataFrame(documents),
            "itens": pd.DataFrame(items, columns=[
                "Arquivo", "Tipo Documento", "Layout", "Número", "Chave", "Item",
                "codigo", "descricao", "ncm", "cfop", "unidade", "quantidade",
                "valor_unitario", "valor_desconto", "valor_total", "cst",
                "base_calculo_icms", "valor_icms", "valor_ipi", "aliquota_icms",
                "aliquota_ipi", "valor_total_tributos", "outros_campos",
            ]),
            "parcelas": pd.DataFrame(installments, columns=[
                "Arquivo", "Tipo Documento", "Layout", "Número", "Chave",
                "numero", "vencimento", "valor", "raw", "pagina",
            ]),
            "tributos": pd.DataFrame(taxes, columns=[
                "Arquivo", "Tipo Documento", "Layout", "Número", "Chave", "Tributo", "Valor",
            ]),
            "validacoes": pd.DataFrame(validations, columns=[
                "Arquivo", "Tipo Documento", "Layout", "Número", "Chave", "regra", "status",
                "valor_extraido", "valor_calculado", "mensagem",
            ]),
        }
        self._write_frames(frames)

    def _write_frames(self, frames: dict[str, pd.DataFrame], output_path: Path | None = None) -> None:
        path = output_path or self._output_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for sheet_name, frame in frames.items():
                frame.to_excel(writer, index=False, sheet_name=sheet_name)
        self._format_workbook(path)
        self._logger.info("Structured Excel updated: %s | sheets=%s", path, len(frames))

    def write_single_sheet(self, notas: Iterable[NotaFiscal]) -> None:
        """Append all documents to a single sheet."""
        rows = [self._summary_row(nota) for nota in notas]

        if not rows:
            return

        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        new_frame = pd.DataFrame(rows, columns=self.SUMMARY_COLUMNS)

        if self._output_path.is_file():
            try:
                existing_frame = pd.read_excel(self._output_path, sheet_name="notas")
            except ValueError:
                self._backup_incompatible_workbook()
                existing_frame = pd.DataFrame(columns=self.SUMMARY_COLUMNS)

            if self._is_compatible_summary_frame(existing_frame):
                frame = pd.concat([existing_frame, new_frame], ignore_index=True)
            else:
                self._backup_incompatible_workbook()
                frame = new_frame
        else:
            frame = new_frame

        with pd.ExcelWriter(self._output_path, engine="openpyxl") as writer:
            frame.to_excel(writer, index=False, sheet_name="notas")

        self._format_workbook()
        self._logger.info("Excel updated: %s | new rows=%s", self._output_path, len(rows))

    def write_multi_sheet(
        self,
        notas: Iterable[NotaFiscal],
        sheet_name_resolver: Callable[[NotaFiscal], str] | None = None,
    ) -> None:
        """Write all documents into one workbook with one sheet per document."""
        rows = list(notas)

        if not rows:
            return

        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        resolver = sheet_name_resolver or self._default_sheet_name
        used_names: set[str] = set()

        with pd.ExcelWriter(self._output_path, engine="openpyxl") as writer:
            for nota in rows:
                sheet_name = self._unique_sheet_name(resolver(nota), used_names)
                pd.DataFrame(
                    [self._summary_row(nota)],
                    columns=self.SUMMARY_COLUMNS,
                ).to_excel(
                    writer,
                    index=False,
                    sheet_name=sheet_name,
                )

        self._format_workbook()
        self._logger.info(
            "Multi-sheet Excel updated: %s | sheets=%s",
            self._output_path,
            len(rows),
        )

    def write_one_file_per_pdf(self, notas: Iterable[NotaFiscal]) -> None:
        """Create one Excel file for each processed document."""
        rows = list(notas)

        if not rows:
            return

        output_dir = self._output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        for nota in rows:
            file_name = self._safe_file_name(self._default_sheet_name(nota)) + ".xlsx"
            file_path = self._unique_file_path(output_dir / file_name)

            temporary_writer = ExcelWriter(file_path)
            temporary_writer.write_structured([nota])

        self._logger.info("One-file-per-PDF Excel export completed: %s", output_dir)

    def _format_workbook(self, path: Path | None = None) -> None:
        workbook_path = path or self._output_path

        if not workbook_path.is_file():
            return

        workbook = load_workbook(workbook_path)

        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions

            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(
                    fill_type="solid",
                    fgColor="F92B70",
                )
                cell.alignment = Alignment(horizontal="center", vertical="center")

            sheet.row_dimensions[1].height = 24

            for column_cells in sheet.columns:
                first_cell = column_cells[0]
                column_name = str(first_cell.value or "")
                column_letter = get_column_letter(first_cell.column)
                max_length = max(
                    len(str(cell.value)) if cell.value is not None else 0
                    for cell in column_cells
                )
                sheet.column_dimensions[column_letter].width = min(
                    max(max_length + 2, 12),
                    80,
                )

                for cell in column_cells[1:]:
                    cell.alignment = Alignment(vertical="top", wrap_text=False)

                if self._is_money_column(column_name):
                    for cell in column_cells[1:]:
                        cell.number_format = '#,##0.00'

                if self._is_date_column(column_name):
                    for cell in column_cells[1:]:
                        cell.number_format = "dd/mm/yyyy"

        workbook.save(workbook_path)

    def _default_sheet_name(self, nota: NotaFiscal) -> str:
        candidates = (
            nota.prestador.nome_fantasia,
            nota.prestador.razao_social,
            nota.tomador.razao_social,
            nota.numero,
            nota.arquivo,
            "Nota",
        )

        for candidate in candidates:
            if candidate:
                return str(candidate)

        return "Nota"

    def _summary_row(self, nota: NotaFiscal) -> dict[str, Any]:
        return {
            "Arquivo": nota.arquivo,
            "Tipo Documento": nota.tipo_documento,
            "Parser": nota.parser,
            "Sub Layout": nota.sub_layout,
            "OCR Usado": nota.ocr_used,
            "Número": nota.numero,
            "Série": nota.serie,
            "Modelo": nota.modelo,
            "Chave": nota.chave,
            "Chave Acesso Raw": nota.chave_acesso_raw,
            "Data Emissão": nota.data_emissao,
            "Competência": nota.competencia,
            "RPS Número": nota.rps_numero,
            "Município Emissor NFS-e": nota.municipio_emissor_nfse,
            "Município Incidência ISS": nota.municipio_incidencia_iss,
            "Código NBS": nota.codigo_nbs,
            "Código Obra": nota.codigo_obra,
            "Código CEI/CNO": nota.codigo_cei_cno,
            "SFOBRAS": nota.sfo_bras,
            "Valor Aproximado Tributos Raw": nota.valor_aproximado_tributos_raw,
            "CNPJ Prestador": nota.prestador.cnpj,
            "CPF Prestador": nota.prestador.cpf,
            "Razão Social Prestador": nota.prestador.razao_social,
            "Nome Fantasia Prestador": nota.prestador.nome_fantasia,
            "CNAE": self._extra_value(nota, "cnae", "codigo_cnae", "cnae_fiscal"),
            "Inscrição Municipal Prestador": nota.prestador.inscricao_municipal,
            "Inscrição Estadual Prestador": nota.prestador.inscricao_estadual,
            "Cidade Prestador": nota.prestador.endereco.cidade,
            "UF Prestador": nota.prestador.endereco.uf,
            "CNPJ Tomador": nota.tomador.cnpj,
            "CPF Tomador": nota.tomador.cpf,
            "Razão Social Tomador": nota.tomador.razao_social,
            "Nome Fantasia Tomador": nota.tomador.nome_fantasia,
            "Cidade Tomador": nota.tomador.endereco.cidade,
            "UF Tomador": nota.tomador.endereco.uf,
            "Código Serviço": nota.codigo_servico,
            "Descrição Serviço": nota.descricao_servico,
            "Discriminação": nota.discriminacao,
            "Valor Bruto": nota.valor_bruto,
            "Valor Líquido": nota.valor_liquido,
            "Valor Total": nota.valor_total,
            "Base Cálculo": nota.tributos.base_calculo,
            "Alíquota": nota.tributos.aliquota,
            "ISS": nota.tributos.iss,
            "INSS": nota.tributos.inss,
            "PIS": nota.tributos.pis,
            "COFINS": nota.tributos.cofins,
            "CSLL": nota.tributos.csll,
            "IRRF": nota.tributos.irrf,
            "Retenções": nota.tributos.retencoes,
            "Descontos": nota.tributos.descontos,
            "Observações": nota.observacoes,
            "Status": nota.status_processamento,
            "Erro": nota.erro_processamento,
            "SHA256": nota.sha256,
            "Caminho Local": nota.caminho_local,
            "Caminho Remoto": nota.caminho_remoto,
        }

    def _backup_incompatible_workbook(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self._output_path.with_name(
            f"{self._output_path.stem}_backup_layout_antigo_{timestamp}{self._output_path.suffix}"
        )
        shutil.copy2(self._output_path, backup_path)
        self._logger.info(
            "Existing Excel used an old layout and was backed up: %s",
            backup_path,
        )

    @classmethod
    def _is_compatible_summary_frame(cls, frame: pd.DataFrame) -> bool:
        return list(frame.columns) == cls.SUMMARY_COLUMNS

    def _unique_file_path(self, desired_path: Path) -> Path:
        if not desired_path.exists():
            return desired_path

        counter = 2
        candidate = desired_path.with_name(
            f"{desired_path.stem}_{counter}{desired_path.suffix}"
        )

        while candidate.exists():
            counter += 1
            candidate = desired_path.with_name(
                f"{desired_path.stem}_{counter}{desired_path.suffix}"
            )

        return candidate

    def _extra_value(self, nota: NotaFiscal, *keys: str) -> Any:
        for key in keys:
            direct = nota.outros_campos.get(key)

            if direct:
                return direct

        xml_values = nota.outros_campos.get("xml_campos_extraidos")

        if isinstance(xml_values, dict):
            for key in keys:
                value = xml_values.get(key)

                if value:
                    return value

        return None

    def _unique_sheet_name(self, desired_name: str, used_names: set[str]) -> str:
        base = self._safe_sheet_name(desired_name)
        name = base
        suffix = 2

        while name in used_names:
            suffix_text = f"_{suffix}"
            name = f"{base[:31 - len(suffix_text)]}{suffix_text}"
            suffix += 1

        used_names.add(name)
        return name

    @staticmethod
    def _safe_sheet_name(value: str) -> str:
        cleaned = re.sub(r"[\[\]:*?/\\]", " ", value).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return (cleaned or "Nota")[:31]

    @staticmethod
    def _safe_file_name(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_. -]+", "_", value).strip(" ._")
        return cleaned or "nota"

    def _is_money_column(self, column_name: str) -> bool:
        normalized = self._normalize_column_name(column_name)
        return any(keyword in normalized for keyword in self.MONEY_KEYWORDS)

    def _is_date_column(self, column_name: str) -> bool:
        normalized = self._normalize_column_name(column_name)
        return any(keyword in normalized for keyword in self.DATE_KEYWORDS)

    @staticmethod
    def _normalize_column_name(column_name: str) -> str:
        normalized = unicodedata.normalize("NFKD", column_name)
        normalized = "".join(
            character for character in normalized if not unicodedata.combining(character)
        )
        return normalized.lower().replace(" ", "_")
