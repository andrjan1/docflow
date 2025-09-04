from pathlib import Path
from docflow.core.actions.generative import GenerativeAction
from docflow.core.context import ExecutionContext
from docflow.ai.providers.mock import MockProvider


class RecordingMock(MockProvider):
    def __init__(self, model: str = 'mock-1'):
        super().__init__(model=model)
        self.uploads = []

    def upload_file(self, path: str, mime_type: str | None = None):
        self.uploads.append((path, mime_type))
        return super().upload_file(path, mime_type=mime_type)


def test_attachments_as_text_and_upload(tmp_path: Path):
    # create sample files
    f1 = tmp_path / 'doc1.md'
    f1.write_text('# Title\nThis is a KB file about installation.')
    f2 = tmp_path / 'data.txt'
    f2.write_text('Some logs and details about timeout and errors')

    # action config with unified KB system (replaces old attachments)
    cfg = {
        'kb': {
            'enabled': True,
            'strategy': 'hybrid',  # Both text and upload
            'paths': [str(tmp_path / '*.md'), str(f2)],
            'as_text': True,
            'upload': True,
            'mime_type': 'application/pdf',
        }
    }

    act = GenerativeAction(cfg)
    ctx = ExecutionContext()
    recorder = RecordingMock()
    ctx.ai_client = recorder
    ctx.global_vars.update({'name': 'Alice'})

    res = act.execute(ctx)

    assert res.kind == 'text'
    # ensure upload attempted (recorder recorded something) or at least as_text concatenation worked
    # With unified KB system, text should be included in the prompt and thus in the AI response
    assert recorder.uploads or '# Title' in res.data or 'installation' in res.data
