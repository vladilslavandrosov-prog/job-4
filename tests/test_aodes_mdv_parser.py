from parts_monitor.adapters.aodes_mdv import parse_table_html

SAMPLE_HTML = """
<div class="ofh rad8">
<table class="partsTable w100">
<thead>
<tr><th>Наименование</th><th>Артикул</th></tr>
</thead>
<tbody>
<tr><td>Реле стартера AODES</td><td class="tar"><div class="fs12">001-EL-3700-0830-00</div></td></tr>
<tr><td>Болт М8</td><td class="tar"><div class="fs12">13609340000</div></td></tr>
<tr><td>Прокладка ГБЦ</td><td class="tar"><div class="fs12">13609180090 ?</div></td></tr>
</tbody>
</table>
</div>
"""


def test_parses_rows_and_skips_header():
    items = list(parse_table_html(SAMPLE_HTML))
    assert len(items) == 3
    assert items[0].sku == "001-EL-3700-0830-00"
    assert items[0].name == "Реле стартера AODES"


def test_no_price_column_marks_unverified_with_zero_price():
    items = list(parse_table_html(SAMPLE_HTML))
    assert all(i.price == 0.0 for i in items)
    assert all(i.unverified for i in items)


def test_marks_unverified_sku_and_strips_suffix():
    items = list(parse_table_html(SAMPLE_HTML))
    item = next(i for i in items if i.sku == "13609180090")
    assert item.unverified
