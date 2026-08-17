"""Fiscal document parser strategies."""

from __future__ import annotations

from lumina_bot.parsers.base_parser import BaseParser, ParseContext
from lumina_bot.parsers.boleto_parser import BoletoParser
from lumina_bot.parsers.cte_parser import CteParser
from lumina_bot.parsers.desconhecido_parser import DesconhecidoParser
from lumina_bot.parsers.mdfe_parser import MdfeParser
from lumina_bot.parsers.nfce_parser import NfceParser
from lumina_bot.parsers.nfe_parser import NfeParser
from lumina_bot.parsers.nfse_parser import NfseParser
from lumina_bot.parsers.nfse_sp_parser import NfseSpParser
from lumina_bot.parsers.nfe_danfe55_parser import NfeDanfe55Parser

__all__ = [
    "BaseParser",
    "BoletoParser",
    "CteParser",
    "DesconhecidoParser",
    "MdfeParser",
    "NfceParser",
    "NfeParser",
    "NfseParser",
    "NfseSpParser",
    "NfeDanfe55Parser",
    "ParseContext",
]
