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

## Setup e Installazione

Prima di utilizzare DocFlow, è necessario installare il pacchetto in modalità sviluppo:

```powershell
# Installa le dipendenze
pip install -r requirements.txt -r requirements-dev.txt

# Installa il pacchetto in modalità sviluppo (editable mode)
pip install -e .
```

Il comando `pip install -e .` è necessario per rendere il modulo `docflow` importabile da Python. Senza questo passaggio, riceverai un errore `ModuleNotFoundError: No module named 'docflow'`.

Esempi CLI (PowerShell):
```powershell
python -m docflow.cli.app init
python -m docflow.cli.app config-validate config/example.config.yaml
python -m docflow.cli.app dry-run config/example.config.yaml
python -m docflow.cli.app run config/example.config.yaml
python -m docflow.cli.app inspect-template templates/demo_template.docx --adapter docx
```

**Nota**: Il modulo CLI corretto è `docflow.cli.app`, non solo `docflow.cli`.

### Actions

- `GenerativeAction` (`src/docflow/core/actions/generative.py`): mock che produce un testo (`result_text`), un'immagine PNG in byte e un insieme di `vars` (es. `greeting`). È pensato come esempio/placeholder per integrazione con provider AI.
- `CodeAction` (`src/docflow/core/actions/code.py`): esegue codice Python inline (campo `code`) o da file (`code_file`) in un processo isolato. Lo script può definire una funzione `main(ctx)` che riceve il contesto completo e può restituire un dizionario di variabili (se `returns: vars`) o output diretto.

Buone pratiche per `CodeAction`:
- Restituire `vars` per aggiornare il contesto.
- Restituire immagini come `bytes` (es. PNG) in chiavi con prefisso `image` (p.es. `image_chart`) così gli adapter le riconoscono.

### Sistema di Variabili e Contesto

DocFlow gestisce le variabili attraverso un **contesto condiviso** (`ctx`) che viene passato tra tutte le azioni del workflow.

#### **Flusso delle variabili:**
```
Variabili Input → Azione → Variabili Output → Contesto → Prossima Azione
```

#### **Contesto condiviso (`ctx`):**
- **Dizionario globale** che accumula tutte le variabili durante l'esecuzione
- Ogni azione riceve `ctx` come input e può aggiornarlo
- Le variabili sono disponibili per template Jinja2 e azioni successive

#### **Tipi di output per le azioni (`returns`):**

```yaml
returns: text    # Salva risultato in ctx[action_id]
returns: image   # Salva path immagine in ctx[action_id]
returns: vars    # Aggiunge dizionario di variabili al contesto
```

#### **Esempio di flusso variabili:**

```yaml
workflow:
  actions:
    # 1. Inizializzazione variabili
    - id: setup
      type: code
      returns: vars    # Aggiunge variabili al contesto
      code: |
        def main(ctx):
            return {
                'azienda': 'Altilia',
                'tipo_report': 'mensile'
            }
    
    # 2. Generazione usando variabili precedenti
    - id: genera_intro
      type: generative
      returns: text    # Salva in ctx["genera_intro"]
      prompt: "Scrivi introduzione per {{tipo_report}} di {{azienda}}"
      kb:
        enabled: true
        paths: ["data/*.pdf"]
        strategy: inline
    
    # 3. Calcolo con accesso a tutto il contesto
    - id: calcola_metriche
      type: code
      returns: vars
      code: |
        def main(ctx):
            # Accede a variabili precedenti
            azienda = ctx.get('azienda', '')
            intro = ctx.get('genera_intro', '')
            
            return {
                'fatturato': 150000,
                'clienti': 45
            }
```

**Stato del contesto durante l'esecuzione:**
```python
# Dopo "setup"
ctx = {'azienda': 'Altilia', 'tipo_report': 'mensile'}

# Dopo "genera_intro"  
ctx = {
    'azienda': 'Altilia',
    'tipo_report': 'mensile', 
    'genera_intro': 'Benvenuti al report mensile...'
}

# Dopo "calcola_metriche"
ctx = {
    'azienda': 'Altilia',
    'tipo_report': 'mensile',
    'genera_intro': 'Benvenuti al report mensile...',
    'fatturato': 150000,
    'clienti': 45
}
```

#### **Variabili nei template:**
I template Office possono accedere a tutte le variabili in `ctx`:

```docx
<!-- Nel template DOCX -->
Azienda: {{azienda}}
Tipo: {{tipo_report}} 
Introduzione: {{genera_intro}}
Fatturato: {{fatturato}}
Clienti: {{clienti}}
```

#### **Variabili iniziali:**
**Non esistono variabili globali dichiarabili nel YAML**. Puoi inizializzarle con:

