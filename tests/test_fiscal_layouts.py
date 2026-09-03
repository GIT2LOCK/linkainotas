"""Regression tests for the supported PDF fiscal layouts."""

from __future__ import annotations

import unittest
from pathlib import Path

from lumina_bot.core.document_detector import DocumentDetector, DocumentType
from lumina_bot.core.pdf_reader import PdfReadResult
from lumina_bot.core.xml_writer import XmlWriter
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.parsers.base_parser import ParseContext
from lumina_bot.parsers.nfe_danfe55_parser import NfeDanfe55Parser
from lumina_bot.parsers.nfse_cotia_parser import NfseCotiaParser


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

    def test_detects_cotia_before_generic_nfse(self) -> None:
        result = self.detector.detect(
            "PREFEITURA DO MUNICÍPIO DE COTIA\n"
            "NOTA FISCAL DE SERVIÇOS ELETRÔNICA\n"
            "PRESTADOR DE SERVIÇOS\nTOMADOR DE SERVIÇOS"
        )
        self.assertEqual(result.document_type, DocumentType.NFSE_COTIA_1P)
        self.assertEqual(result.sub_layout, "COTIA_1P")

    def test_detects_known_danfe_sublayouts(self) -> None:
        anchors = "DANFE CHAVE DE ACESSO DESTINATÁRIO / REMETENTE DADOS DOS PRODUTOS / SERVIÇOS"
        self.assertEqual(self.detector.detect(f"ECOMIX ARGAMASSAS LTDA {anchors}").sub_layout, "ECOMIX_OCR")
        self.assertEqual(self.detector.detect(f"METALURGICA FHOENIX DO BRASIL LTDA {anchors}").sub_layout, "FHOENIX")
        self.assertEqual(self.detector.detect(f"STAMP PRE FABRICADOS ARQUITETONICOS LTDA {anchors}").sub_layout, "STAMP")


