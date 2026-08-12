"""Document type detection for fiscal and financial PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from rapidfuzz import fuzz


class DocumentType(str, Enum):
    """Supported document types."""

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