1. **Prima azione di setup:** Usa `type: code` con `returns: vars`
2. **Hardcode nei prompt:** Inserisci valori fissi direttamente
3. **File esterni:** Carica da JSON/CSV con azioni code

#### **Best practices variabili:**
- ✅ Usa nomi descrittivi (`fatturato_mensile` vs `f1`)
- ✅ Inizializza variabili comuni in una prima azione
- ✅ Organizza azioni in sequenza logica
- ✅ Usa `returns: vars` per dati calcolati
- ✅ Usa `returns: text/image` per contenuto finale
- ❌ Non puoi modificare variabili di azioni precedenti
- ❌ Non fare affidamento su ordine non sequenziale

### Adapters

- `DocxAdapter` e `PptxAdapter` (in `src/docflow/adapters/`) implementano l'interfaccia `DocumentAdapter`:
	- `load()` carica il documento
	- `list_placeholders()` restituisce i nomi dei placeholder trovati
	- `apply(mapping, global_vars)` applica i valori (sostituzione Jinja-style `{{ name }}` e placeholder immagini `{{image:key}}`)
	- `save(out_path)` salva il file risultante

Placeholder supportati:
- Variabili: `{{ name }}` o `{{some:var}}` — il codice rimuove eventuali prefissi (`something:var`) e cerca la chiave nel `mapping` o in `global_vars`.
- Immagini: `{{image:key}}` — se la chiave `key` nel contesto è un `bytes` viene inserita un'immagine nel documento (dimensione fissa nel codice). Se è una stringa path (solo PPTX), il codice prova ad aprire il file.

### Prompt builder e Knowledge Base (KB)

- File: `src/docflow/runtime/prompt_builder.py`
- Il progetto supporta tre modi per costruire prompt per azioni generative:
	- Template inline (stringa) con Jinja2
	- File `.j2` (Jinja)
	- File `.py` che espone `build_prompt(vars, kb_text)`

### Sistema KB Unificato

DocFlow implementa un sistema unificato di Knowledge Base che combina estrazione di testo e upload di file binari. Tutte le configurazioni sono gestite tramite il parametro `kb`:

**Configurazione KB:**
```yaml
kb:
  enabled: true
  strategy: "inline"  # inline, upload, hybrid, summarize, retrieve
  paths: ["data/*.pdf", "docs/*.md", "kb/**/*.txt"]
  max_chars: 10000   # limite caratteri per strategia inline
  upload: true       # carica file binari ai provider AI
  as_text: true      # estrai testo dai file
  mime_type: "application/pdf"  # MIME type per upload
```

**Strategie KB disponibili:**

1. **`inline`**: Estrae testo dai file e lo include nel prompt
   - Parametrizzabile con `max_chars` per limitare la lunghezza
   - Supporta tutti i formati: PDF, DOCX, MD, TXT, JSON, CSV

2. **`upload`**: Carica file binari direttamente ai provider AI
   - Utilizza le API native dei provider (Gemini File API, OpenAI Files)
   - Rilevamento automatico MIME type
   - Mantiene file binari nativi per migliore elaborazione AI

3. **`hybrid`**: Combina upload binario + testo estratto
   - Offre il meglio di entrambi gli approcci
   - File binari per elaborazione AI nativa + testo per trasparenza

4. **`summarize`**: Crea riassunti automatici dei documenti
   - Genera snippet di ~300 caratteri per documento
   - Ideale per overview di grandi quantità di contenuto

5. **`retrieve`**: Ricerca semantica nel contenuto
   - Trova sezioni rilevanti basate sulle variabili del contesto
   - Estrae contesto di ~400 caratteri attorno alle corrispondenze

**Esempio completo di action con KB:**

```yaml
- id: analizza_documenti
  type: generative
  prompt: "Analizza i documenti della knowledge base e fornisci insights"
  kb:
    enabled: true
    strategy: "hybrid"
    paths: ["knowledge/*.pdf", "reports/**/*.docx", "data/*.json"]
    max_chars: 15000
    upload: true
    as_text: true
```

### Best Practices per Knowledge Base

**Scelta della strategia:**
- **`inline`**: Ideale per documenti di testo (MD, TXT, JSON) dove vuoi trasparenza e controllo del contenuto
- **`upload`**: Migliore per PDF complessi con immagini/tabelle, sfrutta l'elaborazione AI nativa
- **`hybrid`**: Quando hai bisogno di entrambi gli approcci per analisi complete
- **`summarize`**: Per overview rapide di grandi volumi di documenti
- **`retrieve`**: Per ricerche mirate e contestuali nella knowledge base

