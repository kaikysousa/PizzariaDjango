import re
from pathlib import Path

from django.test import SimpleTestCase

CSS_PATH = Path(__file__).resolve().parents[2] / "static" / "css" / "recibo.css"


def _css():
    return CSS_PATH.read_text(encoding="utf-8")


def _bloco(seletor):
    padrao = rf"(?:^|\n)(?<!,\n){re.escape(seletor)}\s*\{{([^}}]*)\}}"
    encontrado = re.search(padrao, _css())
    return encontrado.group(1) if encontrado else ""


def _valor(bloco, propriedade):
    encontrado = re.search(rf"{re.escape(propriedade)}\s*:\s*([^;]+);", bloco)
    return encontrado.group(1).strip() if encontrado else ""


class ReciboFonteTests(SimpleTestCase):
    """Contrato de legibilidade do recibo em 80 mm."""

    def test_corpo_usa_fonte_13px(self):
        self.assertEqual(_valor(_bloco("body"), "font-size"), "13px")

    def test_corpo_usa_line_height_1_45(self):
        self.assertEqual(_valor(_bloco("body"), "line-height"), "1.45")

    def test_marca_usa_fonte_16px(self):
        self.assertEqual(_valor(_bloco(".recibo__marca"), "font-size"), "16px")

    def test_titulo_usa_fonte_13px(self):
        self.assertEqual(_valor(_bloco(".recibo__titulo"), "font-size"), "13px")

    def test_total_usa_fonte_17px(self):
        self.assertEqual(_valor(_bloco(".recibo__totais strong"), "font-size"), "17px")

    def test_page_continua_em_80mm(self):
        self.assertIn("80mm", _bloco("@page"))

    def test_recibo_longo_tem_pagina_estendida(self):
        css_longo = (
            Path(__file__).resolve().parents[2]
            / "static"
            / "css"
            / "recibo-longo.css"
        ).read_text(encoding="utf-8")
        self.assertIn("@page", css_longo)
        self.assertIn("80mm 420mm", css_longo)

    def test_template_marca_recibo_longo(self):
        template = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "pedidos"
            / "recibo.html"
        ).read_text(encoding="utf-8")
        self.assertIn("recibo--longo", template)
        self.assertIn("recibo-longo.css", template)

    def test_impressao_usa_padding_lateral_de_2mm(self):
        impressao = re.search(r"@media print\s*\{([\s\S]*)\}\s*$", _css())
        self.assertIsNotNone(impressao)
        self.assertIn("padding: 0 2mm;", impressao.group(1))

    def test_fonte_monoespacada_disponivel_no_windows(self):
        familia = _valor(_bloco("body"), "font-family")
        self.assertIn('"Courier New", Courier, monospace', familia)

    def test_largura_do_recibo_continua_80mm(self):
        html_body = re.search(r"html,\s*body\s*\{([^}]*)\}", _css())
        self.assertIsNotNone(html_body)
        self.assertEqual(_valor(html_body.group(1), "width"), "80mm")
