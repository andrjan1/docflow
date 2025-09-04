import pytest
from pathlib import Path
from docflow.kb.strategies import kb_strategy_processor
import yaml


def test_unified_kb_inline_strategy(tmp_path):
    """Test the new unified KB system with inline strategy"""
    # Create test files
    kb_dir = tmp_path / 'kb'
    kb_dir.mkdir()
    (kb_dir / 'doc1.md').write_text('# Document 1\nThis is the first document.')
    (kb_dir / 'doc2.txt').write_text('Document 2 content with important information.')
    
    cfg = {
        'enabled': True,
        'paths': [str(kb_dir / '*.md'), str(kb_dir / '*.txt')],
        'strategy': 'inline',
        'as_text': True,
        'max_chars': 1000
    }
    
    result = kb_strategy_processor.process_kb(cfg, {})
    
    assert 'kb_text' in result
    assert 'Document 1' in result['kb_text']
    assert 'Document 2' in result['kb_text']
    assert len(result['kb_text']) <= 1000


def test_unified_kb_upload_strategy(tmp_path):
    """Test the new unified KB system with upload strategy"""
    # Create test files
    kb_dir = tmp_path / 'kb'
    kb_dir.mkdir()
    (kb_dir / 'document.pdf').write_bytes(b'fake pdf content')
    (kb_dir / 'report.docx').write_bytes(b'fake docx content')
    
    cfg = {
        'enabled': True,
        'paths': [str(kb_dir / '*.pdf'), str(kb_dir / '*.docx')],
        'strategy': 'upload',
        'upload': True,
        'as_text': False,
        'mime_type': 'application/pdf'
    }
    
    result = kb_strategy_processor.process_kb(cfg, {})
    
    assert 'attachments' in result
    assert len(result['attachments']) == 2
    
    # Check attachment structure
    for attachment in result['attachments']:
        assert 'path' in attachment
        assert 'mime_type' in attachment
        assert 'upload' in attachment
        assert attachment['upload'] is True


def test_unified_kb_hybrid_strategy(tmp_path):
    """Test the new unified KB system with hybrid strategy"""
    # Create test files
    kb_dir = tmp_path / 'kb'
    kb_dir.mkdir()
    (kb_dir / 'info.md').write_text('# Information\nThis is important information.')
    (kb_dir / 'data.json').write_text('{"key": "value", "data": "test"}')
    
    cfg = {
        'enabled': True,
        'paths': [str(kb_dir / '*')],
        'strategy': 'hybrid',
        'upload': True,
        'as_text': True,
        'max_chars': 500,
        'mime_type': 'auto'
    }
    
    result = kb_strategy_processor.process_kb(cfg, {})
    
    # Should have both text and attachments
    assert 'kb_text' in result
    assert 'attachments' in result
    
    # Check text extraction
    assert 'Information' in result['kb_text']
    assert 'value' in result['kb_text']
    
    # Check file attachments
    assert len(result['attachments']) == 2
    attachment_paths = [a['path'] for a in result['attachments']]
    assert any('info.md' in p for p in attachment_paths)
    assert any('data.json' in p for p in attachment_paths)


def test_unified_kb_summarize_strategy(tmp_path):
    """Test the new unified KB system with summarize strategy"""
    # Create test files with long content
    kb_dir = tmp_path / 'kb'
    kb_dir.mkdir()
    (kb_dir / 'long_doc.md').write_text('# Long Document\n' + 'A' * 1000 + '\nMore content here.')
    (kb_dir / 'another_doc.txt').write_text('B' * 500 + '\nAdditional information.')
    
    cfg = {
        'enabled': True,
        'paths': [str(kb_dir / '*')],
        'strategy': 'summarize',
        'as_text': True
    }
    
    result = kb_strategy_processor.process_kb(cfg, {})
    
    assert 'kb_text' in result
    # Should contain snippets from both documents
    assert 'Long Document' in result['kb_text']
    assert 'AAAA' in result['kb_text']  # From first 300 chars
    assert 'BBBB' in result['kb_text']  # From first 300 chars
    # Should be much shorter than original
    assert len(result['kb_text']) < 800  # Much less than 1500+ original


def test_unified_kb_retrieve_strategy(tmp_path):
    """Test the new unified KB system with retrieve strategy"""
    # Create test files
    kb_dir = tmp_path / 'kb'
    kb_dir.mkdir()
    (kb_dir / 'faq.md').write_text('Q: What is Python? A: Python is a programming language.')
    (kb_dir / 'guide.txt').write_text('Installation guide: First install Python, then run setup.')
    
    cfg = {
        'enabled': True,
        'paths': [str(kb_dir / '*')],
        'strategy': 'retrieve',
        'as_text': True
    }
    
    # Search for documents containing 'Python'
    vars_with_python = {'query': 'Python', 'language': 'programming'}
    result = kb_strategy_processor.process_kb(cfg, vars_with_python)
    
    assert 'kb_text' in result
    assert 'Python' in result['kb_text']
    
    # Should find relevant snippets
    assert 'programming language' in result['kb_text'] or 'install Python' in result['kb_text']


def test_unified_kb_disabled():
    """Test that disabled KB returns empty result"""
    cfg = {
        'enabled': False,
        'paths': ['some/path'],
        'strategy': 'inline'
    }
    
    result = kb_strategy_processor.process_kb(cfg, {})
    assert result == {}


def test_unified_kb_mime_detection(tmp_path):
    """Test MIME type detection in unified KB system"""
    kb_dir = tmp_path / 'kb'
    kb_dir.mkdir()
    (kb_dir / 'document.pdf').write_bytes(b'fake pdf')
    (kb_dir / 'spreadsheet.csv').write_bytes(b'col1,col2\nval1,val2')
    (kb_dir / 'image.png').write_bytes(b'fake png')
    
    cfg = {
        'enabled': True,
        'paths': [str(kb_dir / '*')],
        'strategy': 'upload',
        'upload': True
    }
    
    result = kb_strategy_processor.process_kb(cfg, {})
    
    attachments = result['attachments']
    mime_types = {a['mime_type'] for a in attachments}
    
    assert 'application/pdf' in mime_types
    assert 'text/csv' in mime_types  
    assert 'image/png' in mime_types
