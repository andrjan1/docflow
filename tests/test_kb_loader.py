from docflow.kb.loader import concat_and_truncate, chunk_text, read_kb_texts, collect_files


def test_concat_truncate_and_chunk(tmp_path):
    a = tmp_path / 'a.md'
    a.write_text('a'*5000)
    b = tmp_path / 'b.md'
    b.write_text('b'*3000)
    files = collect_files([tmp_path], '**/*.md')
    texts = read_kb_texts(files)
    comb = concat_and_truncate(texts, 6000)
    assert len(comb) == 6000
    chunks = chunk_text(comb, chunk_size=2000, overlap=200)
    assert len(chunks) >= 3
