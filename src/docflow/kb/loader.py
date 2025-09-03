from pathlib import Path
from typing import List
import fnmatch
import csv
import json

try:
    from docx import Document as DocxDocument
except Exception:
    DocxDocument = None

try:
    from pypdf import PdfReader
except Exception:
    try:
        # older package name
        from PyPDF2 import PdfReader
    except Exception:
        PdfReader = None


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except Exception:
        return ''


def _read_docx(path: Path) -> str:
    if DocxDocument is None:
        return ''
    try:
        doc = DocxDocument(str(path))
        return '\n'.join(p.text for p in doc.paragraphs if p.text)
    except Exception:
        return ''


def collect_files(paths: List[Path], include_glob: str = '**/*.md') -> List[Path]:
    results: List[Path] = []
    for p in paths:
        if p.is_file():
            results.append(p)
            continue
        if p.is_dir():
            for f in p.rglob('*'):
                if fnmatch.fnmatch(str(f.name), include_glob.split('/')[-1]) or f.match(include_glob):
                    results.append(f)
    return results


def read_kb_texts(files: List[Path]) -> List[str]:
    texts: List[str] = []
    for f in files:
        if not f.exists():
            continue
        suf = f.suffix.lower()
        if suf in ('.md', '.txt'):
            texts.append(_read_text_file(f))
        elif suf in ('.docx',) and DocxDocument is not None:
            texts.append(_read_docx(f))
        elif suf in ('.pdf',) and PdfReader is not None:
            try:
                reader = PdfReader(str(f))
                # concatenate all page text
                pages = []
                for p in getattr(reader, 'pages', []) or []:
                    try:
                        pages.append(p.extract_text() or '')
                    except Exception:
                        pass
                texts.append('\n'.join(p for p in pages if p))
            except Exception:
                texts.append('')
        elif suf in ('.csv',):
            try:
                with f.open('r', encoding='utf-8', errors='ignore') as fh:
                    rdr = csv.reader(fh)
                    rows = [' , '.join(r) for r in rdr]
                    texts.append('\n'.join(rows))
            except Exception:
                texts.append('')
        elif suf in ('.json',):
            try:
                j = json.loads(f.read_text(encoding='utf-8'))
                texts.append(json.dumps(j, ensure_ascii=False, indent=2))
            except Exception:
                texts.append('')
    return texts


def concat_and_truncate(texts: List[str], max_chars: int) -> str:
    combined = '\n\n'.join(t for t in texts if t)
    if len(combined) <= max_chars:
        return combined
    return combined[:max_chars]


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    if not text:
        return []
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = min(start + chunk_size, L)
        chunks.append(text[start:end])
        if end == L:
            break
        start = max(0, end - overlap)
    return chunks
