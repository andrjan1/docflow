from docflow.ai.factory import make_ai_client


def test_factory_returns_mock_by_default(monkeypatch):
    cfg = {'provider': 'mock', 'model': 'm1'}
    client = make_ai_client(cfg)
    out = client.generate_text('hello')
    assert 'MOCK_TEXT' in out['text']


def test_factory_reads_api_key_env(monkeypatch):
    monkeypatch.setenv('SOME_KEY', 'abc123')
    cfg = {'provider': 'mock', 'api_key_envvar': 'SOME_KEY'}
    client = make_ai_client(cfg)
    # mock provider ignores api key but factory should not crash
    out = client.generate_text('ping')
    assert 'MOCK_TEXT' in out['text']
