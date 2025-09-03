# DocFlow

Questa documentazione descrive i componenti del progetto DocFlow, come comunicano tra loro e come usarli sia da riga di comando che programmaticamente.
## Panoramica

DocFlow è un piccolo framework per generare documenti (DOCX, PPTX) combinando azioni che producono testo/immagini con template Office. Le componenti principali sono:
- CLI: comandi per inizializzare un progetto, validare la config, eseguire una dry-run o generare i documenti.
- Config: definisce la forma del file YAML di configurazione (`src/docflow/config.py`).
- Actions: moduli che producono output (testo, immagini, variabili). Attualmente ci sono due tipi principali: `GenerativeAction` (mock) e `CodeAction` (esegue codice Python fornito dall'utente).
- Adapters: adapter per template Office — `DocxAdapter` e `PptxAdapter` — responsabili del caricamento del template, sostituzione dei placeholder e inserimento di immagini.
- Prompt builder / KB: componenti per costruire prompt (Jinja, file .py) e preparare conoscenza (kb) per le azioni.

## Architettura e comunicazione tra moduli
- L'entrypoint primario è la CLI (`src/docflow/cli/app.py`). La CLI carica la configurazione con `load_config(path)`.
- `load_config` normalizza percorsi e crea un oggetto `AppConfig` (Pydantic). Questo oggetto contiene:
	- `project`: informazioni su base_dir, output_dir, temp_dir
	- `ai`: configurazione provider AI (mock/default)
	- `workflow`: lista di `actions` e `templates`
- La CLI esegue le azioni in ordine; ogni azione riceve il contesto `ctx` (dizionario condiviso) ed eventualmente aggiorna `ctx` con `vars` o valori binari (immagini).
- Dopo le azioni, la CLI sceglie un adapter per ogni template (`docx`/`pptx`) e chiama l'adapter per applicare i valori e salvare il file finale.

## Componenti principali (dettagli)
### Config

- File: `src/docflow/config.py`
- Funzione: `load_config(path: str) -> AppConfig`
- Forma: `AppConfig` usa Pydantic; le entità rilevanti sono `ActionConfig` (id, type, prompt, code, returns, ecc.) e `TemplateConfig` (path, adapter).
- Normalizzazione: i percorsi relativi vengono risolti rispetto a `base_dir` (di solito la directory del progetto o la cartella del file di config).

### CLI
- File principali: `src/docflow/cli/app.py` (implementazione principale) e `src/docflow/cli.py` (shim di compatibilità).
- Comandi utili:
	- `init`: crea un esempio di config e template (usa `python-docx`/`python-pptx` se presenti)
	- `config-validate`: tenta di caricare la config
	- `dry-run`: esegue le azioni in mock e stampa il contesto finale e il prompt risolto del primo step
	- `run`: esegue l'intero workflow e scrive i file di output
	- `inspect-template`: elenca i placeholder trovati in un template

Esempi CLI (PowerShell):
```powershell
python -m docflow.cli init
python -m docflow.cli config-validate config/example.config.yaml
python -m docflow.cli dry-run config/example.config.yaml
python -m docflow.cli run config/example.config.yaml
python -m docflow.cli inspect-template templates/demo_template.docx --adapter docx
```

### Actions

- `GenerativeAction` (`src/docflow/core/actions/generative.py`): mock che produce un testo (`result_text`), un'immagine PNG in byte e un insieme di `vars` (es. `greeting`). È pensato come esempio/placeholder per integrazione con provider AI.
- `CodeAction` (`src/docflow/core/actions/code.py`): esegue codice Python inline (campo `code`) o da file (`code_file`) in un processo isolato. Lo script riceve le variabili di input come JSON su stdin e può restituire nuove variabili stampando una linea `VARS_JSON={...}` su stdout. Non è più obbligatorio definire una funzione `run(vars)`.

Buone pratiche per `CodeAction`:
- Restituire `vars` per aggiornare il contesto.
- Restituire immagini come `bytes` (es. PNG) in chiavi con prefisso `image` (p.es. `image_chart`) così gli adapter le riconoscono.

### Adapters

- `DocxAdapter` e `PptxAdapter` (in `src/docflow/adapters/`) implementano l'interfaccia `DocumentAdapter`:
	- `load()` carica il documento
	- `list_placeholders()` restituisce i nomi dei placeholder trovati
	- `apply(mapping, global_vars)` applica i valori (sostituzione Jinja-style `{{ name }}` e placeholder immagini `{{image:key}}`)
	- `save(out_path)` salva il file risultante

Placeholder supportati:
- Variabili: `{{ name }}` o `{{some:var}}` — il codice rimuove eventuali prefissi (`something:var`) e cerca la chiave nel `mapping` o in `global_vars`.
- Immagini: `{{image:key}}` — se la chiave `key` nel contesto è un `bytes` viene inserita un'immagine nel documento (dimensione fissa nel codice). Se è una stringa path (solo PPTX), il codice prova ad aprire il file.

### Prompt builder e KB

- File: `src/docflow/runtime/prompt_builder.py`
- Il progetto supporta tre modi per costruire prompt per azioni generative:
	- Template inline (stringa) con Jinja2
	- File `.j2` (Jinja)
	- File `.py` che espone `build_prompt(vars, kb_text)`
- KB (knowledge base): esiste una componente che può caricare file Markdown, sintetizzarli o fornirli inline alle azioni (strategia configurabile).

### Attachments (inviare file alle action/provider)

DocFlow ora supporta la dichiarazione di `attachments` per un'azione. Le opzioni principali per ogni action sono:

- `attachments.paths`: lista di percorsi o glob (assoluti o relativi) che indicano i file da allegare.
- `attachments.as_text`: se true, DocFlow estrae il testo dai file (md, txt, docx, pdf, csv, json) e lo concatena al prompt.
- `attachments.upload`: se true, e se il provider AI implementa `upload_file`, DocFlow caricherà i file al provider e passerà i riferimenti remoti all'API (chiave `attachments`).
- `attachments.mime`: mime type suggerito per l'upload (es. `application/pdf`).

Esempio di action con attachments:

```yaml
- id: gen_doc
	type: generative
	prompt: "Analizza i documenti allegati e fornisci un sommario"
	attachments:
		paths: ["kb/*.pdf", "kb/data.csv"]
		as_text: true
		upload: true
		mime: "application/pdf"
```

Comportamento:

- Se `upload` è true, DocFlow prova a chiamare `ai_client.upload_file(path, mime_type=...)` per ogni file. L'implementazione è provider-specifica (MockProvider restituisce un riferimento di test; Gemini/OpenAI hanno wrapper condizionali).
- Se l'upload fallisce o non è disponibile, e `as_text` è true (o sempre, se non ci sono refs remoti), il testo viene estratto localmente usando `src/docflow/kb/loader.py`.
- I riferimenti remoti (se presenti) vengono inviati alla chiamata di generazione come `attachments=[...]` — il provider decide come usarli.

Provider supporto upload (implementazione attuale):

- MockProvider: `upload_file` restituisce un riferimento fittizio (utile per test).
- GeminiProvider: se `google.generativeai` è installato e espone `upload_file`, il wrapper lo usa.
- OpenAIProvider: usa `openai.File.create` quando disponibile (legacy API). Potrebbe richiedere permessi/uso specifico (es. purpose 'answers').

Best practices:

- Per documenti di testo (md/txt/docx/json/csv) preferisci `as_text` per trasparenza e privacy.
- Per file complessi (PDF con immagini/tabelle) considera `upload` quando il provider supporta processing nativo dei file.
- Per retrieval frequente, considera indicizzazione separata (embeddings + vector DB) piuttosto che upload ad ogni chiamata.


## Esempi completi

1) Esempio di config YAML (semplificato)

