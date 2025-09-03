import yaml
from pathlib import Path
from docflow.runtime.orchestrator import run_config


def test_e2e_run_with_attachments(tmp_path: Path):
    # create KB files
    kbdir = tmp_path / 'kb'
    kbdir.mkdir()
    (kbdir / 'note.md').write_text('# Note\nThis is a KB note about sales and installation')

    # create a simple docx template
    from docx import Document

    templates = tmp_path / 'templates'
    templates.mkdir()
    doc = Document()
    doc.add_paragraph('Greeting: {{greeting}}')
    doc.save(templates / 'demo_template.docx')

    # write config
    cfg = {
        'project': {'base_dir': str(tmp_path), 'output_dir': 'output'},
        'ai': {'provider': 'mock'},
        'workflow': {
            'actions': [
                {
                    'id': 'gen1',
                    'type': 'generative',
                    'returns': 'image',
                    'prompt': 'Say hello to {{name}}',
                    'attachments': {'paths': [str(kbdir / '*.md')], 'as_text': True, 'upload': False},
                }
            ],
            'templates': [{'path': str(templates / 'demo_template.docx'), 'adapter': 'docx'}],
        },
    }
    cfg_path = tmp_path / 'cfg.yaml'
    cfg_path.write_text(yaml.safe_dump(cfg))

    # run orchestrator
    out = run_config(str(cfg_path))
    # should have created an output file
    assert any(p.endswith('.docx') for p in out)
