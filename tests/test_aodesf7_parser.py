from parts_monitor.adapters.aodesf7 import parse_table_html

SAMPLE_HTML = """
<div class="wpb_wrapper">
<table width="809">
<tr><td>Артикул</td><td>Наименование</td><td>Рекомендованная розничная цена, руб.</td></tr>
<tr><td>001-EL-3700-0830-00</td><td>Реле стартера</td><td>281</td></tr>
<tr><td>13609340000</td><td>Болт М8</td><td>438</td></tr>
<tr><td>13609340000</td><td>Болт М8 (компл.)</td><td>1047</td></tr>
<tr><td>13609180090 ?</td><td>Прокладка ГБЦ</td><td>225214</td></tr>
<tr><td>01256100606</td><td>Подшипник 6204</td><td>224</td></tr>
<tr><td>1256100606</td><td>Подшипник 6204 (аналог)</td><td>101</td></tr>
</table>
</div>
"""


def test_parses_rows_and_skips_header():
    items = list(parse_table_html(SAMPLE_HTML))
    assert len(items) == 6
    assert items[0].sku == "001-EL-3700-0830-00"
    assert items[0].name == "Реле стартера"
    assert items[0].price == 281


def test_marks_unverified_sku_and_strips_suffix():
    items = list(parse_table_html(SAMPLE_HTML))
    unverified = [i for i in items if i.unverified]
    assert len(unverified) == 1
    assert unverified[0].sku == "13609180090"


def test_duplicate_sku_at_different_prices_both_kept():
    items = list(parse_table_html(SAMPLE_HTML))
    matching = [i for i in items if i.sku == "13609340000"]
    assert {i.price for i in matching} == {438, 1047}


def test_leading_zero_sku_variant_kept_as_distinct_raw_sku():
    items = list(parse_table_html(SAMPLE_HTML))
    skus = {i.sku for i in items}
    assert "01256100606" in skus
    assert "1256100606" in skus