```yaml
project:
	base_dir: .
	output_dir: build/output

ai:
	provider: mock

workflow:
	actions:
		- id: gen1
			type: generative
			returns: image
			prompt: |
				Say hello to {{name}}
		- id: code1
			type: code
			returns: image
			code: |
				import matplotlib.pyplot as plt
				import io
				import json
				import os

				# Create a dummy chart
				fig, ax = plt.subplots()
				ax.plot([1, 2, 3], [1, 4, 9])
				ax.set_title(vars.get('greeting', 'chart'))

				# Save it to a temporary path
				fpath = "build/tmp/chart.png"
				os.makedirs(os.path.dirname(fpath), exist_ok=True)
				fig.savefig(fpath, format='png')

				# Return vars and the path to the generated image
				print('VARS_JSON=' + json.dumps({'charted': True}))
				print(fpath)

	templates:
		- path: templates/demo_template.docx
			adapter: docx
		- path: templates/demo_template.pptx
			adapter: pptx
```

2) Esempio di template DOCX (snippet Jinja-like)

- `templates/demo_template.docx` può contenere testi come:
	- `Hello {{greeting}}`
	- `Name: {{name}}`
	- `{{image:image}}`  (qui l'adapter inserirà l'immagine se disponibile)

3) Esempio `CodeAction` inline

