"""Document type detection for fiscal and financial PDFs."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from rapidfuzz import fuzz


class DocumentType(str, Enum):
    """Supported document types."""

    NFE_DANFE_55 = "NFE_DANFE_55"
    NFSE_SP = "NFSE_SP"
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

        nfse_found = tuple(anchor for anchor in nfse_anchors if cls._contains_anchor(normalized, anchor))
        nfe_found = tuple(anchor for anchor in nfe_anchors if cls._contains_anchor(normalized, anchor))

        if len(nfse_found) >= 3:
            return DocumentDetection(
                document_type=DocumentType.NFSE_SP,
                confidence=min(100.0, 60.0 + len(nfse_found) * 10.0),
                reason="NFSE_SP fiscal layout anchors",
                anchors_found=nfse_found,
                anchors_missing=tuple(anchor for anchor in nfse_anchors if anchor not in nfse_found),
            )

        if len(nfe_found) >= 3:
            return DocumentDetection(
                document_type=DocumentType.NFE_DANFE_55,
                confidence=min(100.0, 60.0 + len(nfe_found) * 8.0),
                reason="NFE_DANFE_55 fiscal layout anchors",
                anchors_found=nfe_found,
                anchors_missing=tuple(anchor for anchor in nfe_anchors if anchor not in nfe_found),
            )

        return None

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
