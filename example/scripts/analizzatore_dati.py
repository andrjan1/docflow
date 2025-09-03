import json, sys, pathlib

# Legge il file JSON locale accanto alla config (assumendo working dir example)
data_path = pathlib.Path('example/data/dati_vendite.json')
if not data_path.exists():
	# fallback: maybe already inside example/
	alt = pathlib.Path('data/dati_vendite.json')
	data_path = alt if alt.exists() else data_path

try:
	dati = json.loads(data_path.read_text(encoding='utf-8')) if data_path.exists() else {}
except Exception:
	dati = {}

fatturato = dati.get('fatturato_mese_corrente', 0)
unita = dati.get('unita_vendute', 0)
prodotto = dati.get('prodotto', 'N/A')
regione = dati.get('regione', 'N/A')

messaggio = f"Analisi per {prodotto} in {regione}: {unita} unità vendute per un totale di {fatturato} EUR."
print(messaggio)