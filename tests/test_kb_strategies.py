from docflow.kb.strategies import strategy_inline, strategy_summarize, strategy_retrieve_mock


def test_strategies_inline_and_summarize(tmp_path):
    d = tmp_path / 'kb'
    d.mkdir()
    f = d / 'note.md'
    f.write_text('This is a KB note about Python and testing. It mentions function names and keywords.')
    cfg = {'paths': [str(d)], 'include_glob': '**/*.md', 'max_chars': 1000}
    txt = strategy_inline(cfg, {})
    assert 'KB note' in txt
    summ = strategy_summarize(cfg, {})
    assert 'KB note' in summ


def test_retrieve_mock(tmp_path):
    d = tmp_path / 'kb'
    d.mkdir()
    f = d / 'note.md'
    f.write_text('Alpha beta gamma. contains keyword: foobar. more text.')
    cfg = {'paths': [str(d)], 'include_glob': '**/*.md'}
    out = strategy_retrieve_mock(cfg, {'foobar': 'x'})
    assert out is not None
 
