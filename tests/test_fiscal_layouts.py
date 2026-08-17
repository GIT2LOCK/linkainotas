"""Regression tests for the supported PDF fiscal layouts."""

from __future__ import annotations

import unittest

from lumina_bot.core.document_detector import DocumentDetector, DocumentType


class FiscalLayoutDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = DocumentDetector()

    def test_detects_sp_nfse_before_generic_nfse(self) -> None:
        result = self.detector.detect(
            "PREFEITURA DO MUNICIPIO DE SAO PAULO\n"
            "NOTA FISCAL ELETRONICA DE SERVICOS - NFS-e\n"
            "PRESTADOR DE SERVICOS\nTOMADOR DE SERVICOS"
        )
        self.assertEqual(result.document_type, DocumentType.NFSE_SP)

    def test_detects_danfe_before_generic_nfe(self) -> None:
        result = self.detector.detect(
            "DANFE\nDocumento Auxiliar da Nota Fiscal Eletronica\n"
            "CHAVE DE ACESSO\nDESTINATARIO / REMETENTE\n"
            "DADOS DOS PRODUTOS / SERVICOS"
        )
        self.assertEqual(result.document_type, DocumentType.NFE_DANFE_55)

    def test_does_not_treat_da_nfe_as_danfe(self) -> None:
        result = self.detector.detect(
            "Consulta de autenticidade no portal nacional da NF-e"
        )
        self.assertNotEqual(result.document_type, DocumentType.NFE_DANFE_55)


if __name__ == "__main__":
    unittest.main()
