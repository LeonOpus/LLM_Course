import pytest
from rag_app.parsing import normalize_layouts,table_html

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
def damaged(markdown):
    return {'type':'table','pageNum':9,'uniqueId':'real-shape-reproduction',
        'cells':[{'ysc':0,'yec':0,'xsc':0,'xec':0,'text':'header'},
                 {'ysc':0,'yec':0,'xsc':0,'xec':0,'text':'value'}],
        'markdownContent':markdown}

def test_invalid_cells_keep_provider_markdown_with_explicit_warning():
    markdown='|费用项|金额|\n|---|---|\n|合计|339|'
    block=normalize_layouts('D11','pdf',[damaged(markdown)])[0]
    assert block['text']==markdown
    assert block['locator']['page']==10
    assert block['metadata']['table_representation']=='provider_markdown_fallback'
    assert block['metadata']['table_structure_validated'] is False
    assert '重叠' in block['metadata']['table_structure_issue']

@pytest.mark.parametrize('markdown',['',None])
def test_invalid_cells_without_usable_alternative_still_fail(markdown):
    with pytest.raises(ValueError,match='重叠'):
        normalize_layouts('D11','pdf',[damaged(markdown)])

def test_raw_cell_renderer_stays_strict():
    with pytest.raises(ValueError,match='重叠'):table_html(damaged('fallback'))
