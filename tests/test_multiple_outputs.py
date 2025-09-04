"""Test multiple outputs functionality"""

from pathlib import Path
from docflow.core.actions.generative import GenerativeAction
from docflow.core.actions.code import CodeAction
from docflow.core.context import ExecutionContext
from docflow.ai.providers.mock import MockProvider
import tempfile
import os


class MultiOutputMockProvider(MockProvider):
    """Mock provider that returns structured responses for testing"""
    
    def generate_text(self, prompt: str, **kwargs):
        if "analizza documento" in prompt.lower():
            return {
                'text': "TESTO: Il documento parla di vendite Q1 2024.\nVARIABILI: vendite=150000, trimestre=Q1, crescita=12.5",
                'meta': {'provider': 'mock'}
            }
        return super().generate_text(prompt, **kwargs)


def test_generative_multiple_outputs():
    """Test generative action with multiple outputs (text + vars)"""
    
    cfg = {
        'id': 'test_multi',
        'type': 'generative',
        'returns': ['text', 'vars'],  # Multiple outputs!
        'prompt': 'Analizza documento e restituisci TESTO e VARIABILI'
    }
    
    action = GenerativeAction(cfg)
    ctx = ExecutionContext()
    ctx.ai_client = MultiOutputMockProvider()
    
    result = action.execute(ctx)
    
    # Should return tuple for multiple outputs
    assert isinstance(result, tuple)
    assert len(result) == 2
    
    text, vars_dict = result
    assert isinstance(text, str)
    assert isinstance(vars_dict, dict)
    
    # Check extracted content
    assert "documento parla di vendite" in text
    assert 'vendite' in vars_dict
    assert vars_dict['vendite'] == '150000'
    assert vars_dict['trimestre'] == 'Q1'


def test_code_multiple_outputs():
    """Test code action with multiple outputs (vars + text)"""
    
    cfg = {
        'id': 'test_code_multi',
        'type': 'code',
        'returns': ['vars', 'text'],  # Multiple outputs!
        'code': '''
import json

def main(ctx):
    # Return both variables and text
    vars_data = {
        'fatturato': 250000,
        'clienti': 50,
        'region': 'Nord'
    }
    text_data = f"Report: {vars_data['fatturato']} EUR da {vars_data['clienti']} clienti"
    
    # For multiple outputs, return tuple
    return vars_data, text_data
        '''
    }
    
    action = CodeAction(cfg)
    ctx = ExecutionContext()
    
    result = action.execute(ctx)
    
    # Should return tuple for multiple outputs
    assert isinstance(result, tuple)
    assert len(result) == 2
    
    vars_dict, text = result
    assert isinstance(vars_dict, dict)
    assert isinstance(text, str)
    
    # Check content
    assert vars_dict['fatturato'] == 250000
    assert vars_dict['clienti'] == 50
    assert '250000 EUR' in text
    assert '50 clienti' in text


def test_backward_compatibility_single_output():
    """Test that single outputs still work (backward compatibility)"""
    
    cfg = {
        'id': 'test_single',
        'type': 'generative',
        'returns': 'text',  # Single output (existing behavior)
        'prompt': 'Generate simple text'
    }
    
    action = GenerativeAction(cfg)
    ctx = ExecutionContext()
    ctx.ai_client = MockProvider()
    
    result = action.execute(ctx)
    
    # Should return ActionResult (existing behavior)
    from docflow.core.results import ActionResult
    assert isinstance(result, ActionResult)
    assert result.kind == 'text'
    assert isinstance(result.data, str)


def test_code_legacy_vars_json():
    """Test code action backward compatibility with VARS_JSON output"""
    
    cfg = {
        'id': 'test_legacy',
        'type': 'code',
        'returns': 'text',
        'code': '''
print('VARS_JSON={"test_var": "test_value", "number": 42}')
print('This is the main output text')
        '''
    }
    
    action = CodeAction(cfg)
    ctx = ExecutionContext()
    
    result = action.execute(ctx)
    
    from docflow.core.results import ActionResult
    assert isinstance(result, ActionResult)
    assert result.kind == 'text'
    assert 'main output text' in result.data
    assert result.vars['test_var'] == 'test_value'
    assert result.vars['number'] == 42


def test_workflow_integration_multiple_outputs(tmp_path):
    """Test that workflow correctly handles multiple outputs"""
    
    from docflow.core.workflow import execute_workflow
    from docflow.core.context import ExecutionContext
    
    # Create test workflow config
    actions = [
        {
            'id': 'multi_action',
            'type': 'generative',
            'returns': ['text', 'vars'],
            'prompt': 'Analizza documento test'
        },
        {
            'id': 'use_vars',
            'type': 'generative', 
            'returns': 'text',
            'prompt': 'Fatturato: {{vendite}}, Crescita: {{crescita}}'
        }
    ]
    
    ctx = ExecutionContext()
    ctx.ai_client = MultiOutputMockProvider()
    
    results = execute_workflow(actions, ctx)
    
    # Check that variables from first action are available to second
    assert 'multi_action' in results
    assert 'use_vars' in results
    
    # Check that variables were properly extracted and made available
    assert 'vendite' in ctx.global_vars
    assert 'crescita' in ctx.global_vars
    assert ctx.global_vars['vendite'] == '150000'
    
    # Second action should have used the variables
    second_result = results['use_vars']
    assert '150000' in str(second_result.data)
    assert '12.5' in str(second_result.data)