class FiscalParserTests(unittest.TestCase):
    @staticmethod
    def _context(text: str, file_name: str, *, ocr_used: bool = False, ocr_required: bool = False) -> ParseContext:
        pdf = PdfReadResult(
            path=Path(file_name),
            text=text,
            page_count=1,
            author=None,
            creator=None,
            producer=None,
            size_bytes=len(text),
            sha256="test-hash",
            ocr_required=ocr_required,
            ocr_used=ocr_used,
            pages=(text,),
        )
        detection = DocumentDetector().detect(text, file_name)
        return ParseContext(text=text, file_name=file_name, detection=detection, pdf=pdf)

    def test_parses_cotia_without_second_page_or_fake_key(self) -> None:
        text = """PREFEITURA DO MUNICÍPIO DE COTIA
NOTA FISCAL DE SERVIÇOS ELETRÔNICA
Nº Nota: 28275
RPS: 29211
Data de Emissão: 04/AGO/2026
Competência: 08/2026
Código de Verificação: 45135827YX
PRESTADOR DE SERVIÇOS
Nome/Razão Social: VOTORANTIM CIMENTOS S.A.
CPF/CNPJ: 01.637.895/0038-24
TOMADOR DE SERVIÇOS
Nome/Razão Social: STAN 38 PARTICIPACOES LTDA
CPF/CNPJ: 42.610.240/0001-58
DISCRIMINAÇÃO DOS SERVIÇOS
Servico de Concretagem
CNO/CEI: 90.027.39258/76
SFOBRAS: 2026/0001227-2
Valor aproximado dos tributos: 8531,17 (8,65%)
VALOR TOTAL DA NOTA: 98626,40
Código da Obra: 50201
Código NBS: 101054000
Base de Cálculo do ISS: 98626,40
Alíquota do ISS: 5,00
Valor do ISS: 4931,32
Valor Líquido da Nota: 93695,08
Valor do IBS: 98,63
Valor da CBS: 887,64
Chave Acesso: Aguardando retorno do Ambiente Nacional"""
        nota = NfseCotiaParser().parse(self._context(text, "NFS-e 28275 - Votorantim Cimentos.pdf"))
        self.assertEqual(nota.layout, "NFSE_COTIA_1P")
        self.assertEqual(nota.numero, "28275")
        self.assertEqual(nota.rps_numero, "29211")
        self.assertEqual(nota.data_emissao, "2026-08-04")
        self.assertEqual(nota.valor_total, 98626.40)
        self.assertEqual(nota.valor_liquido, 93695.08)
        self.assertEqual(nota.tributos.ibs, 98.63)
        self.assertEqual(nota.tributos.cbs, 887.64)
        self.assertIsNone(nota.chave)
        self.assertEqual(nota.chave_acesso_raw, "Aguardando retorno do Ambiente Nacional")

    def test_parses_cotia_footer_sections_without_cross_contamination(self) -> None:
        text = """PREFEITURA DO MUNICÍPIO DE COTIA
NOTA FISCAL DE SERVIÇOS ELETRÔNICA
Nº Nota: 28275
RPS: 29211
Data de Emissão: 04/AGO/2026
Competência: 08/2026
Código de Verificação
45135827YX
PRESTADOR DE SERVIÇOS
Nome/Razão Social: VOTORANTIM CIMENTOS S.A.
CPF/CNPJ: 01.637.895/0038-24
TOMADOR DE SERVIÇOS
Nome/Razão Social: STAN 38 PARTICIPACOES LTDA
CPF/CNPJ: 42.610.240/0001-58
DISCRIMINAÇÃO DOS SERVIÇOS
O ISSQN desta NFS-e será recolhido pelo TOMADOR MENCIONADO ACIMA.
INFORMAÇÕES COMPLEMENTARES
Servico de Concretagem - Local da Obra: AVENIDA PEDROSO DE MORAIS, 919 PINHEIROS - SAO PAULO / SP Codigo CEI: 900273925876 CNO/CEI: 90.027.39258/76 SFOBRAS: 2026/0001227-2
Vlr Outras Retenções (R$)
Código de Verificação:
45135827YX
Chave Acesso:
Aguardando retorno do Ambiente Nacional"""
        nota = NfseCotiaParser().parse(self._context(text, "NFS-e 28275 - Votorantim Cimentos.pdf"))
        nfse = nota.outros_campos["nfse"]
        additional = nota.outros_campos["dados_adicionais"]
        self.assertEqual(nfse["servico_descricao"], "Servico de Concretagem")
        self.assertEqual(nfse["local_obra"], "AVENIDA PEDROSO DE MORAIS, 919 PINHEIROS - SAO PAULO / SP")
        self.assertEqual(nfse["codigo_cei"], "900273925876")
        self.assertEqual(nfse["cno_cei"], "90.027.39258/76")
        self.assertEqual(additional["informacoes_complementares_raw"].splitlines(), ["Servico de Concretagem - Local da Obra: AVENIDA PEDROSO DE MORAIS, 919 PINHEIROS - SAO PAULO / SP Codigo CEI: 900273925876 CNO/CEI: 90.027.39258/76 SFOBRAS: 2026/0001227-2"])
        self.assertEqual(additional["outras_informacoes_raw"], "O ISSQN desta NFS-e será recolhido pelo TOMADOR MENCIONADO ACIMA.")
        self.assertEqual(nota.outros_campos["codigo_verificacao_rodape"], "45135827YX")
        self.assertTrue(any(item.regra == "nfse.codigo_verificacao_repetido_coincide" and item.status == "ok" for item in nota.validacoes))

    def test_parses_fhoenix_multiline_items_and_ocr_metadata(self) -> None:
        text = """DANFE
Documento Auxiliar da Nota Fiscal Eletrônica
CHAVE DE ACESSO
35260715383361000131550010000036831333983943
DESTINATÁRIO / REMETENTE
DADOS DOS PRODUTOS / SERVIÇOS
METALURGICA FHOENIX DO BRASIL LTDA
Nº 000.003.683
SÉRIE 001
VALOR TOTAL DOS PRODUTOS 4465,00
VALOR TOTAL DA NOTA 4465,00
VALOR APROXIMADO DOS IMPOSTOS 1396,78
DUPLICATAS
001 26/08/2026 4465,00
0071 FECHAMENTO MEDINDO: 0,25+1,50+0,25X1,70M - Bem/Mercadoria do Cod./Produto 0071 73089010 0102 5102 PC 1,00 4295,00 0,00 4295,00 0,00 0,00 0,00 0,00 0,00
0069 REQUADRO GALVANIZADO MEDINDO: 0,53X2,69M - Bem/Mercadoria do Cod./Produto 0069 73089090 0102 5102 PC 1,00 170,00 0,00 170,00 0,00 0,00 0,00 0,00 0,00
TRANSPORTADOR / VOLUMES TRANSPORTADOS
3 - PROP/REMT
CÁLCULO DO ISSQN
DADOS ADICIONAIS"""
        nota = NfeDanfe55Parser().parse(self._context(text, "METALURGICA FHOENIX NFE 3683.pdf", ocr_used=True))
        self.assertEqual(nota.sub_layout, "FHOENIX")
        self.assertTrue(nota.ocr_used)
        self.assertEqual(len(nota.itens), 2)
        self.assertEqual([item.codigo for item in nota.itens], ["0071", "0069"])
        self.assertEqual(round(sum(item.valor_total or 0 for item in nota.itens), 2), 4465.00)
        self.assertEqual(len(nota.parcelas), 1)
        self.assertIsNone(nota.outros_campos.get("transportador", {}).get("razao_social"))

    def test_keeps_ocr_complementary_block_and_parcelas_label(self) -> None:
        text = """DANFE
Documento Auxiliar da Nota Fiscal Eletrônica
CHAVE DE ACESSO
35260715383361000131550010000036831333983943
METALURGICA FHOENIX DO BRASIL LTDA
DESTINATÁRIO / REMETENTE
FATURA
DADOS DA FATURA Numero: 000003683 - Valor Original: R$ 4.465,00 - Valor Desconto: R$0,00 - Valor Liquido: R$ 4.465,00
PARCELAS
Numero : 001
Vencimento : 26/08/2026
Valor R$ 4.465,00
DADOS DOS PRODUTOS / SERVIÇOS
0071 FECHAMENTO MEDINDO: 0,25X1,70M 73089010 0102 5102 PC 1,00 4.295,00 0,00 4.295,00 0,00 0,00 0,00 0,00 0,00
0069 REQUADRO GALVANIZADO MEDINDO: 0,53X2,69M 73089090 0102 5102 PC 1,00 170,00 0,00 170,00 0,00 0,00 0,00 0,00 0,00
DADOS ADICIONAIS
INFORMACOES COMPLEMENTARES RESERVADO AO FISCO
Pagamento(s): (Boleto Bancario R$4.465,00) - OBRA: FONSECA RODRIGUES-LINKA
Endereco: Av. Prof. Fonseca Rodrigues, 498
SFOBRAS: 2024.0010782-6 CNO - 90.020.92145/72.
"""
        nota = NfeDanfe55Parser().parse(
            self._context(text, "METALURGICA FHOENIX NFE 3683.pdf", ocr_used=True)
        )
        self.assertEqual(
            [(parcela.numero, parcela.vencimento, parcela.valor) for parcela in nota.parcelas],
            [("001", "2026-08-26", 4465.00)],
        )
        self.assertIn("OBRA: FONSECA RODRIGUES-LINKA", nota.observacoes or "")

    def test_recovers_labeled_due_date_from_full_document_text(self) -> None:
        text = """DANFE
Documento Auxiliar da Nota Fiscal Eletrônica
CHAVE DE ACESSO
35260715383361000131550010000036831333983943
METALURGICA FHOENIX DO BRASIL LTDA
VALOR TOTAL DA NOTA 4465,00
DADOS DOS PRODUTOS / SERVIÇOS
0071 FECHAMENTO 73089010 PC 1,00 4295,00
0069 REQUADRO 73089090 PC 1,00 170,00
PARCELAS
Numero : 001
Vencimento :
26/08/2026
Valor : R$ 4.465,00
DADOS ADICIONAIS"""
        nota = NfeDanfe55Parser().parse(
            self._context(text, "METALURGICA FHOENIX NFE 3683.pdf", ocr_used=True)
        )
        self.assertEqual(
            [(parcela.numero, parcela.vencimento, parcela.valor) for parcela in nota.parcelas],
            [("001", "2026-08-26", 4465.0)],
        )

    def test_xml_contains_canonical_metadata(self) -> None:
        nota = NotaFiscal(
            arquivo="cotia.pdf",
            layout="NFSE_COTIA_1P",
            sub_layout="COTIA_1P",
            ocr_used=False,
            numero="28275",
            chave_acesso_raw="Aguardando retorno do Ambiente Nacional",
        )
        output = Path(__file__).parent / "_tmp_xml"
        output.mkdir(exist_ok=True)
        try:
            xml_path = XmlWriter().write(nota, output)
            xml = xml_path.read_text(encoding="utf-8")
            self.assertIn('sub_layout="COTIA_1P"', xml)
            self.assertIn("<chaveAcessoRaw>Aguardando retorno do Ambiente Nacional</chaveAcessoRaw>", xml)
            self.assertIn("<nfseCotia", xml)
        finally:
            for path in output.glob("*"):
                path.unlink()
            output.rmdir()


if __name__ == "__main__":
    unittest.main()
