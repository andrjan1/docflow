from src.docflow.config import load_config
import os

cfg = load_config('config/example.config_with_attachments.yaml')
print('GEMINI_API_KEY from env:', os.getenv('GEMINI_API_KEY'))
