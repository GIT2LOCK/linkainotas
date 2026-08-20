"""Document type detection for fiscal and financial PDFs."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

try:
    from rapidfuzz import fuzz
except ImportError:  # Keep the standalone parser usable on a fresh worker.
    from difflib import SequenceMatcher

    class _FuzzFallback:
        @staticmethod
        def ratio(left: str, right: str) -> float:
            return SequenceMatcher(None, left, right).ratio() * 100

        @staticmethod
        def partial_ratio(left: str, right: str) -> float:
            if not left or not right:
                return 0.0
            if len(left) > len(right):
                left, right = right, left
            window = len(left)
            return max(
                SequenceMatcher(None, left, right[index:index + window]).ratio() * 100
                for index in range(len(right) - window + 1)
            )

    fuzz = _FuzzFallback()


class DocumentType(str, Enum):
    """Supported document types."""

    NFE_DANFE_55 = "NFE_DANFE_55"
    NFSE_SP = "NFSE_SP"
    NFSE_COTIA_1P = "NFSE_COTIA_1P"
    UNKNOWN_LAYOUT = "UNKNOWN_LAYOUT"
    NFE = "NF-e"
    NFSE = "NFS-e"
    NFCE = "NFC-e"
    CTE = "CT-e"
    MDFE = "MDF-e"
    RECIBO = "Recibo"
    BOLETO = "Boleto"
    DESCONHECIDO = "Documento desconhecido"


@dataclass(frozen=True, slots=True)
class DocumentDetection:
    """Result of document type detection."""

    document_type: DocumentType
    confidence: float
    reason: str
    anchors_found: tuple[str, ...] = ()
    anchors_missing: tuple[str, ...] = ()
    sub_layout: str | None = None


class DocumentDetector:
    """Detects document type from text and file name signals."""

    KEYWORDS: dict[DocumentType, tuple[str, ...]] = {
        DocumentType.NFE: (
            "nota fiscal eletronica",
            "danfe",
            "chave de acesso",
            "protocolo de autorizacao",
            "nfeproc",
            "infnfe",
        ),
        DocumentType.NFSE: (
            "nota fiscal de servicos eletronica",
            "nfs-e",
            "codigo de verificacao",
            "prestador de servicos",
            "compnfse",
            "infnfse",
        ),
        DocumentType.NFCE: (
            "nota fiscal de consumidor eletronica",
            "nfc-e",
            "consulta pela chave de acesso",
        ),
        DocumentType.CTE: (
            "conhecimento de transporte eletronico",
            "ct-e",
            "dacte",
            "cteproc",
            "infcte",
        ),
        DocumentType.MDFE: (
            "manifesto eletronico de documentos fiscais",
            "mdf-e",
            "damdfe",
            "mdfeproc",
            "infmdfe",
        ),
        DocumentType.RECIBO: (
            "recibo",
            "recebemos de",
            "recebi de",
        ),
        DocumentType.BOLETO: (
            "boleto",
            "linha digitavel",
            "cedente",
            "sacado",
            "beneficiario",
        ),
    }

    def detect(self, text: str, file_name: str = "") -> DocumentDetection:
        """Detect a document type using keyword scoring and fuzzy matching."""
        normalized = self._normalize(f"{file_name}\n{text}")

        if not normalized:
            return DocumentDetection(
                document_type=DocumentType.DESCONHECIDO,
                confidence=0.0,
                reason="empty text",
            )

        fiscal_detection = self._detect_fiscal_layout(normalized)

        if fiscal_detection is not None:
            return fiscal_detection

        scores: dict[DocumentType, float] = {}

        for document_type, keywords in self.KEYWORDS.items():
            scores[document_type] = self._score(normalized, keywords)

        best_type, best_score = max(scores.items(), key=lambda item: item[1])

        if best_score < 35:
            return DocumentDetection(
                document_type=DocumentType.DESCONHECIDO,
                confidence=best_score,
                reason="no strong document markers",
            )

        return DocumentDetection(
            document_type=best_type,
            confidence=best_score,
            reason="keyword and fuzzy score",
        )

    @classmethod
    def _detect_fiscal_layout(cls, normalized: str) -> DocumentDetection | None:
        # Cotia must be evaluated before the generic São Paulo NFS-e anchors:
        # both documents share the Prestador/Tomador labels.
        cotia_anchors = (
            "prefeitura do municipio de cotia",
            "nota fiscal de servicos eletronica",
            "prestador de servicos",
            "tomador de servicos",
        )
        nfse_anchors = (
            "prefeitura do municipio de sao paulo",
            "nota fiscal eletronica de servicos",
            "prestador de servicos",
            "tomador de servicos",
        )
        nfe_anchors = (
            "danfe",
            "documento auxiliar da nota fiscal eletronica",
            "chave de acesso",
            "destinatario remetente",
            "dados dos produtos servicos",
        )

        cotia_found = tuple(anchor for anchor in cotia_anchors if cls._contains_anchor(normalized, anchor))
        nfse_found = tuple(anchor for anchor in nfse_anchors if cls._contains_anchor(normalized, anchor))
        nfe_found = tuple(anchor for anchor in nfe_anchors if cls._contains_anchor(normalized, anchor))

        cotia_municipality = cls._compact(cotia_anchors[0]) in cls._compact(normalized)
        if len(cotia_found) >= 3 and cotia_municipality:
            return DocumentDetection(
                document_type=DocumentType.NFSE_COTIA_1P,
                confidence=min(100.0, 70.0 + len(cotia_found) * 7.5),
                reason="NFSE_COTIA_1P fiscal layout anchors",
                anchors_found=cotia_found,
                anchors_missing=tuple(anchor for anchor in cotia_anchors if anchor not in cotia_found),
                sub_layout="COTIA_1P",
            )

        if len(nfse_found) >= 3:
            return DocumentDetection(
                document_type=DocumentType.NFSE_SP,
                confidence=min(100.0, 60.0 + len(nfse_found) * 10.0),
                reason="NFSE_SP fiscal layout anchors",
                anchors_found=nfse_found,
                anchors_missing=tuple(anchor for anchor in nfse_anchors if anchor not in nfse_found),
                sub_layout="SP_2P",
            )

        if len(nfe_found) >= 3:
            sub_layout = cls._danfe_sub_layout(normalized)
            return DocumentDetection(
                document_type=DocumentType.NFE_DANFE_55,
                confidence=min(100.0, 60.0 + len(nfe_found) * 8.0),
                reason="NFE_DANFE_55 fiscal layout anchors",
                anchors_found=nfe_found,
                anchors_missing=tuple(anchor for anchor in nfe_anchors if anchor not in nfe_found),
                sub_layout=sub_layout,
            )

        return None

    @classmethod
    def _danfe_sub_layout(cls, normalized: str) -> str:
        """Identify known DANFE variants without changing the canonical type."""
        if cls._contains_anchor(normalized, "ecomix argamassas ltda") or cls._contains_anchor(normalized, "ecomix"):
            return "ECOMIX_OCR"
        if cls._contains_anchor(normalized, "metalurgica fhoenix do brasil ltda") or cls._contains_anchor(normalized, "fhoenix"):
            return "FHOENIX"
        if cls._contains_anchor(normalized, "stamp pre fabricados arquitetonicos ltda") or cls._contains_anchor(normalized, "stamp pre fabricados"):
            return "STAMP"
        return "GENERIC"

    @classmethod
    def _contains_anchor(cls, text: str, anchor: str) -> bool:
        if cls._compact(anchor) == "danfe":
            return bool(re.search(r"(?i)(?:^|\s)danfe(?:\s|$)", cls._normalize(text)))
        normalized_text = cls._compact(text)
        normalized_anchor = cls._compact(anchor)

        if normalized_anchor in normalized_text:
            return True

        text_tokens = cls._tokens(text)
        anchor_tokens = cls._tokens(anchor)

        if not anchor_tokens or len(text_tokens) < len(anchor_tokens):
            return False

        # Compare contiguous token windows. Independent token matching causes
        # an NF-e with a "servicos" column to look like an NFS-e.
        anchor_value = " ".join(anchor_tokens)
        window_size = len(anchor_tokens)
        return any(
            fuzz.ratio(anchor_value, " ".join(text_tokens[index:index + window_size])) >= 90
            for index in range(len(text_tokens) - window_size + 1)
        )

    @staticmethod
    def _score(text: str, keywords: tuple[str, ...]) -> float:
        score = 0.0

        for keyword in keywords:
            if keyword in text:
                score += 35.0
            else:
                score += max(0.0, fuzz.partial_ratio(keyword, text) - 70.0) / 3

        return min(score, 100.0)

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.lower().replace("\xa0", " ").split())

    @staticmethod
    def _compact(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value.lower())
        ascii_value = "".join(
            character for character in normalized if not unicodedata.combining(character)
        )
        return re.sub(r"[^a-z0-9]+", "", ascii_value)

    @classmethod
    def _tokens(cls, value: str) -> list[str]:
        normalized = unicodedata.normalize("NFKD", value.lower())
        ascii_value = "".join(
            character for character in normalized if not unicodedata.combining(character)
        )
        return re.findall(r"[a-z0-9]+", ascii_value)