**Ottimizzazione performance:**
- Usa `max_chars` appropriato per limitare il token usage (default: 10000)
- Per upload frequenti, considera cache o indicizzazione separata
- Glob pattern specifici (`*.pdf`) sono più efficienti di pattern generici (`**/*`)

**Gestione file:**
- Organizza i file KB in cartelle logiche (`data/`, `knowledge/`, `reports/`)
- Usa naming conventions consistenti per facilitare glob pattern
- Monitora le dimensioni dei file per evitare timeout di upload

**Sicurezza e privacy:**
- `inline` mantiene file locali (più sicuro per dati sensibili)  
- `upload` invia file ai provider AI (verifica policy di privacy)
- Considera `hybrid` per bilanciare funzionalità e controllo dati

**Supporto provider per upload:**
- **MockProvider**: Supporto simulato per testing e sviluppo
- **GeminiProvider**: Integrazione nativa con Gemini File API
- **OpenAIProvider**: Supporto OpenAI Files API  
- **Fallback automatico**: Se upload non disponibile, usa estrazione testo locale


## Esempi completi con Knowledge Base

### Esempio 1: KB Inline per analisi documenti

```yaml
# Configurazione per analizzare documenti locali
- id: analizza_vendite
  type: generative
  prompt: |
    Basandoti sui dati della knowledge base, fornisci un'analisi delle vendite:
    - Trend principali
    - Anomalie o insight interessanti
    - Raccomandazioni
  kb:
    enabled: true
    strategy: "inline"
    paths: ["data/vendite*.json", "reports/*.csv"]
    max_chars: 8000
```

### Esempio 2: KB Upload per elaborazione AI nativa

```yaml
# Caricamento diretto di PDF per elaborazione AI
- id: riassumi_contratti
  type: generative
  prompt: "Riassumi i contratti caricati evidenziando clausole chiave"
  kb:
    enabled: true
    strategy: "upload"
    paths: ["contratti/*.pdf", "legal_docs/*.docx"]
    upload: true
    mime_type: "application/pdf"
```

### Esempio 3: KB Hybrid per analisi completa

```yaml
# Combina upload binario + testo estratto
- id: analisi_completa
  type: generative
  prompt: "Analizza i documenti sia come testo che come file binari"
  kb:
    enabled: true
    strategy: "hybrid"
    paths: ["documenti/**/*.pdf"]
    upload: true
    as_text: true
    max_chars: 10000
```

### Esempio 4: KB Summarize per overview

```yaml
# Panoramica rapida di molti documenti
- id: overview_progetto
  type: generative
  prompt: "Fornisci una panoramica generale basata sui riassunti"
  kb:
    enabled: true
    strategy: "summarize"
    paths: ["progetto/**/*.md", "docs/**/*.txt"]
```

### Esempio 5: KB Retrieve per ricerca contestuale

```yaml
# Ricerca intelligente nel contenuto
- id: ricerca_specifica
  type: generative
  prompt: "Cerca informazioni su {{argomento}} nella knowledge base"
  kb:
    enabled: true
    strategy: "retrieve"
    paths: ["knowledge/**/*"]
  vars:
    argomento: "machine learning"
```

### Esempio 1: Config YAML completo con gestione variabili

```yaml
project:
	base_dir: .
	output_dir: build/output

ai:
	provider: mock

workflow:
	actions:
		# Inizializzazione variabili di progetto
		- id: init_progetto
			type: code
			returns: vars
			code: |
				from datetime import datetime
				def main(ctx):
					return {
						'azienda': 'Altilia',
						'data_report': datetime.now().strftime('%d/%m/%Y'),
						'tipo_documento': 'Report Mensile'
					}
		
		# Generazione contenuto con KB e variabili
		- id: genera_analisi
			type: generative
			returns: text
			prompt: |
				Azienda: {{azienda}}
				Data: {{data_report}}
				
				Analizza la knowledge base e crea un'analisi per il {{tipo_documento}}
			kb:
				enabled: true
				strategy: "inline"
				paths: ["knowledge/*.md", "data/*.json"]
				max_chars: 5000
		
		# Calcolo metriche basato su analisi
		- id: calcola_kpi
			type: code
			returns: vars
			code: |
				def main(ctx):
					# Accesso alle variabili precedenti
					analisi = ctx.get('genera_analisi', '')
					azienda = ctx.get('azienda', '')
					
					# Calcoli simulati
					return {
						'vendite_totali': 150000,
						'crescita_percentuale': 12.5,
						'numero_clienti': 45,
						'kpi_principale': 'Crescita positiva'
					}
		
		# Generazione grafici con tutti i dati
		- id: genera_grafico
			type: code
			returns: image
			code: |
				import matplotlib.pyplot as plt
				import os
				
				def main(ctx):
					# Usa le variabili calcolate
					vendite = ctx.get('vendite_totali', 0)
					crescita = ctx.get('crescita_percentuale', 0)
					
					fig, ax = plt.subplots()
					ax.bar(['Vendite', 'Crescita'], [vendite/1000, crescita])
					ax.set_title(f"KPI {ctx.get('azienda', '')}")
					
					fpath = "build/tmp/kpi_chart.png"
					os.makedirs(os.path.dirname(fpath), exist_ok=True)
					fig.savefig(fpath, format='png')
					
					return fpath

	templates:
		- path: templates/report_template.docx
			adapter: docx
```

