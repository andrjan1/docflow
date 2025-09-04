from typing import Optional, Dict, Any, List
from pathlib import Path
from .loader import collect_files, read_kb_texts, concat_and_truncate


class UnifiedKBStrategy:
    """Unified KB strategy handling both text extraction and file uploads"""
    
    def process_kb(self, cfg: Dict[str, Any], vars: Dict[str, Any]) -> Dict[str, Any]:
        """Process KB according to strategy, returns context updates"""
        if not cfg.get('enabled', False):
            return {}
            
        paths_raw = cfg.get('paths', [])
        # Handle both string paths and Path objects, expand globs
        expanded_paths = []
        for p in paths_raw:
            path_str = str(p)
            if any(char in path_str for char in ['*', '?', '[']):
                # Expand glob patterns
                import glob
                matches = glob.glob(path_str, recursive=True)
                expanded_paths.extend([Path(m) for m in matches])
            else:
                expanded_paths.append(Path(path_str))
        
        files = [p for p in expanded_paths if p.exists() and p.is_file()]
        strategy = cfg.get('strategy', 'inline')
        
        if strategy == "inline":
            return self._strategy_inline(files, cfg)
        elif strategy == "upload":
            return self._strategy_upload(files, cfg)
        elif strategy == "hybrid":
            return self._strategy_hybrid(files, cfg)
        elif strategy == "summarize":
            return self._strategy_summarize(files, cfg)
        elif strategy == "retrieve":
            return self._strategy_retrieve(files, cfg, vars)
        else:
            raise ValueError(f"Unknown KB strategy: {strategy}")
    
    def _strategy_inline(self, files: List[Path], cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text and return as knowledge_base"""
        if not cfg.get('as_text', True):
            return {}
        texts = read_kb_texts(files)
        max_chars = cfg.get('max_chars', 10000)
        # Support dynamic max_chars from variables
        if isinstance(max_chars, str) and max_chars.startswith('{{'):
            from jinja2 import Template
            try:
                max_chars = int(Template(max_chars).render(**vars))
            except:
                max_chars = 10000
        kb_text = concat_and_truncate(texts, max_chars)
        return {'kb_text': kb_text} if kb_text else {}
    
    def _strategy_upload(self, files: List[Path], cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare files for upload to AI provider"""
        attachments = []
        for file in files:
            attachments.append({
                'path': str(file),
                'mime_type': cfg.get('mime_type') or self._detect_mime(file),
                'upload': True
            })
        return {'attachments': attachments}
    
    def _strategy_hybrid(self, files: List[Path], cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Both text extraction AND file upload"""
        result = {}
        
        # Add text if enabled
        if cfg.get('as_text', True):
            inline_result = self._strategy_inline(files, cfg)
            result.update(inline_result)
        
        # Add attachments for upload
        upload_result = self._strategy_upload(files, cfg)
        result.update(upload_result)
        
        return result
    
    def _strategy_summarize(self, files: List[Path], cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize files (first N chars of each)"""
        texts = read_kb_texts(files)
        snippets = [t[:min(300, len(t))] for t in texts if t]
        summary = '\n\n'.join(snippets)
        return {'kb_text': summary} if summary else {}
    
    def _strategy_retrieve(self, files: List[Path], cfg: Dict[str, Any], vars: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant snippets based on input vars"""
        texts = read_kb_texts(files)
        queries = vars.keys()
        matches = []
        for t in texts:
            for q in queries:
                if q and q.lower() in t.lower():
                    idx = t.lower().index(q.lower())
                    start = max(0, idx - 100)
                    matches.append(t[start:start + 400])
                    break
        kb_text = '\n\n'.join(matches)
        return {'kb_text': kb_text} if kb_text else {}
    
    def _detect_mime(self, file: Path) -> str:
        """Detect MIME type based on file extension"""
        suffix = file.suffix.lower()
        mime_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg'
        }
        return mime_map.get(suffix, 'application/octet-stream')


# Instantiate the unified strategy processor
kb_strategy_processor = UnifiedKBStrategy()


# Legacy wrapper functions for backward compatibility with existing code
def strategy_inline(cfg: Dict[str, Any], vars: Dict[str, Any]) -> Optional[str]:
    """Legacy wrapper for inline strategy"""
    cfg_copy = cfg.copy()
    cfg_copy['strategy'] = 'inline'
    cfg_copy['enabled'] = True
    
    # Use old system if paths don't contain globs
    paths = cfg_copy.get('paths', [])
    if not any(any(char in str(p) for char in ['*', '?', '[']) for p in paths):
        # Use legacy collect_files approach
        path_objs = [Path(p) for p in paths]
        files = collect_files(path_objs, cfg_copy.get('include_glob', '**/*.md'))
        texts = read_kb_texts(files)
        max_chars = cfg_copy.get('max_chars', 10000)
        return concat_and_truncate(texts, max_chars) or None
    
    # Use new unified system for glob patterns
    result = kb_strategy_processor.process_kb(cfg_copy, vars)
    return result.get('kb_text')


def strategy_summarize(cfg: Dict[str, Any], vars: Dict[str, Any]) -> Optional[str]:
    """Legacy wrapper for summarize strategy"""
    cfg_copy = cfg.copy()
    cfg_copy['strategy'] = 'summarize'
    cfg_copy['enabled'] = True
    
    # Use old system if paths don't contain globs
    paths = cfg_copy.get('paths', [])
    if not any(any(char in str(p) for char in ['*', '?', '[']) for p in paths):
        # Use legacy collect_files approach
        path_objs = [Path(p) for p in paths]
        files = collect_files(path_objs, cfg_copy.get('include_glob', '**/*.md'))
        texts = read_kb_texts(files)
        snippets = [t[:min(300, len(t))] for t in texts if t]
        return '\n\n'.join(snippets) or None
    
    result = kb_strategy_processor.process_kb(cfg_copy, vars)
    return result.get('kb_text')


def strategy_retrieve_mock(cfg: Dict[str, Any], vars: Dict[str, Any]) -> Optional[str]:
    """Legacy wrapper for retrieve strategy"""
    cfg_copy = cfg.copy()
    cfg_copy['strategy'] = 'retrieve'
    cfg_copy['enabled'] = True
    
    # Use old system if paths don't contain globs
    paths = cfg_copy.get('paths', [])
    if not any(any(char in str(p) for char in ['*', '?', '[']) for p in paths):
        # Use legacy collect_files approach
        path_objs = [Path(p) for p in paths]
        files = collect_files(path_objs, cfg_copy.get('include_glob', '**/*.md'))
        texts = read_kb_texts(files)
        queries = vars.keys()
        matches = []
        for t in texts:
            for q in queries:
                if q and q.lower() in t.lower():
                    idx = t.lower().index(q.lower())
                    start = max(0, idx - 100)
                    matches.append(t[start:start + 400])
                    break
        return '\n\n'.join(matches) if matches else None
    
    result = kb_strategy_processor.process_kb(cfg_copy, vars)
    return result.get('kb_text')


def prepare_kb_for_action(action_cfg: Dict[str, Any], vars: Dict[str, Any]) -> Optional[str]:
    """Main entry point for KB processing - updated to use unified system"""
    if not action_cfg:
        return None
    
    # Extract kb configuration
    if isinstance(action_cfg, dict) and 'kb' in action_cfg:
        kb = action_cfg.get('kb') or {}
    else:
        kb = action_cfg or {}
    
    if not kb.get('enabled'):
        return None
    
    # Use the unified processor
    result = kb_strategy_processor.process_kb(kb, vars)
    
    # Return text for backward compatibility with existing prompt builder
    return result.get('kb_text')