Nel campo `code` dell'action inserire uno script Python. Lo script riceve un dizionario di variabili come JSON su stdin e può restituire un dizionario di nuove variabili stampando `VARS_JSON={...}` su stdout. Vedere l'esempio YAML sopra.

4) Usare `inspect-template` per vedere i placeholder

```powershell
python -m docflow.cli inspect-template templates/demo_template.docx --adapter docx
```

## Uso programmatico

Caricare la config e usare gli adapter direttamente:

```python
from src.docflow.config import load_config
from src.docflow.adapters.docx_adapter import DocxAdapter

cfg = load_config('config/example.config.yaml')
adapter = DocxAdapter('templates/demo_template.docx')
adapter.load()
placeholders = adapter.list_placeholders()
adapter.apply(mapping={'name':'Alice','image': image_bytes}, global_vars={})
adapter.save('build/output/demo.docx')
```

Nota: i moduli si trovano nel pacchetto `docflow` (API stabile).

## Testing e sviluppo

- I test sono presenti nella cartella `tests/`. Per eseguirli in ambiente con dipendenze installate:

```powershell
python -m pytest -q
```

I test possono richiedere librerie (python-docx, python-pptx, matplotlib). Se mancano, alcuni test vengono saltati.

## Note e prossimi passi

- L'azione `GenerativeAction` è attualmente un mock: per collegare un provider reale (OpenAI/Gemini/Azure) c'è il punto di estensione in `src/docflow/ai` e nella sezione `ai` della config.
- È possibile aggiungere nuovi adapter estendendo `DocumentAdapter` in `src/docflow/adapters/base.py`.

## Logging

- `src/docflow/logging_lib.py` espone `setup_logger(name, json_file=None)` e `json_log_entry(logger, obj)` per log strutturati in formato json-line.
- Per attivare logging strutturato e scrivere su file JSON:

```python
from src.docflow.logging_lib import setup_logger

logger = setup_logger('docflow', json_file='build/logs/docflow.json')
logger.info('starting', extra={'stage': 'init'})
```

- Nota: i provider AI e le action usano chiamate di logging; abilitare il logger su file facilita il tracciamento degli upload e degli errori.
- Requisiti: se usi PDF nel tuo KB, assicurati che `pypdf` sia installato (è elencato in `requirements.txt` e `pyproject.toml`).
 - Esempio: per vedere un esempio pratico che usa `attachments`, guarda `config/example.config_with_attachments.yaml` incluso nel repository.
 
### Uso di `.env` e `python-dotenv`

Per comodit e0 puoi mettere le chiavi API in un file `.env` nella root del progetto. Questo repository include `.env` in `.gitignore` per evitare commit accidentali.

Esempio di `.env` (non commettere questo file):

```
GEMINI_API_KEY=la_tua_chiave
OPENAI_API_KEY=la_tua_chiave_openai
```

La CLI carica automaticamente `.env` quando eseguita (se `python-dotenv`  e8 installato). In codice Python usa `python-dotenv` oppure `os.getenv` dopo il caricamento:

```python
from dotenv import load_dotenv
import os

load_dotenv()  # carica .env dalla working directory
key = os.getenv('GEMINI_API_KEY')
```

`python-dotenv`  e8 presente in `requirements-dev.txt` per sviluppo; installalo nelle tue dipendenze di sviluppo se vuoi usarlo localmente.
Se vuoi, posso: generare esempi reali nei file `config/` e `templates/`, integrare un provider AI mock più ricco, o aggiungere documentazione API dei singoli moduli (docstrings estesi).
DocFlow scaffold\n\nCommands:\n- python -m docflow.cli init\n- python -m docflow.cli config-validate config/example.config.yaml\n- python -m docflow.cli dry-run config/example.config.yaml\n- python -m docflow.cli run config/example.config.yaml\n
