from docflow.runtime.prompt_builder import build_prompt_for_action


def test_inline_prompt():
    action = {'prompt': 'Hello {{name}}', 'input_vars': ['name']}
    out = build_prompt_for_action(action, {'name': 'Alice'}, None)
    assert 'Hello Alice' in out


def test_j2_file_prompt(tmp_path):
    f = tmp_path / 'p.j2'
    f.write_text('Title: {{name}} -- KB: {{kb}}')
    action = {'prompt_file': str(f), 'input_vars': ['name']}
    out = build_prompt_for_action(action, {'name': 'Bob'}, 'kbtext')
    assert 'Title: Bob' in out and 'KB: kbtext' in out


def test_py_prompt(tmp_path):
    f = tmp_path / 'p.py'
    f.write_text('def build_prompt(input_vars, kb_text):\n    return f"PYPROMPT: {input_vars.get(\'name\')} KB:{kb_text}"')
    action = {'prompt_fn': str(f) + ':build_prompt', 'input_vars': ['name']}
    out = build_prompt_for_action(action, {'name': 'Carla'}, 'kbb')
    assert 'PYPROMPT: Carla' in out and 'KB:kbb' in out
 