**Template corrispondente (`templates/report_template.docx`):**
```docx
REPORT {{tipo_documento}} - {{azienda}}
Data: {{data_report}}

ANALISI:
{{genera_analisi}}

METRICHE:
- Vendite Totali: €{{vendite_totali}}
- Crescita: {{crescita_percentuale}}%
- Clienti: {{numero_clienti}}
- KPI: {{kpi_principale}}

GRAFICO:
{{image:genera_grafico}}
```

### Esempio 2: Template DOCX (snippet Jinja-like)

- `templates/demo_template.docx` può contenere testi come:
	- `Hello {{greeting}}`
	- `Name: {{name}}`
	- `{{image:image}}`  (qui l'adapter inserirà l'immagine se disponibile)

### Esempio 3: `CodeAction` inline

Nel campo `code` dell'action inserire uno script Python. Lo script riceve un dizionario di variabili come JSON su stdin e può restituire un dizionario di nuove variabili stampando `VARS_JSON={...}` su stdout. Vedere l'esempio YAML sopra.

### Esempio 4: Usare `inspect-template` per vedere i placeholder

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

## Esempio di esecuzione rapida

Per testare DocFlow con l'esempio fornito:

```powershell
# Dalla directory del progetto
python -m docflow.cli.app run example/config.yaml --verbose
```

Questo comando:
1. Carica la configurazione da `example/config.yaml`
2. Esegue le azioni definite nel workflow (generazione AI, codice Python)
3. Produce il documento finale in `example/build/output/report.docx`
4. Mostra log dettagliati con `--verbose`

## Testing e sviluppo

- I test sono presenti nella cartella `tests/`. Per eseguirli in ambiente con dipendenze installate:

```powershell
python -m pytest -q
```

I test possono richiedere librerie (python-docx, python-pptx, matplotlib). Se mancano, alcuni test vengono saltati.

## Risoluzione problemi comuni

### Errore "ModuleNotFoundError: No module named 'docflow'"

Se ricevi questo errore quando esegui i comandi CLI, significa che il pacchetto non è installato correttamente. Esegui:

```powershell
pip install -e .
```

### Problemi con Knowledge Base

**Errore "No files found matching pattern":**
- Verifica che i percorsi in `kb.paths` siano corretti rispetto a `base_dir`
- Controlla che i file esistano: `ls data/*.pdf` o `dir data\*.pdf`
- Usa percorsi assoluti per debug: `C:\path\to\files\*.pdf`

**Upload fallisce con provider AI:**
- Verifica che le API key siano configurate correttamente
- Controlla che il provider supporti upload (MockProvider solo per test)
- File troppo grandi potrebbero causare timeout - usa `max_chars` per limitare

**Estrazione testo da PDF non funziona:**
- Assicurati che `pypdf` sia installato: `pip install pypdf`
- Alcuni PDF protetti o scansionati potrebbero non essere leggibili
- Considera OCR esterno per PDF image-based

### Errore "Unable to create process using python.exe"

Se pip cerca di usare un Python in un percorso diverso, assicurati di:
1. Attivare il virtual environment corretto
2. Usare il percorso completo del Python del tuo ambiente virtuale
3. Verificare che il virtual environment sia nella directory corretta del progetto

### Problemi con l'ambiente virtuale

Se hai problemi con l'ambiente virtuale, ricrea l'ambiente:

```powershell
# Rimuovi l'ambiente esistente (se presente)
Remove-Item -Recurse -Force .venv

# Crea un nuovo ambiente
python -m venv .venv

# Attiva l'ambiente
.venv\Scripts\Activate.ps1

# Installa le dipendenze
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

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
- Requisiti: per utilizzare il sistema KB con PDF, assicurati che `pypdf` sia installato (incluso in `requirements.txt`).
- Per esempi pratici del sistema KB unificato, consulta:
  - `example/config.yaml` - configurazione reale funzionante
  - `config/example.config.yaml` - esempio base
  - `tests/test_unified_kb.py` - test completi di tutte le strategie
 
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
