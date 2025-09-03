from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class ExecutionContext:
    global_vars: Dict[str, Any] = field(default_factory=dict)
    action_cache: Dict[str, Any] = field(default_factory=dict)
    assets_dir: Optional[Path] = None
    kb_cache_dir: Optional[Path] = None
    ai_client: Any = None
    logger: Any = None
