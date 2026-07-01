# Mirror del Bollettino CFD Veneto

Mirror automatico, aggiornato ogni 15 minuti, del bollettino di criticità
idrogeologica/idraulica (CFD) pubblicato dalla Regione del Veneto. Il file
JSON viene ripubblicato **byte-identico** all'originale su GitHub Pages, con
CORS aperto, così un'app esterna può leggerlo direttamente via `fetch()`
cross-origin senza passare dal sito della Regione (che non invia header CORS).

## API per app consumer

Sostituisci `<utente>` e `<repo>` con i valori reali del deploy.

| Endpoint | Contenuto |
|---|---|
| `https://<utente>.github.io/<repo>/data/bollettino.json` | Bollettino corrente, bytes identici a quelli pubblicati dalla Regione |
| `https://<utente>.github.io/<repo>/data/meta.json` | Metadati: URL sorgente, nome file, timestamp di fetch, numero bollettino/revisione |
| `https://<utente>.github.io/<repo>/data/archive/<nomefile>.json` | Copie storiche, una per ogni numero+revisione mai pubblicati |

`meta.json`:

```json
{
  "source_url": "https://www.regione.veneto.it/.../BLMultiCfd_31_01_2026-07-01.json/<uuid>",
  "filename": "BLMultiCfd_31_01_2026-07-01.json",
  "fetched_at": "2026-07-01T17:12:03.421Z",
  "num_boll": "031/2026",
  "aggiornamento": "01",
  "data_compilazione": "01/07/2026",
  "ora_compilazione": "17:07:13"
}
```

### Note per il consumer

- **Latenza nel caso peggiore ≈ 15' (intervallo cron) + fino a ~30' di
  slittamento dello scheduler GitHub Actions nei picchi + fino a 10' di cache
  CDN di GitHub Pages** (`max-age=600`). In pratica prevedere un ritardo fino
  a circa 55 minuti rispetto alla pubblicazione originale nel caso peggiore.
- Per bypassare la cache CDN, aggiungere un parametro cache-busting alla
  richiesta: `fetch(url + '?t=' + Date.now())`.
- Per rilevare una nuova revisione, confrontare `meta.json` →
  `num_boll` + `aggiornamento` con l'ultimo valore visto, oppure controllare
  che `fetched_at` sia più recente del proprio ultimo fetch.
- I campi in `note.*` del bollettino (es. `allerta_prevista`) possono essere
  `null` nelle emissioni ordinarie: gestire il caso.
- Se questo mirror non ha ancora completato il primo fetch (subito dopo il
  deploy iniziale), `data/bollettino.json` e `data/meta.json` non esistono
  ancora e le richieste falliranno con 404: gestire questo stato transitorio.

## Come funziona

1. Un workflow GitHub Actions schedulato ogni 15 minuti
   (`.github/workflows/update-bollettino.yml`) esegue
   `scripts/fetch_bollettino.py`.
2. Lo script:
   - scarica la pagina sorgente della Regione e ne estrae il primo link
     `BLMultiCfd*.json` (l'URL cambia a ogni emissione/revisione, incluso un
     UUID Liferay non prevedibile — non viene mai hardcodato);
   - se l'URL non è cambiato dall'ultimo fetch, si ferma senza fare nulla;
   - scarica il JSON come bytes grezzi e lo valida con `json.loads` (il
     server può rispondere con una pagina di errore HTML con status 200,
     quindi non ci si fida del solo status/Content-Type);
   - se la validazione fallisce, i file esistenti non vengono toccati;
   - se ha successo, scrive `data/bollettino.json` (bytes originali, mai
     riserializzati), archivia una copia in `data/archive/` con il nome file
     originale, e aggiorna `data/meta.json`.
3. Il workflow committa e pusha solo se `data/` è effettivamente cambiata.
4. GitHub Pages serve tutti i file con `Access-Control-Allow-Origin: *`.

## Struttura repo

```
/
├── index.html              # pagina di stato/visualizzazione
├── data/
│   ├── bollettino.json     # mirror corrente, byte-identico all'originale
│   ├── meta.json           # metadati di provenienza/freschezza
│   └── archive/            # storico, un file per ogni num+revisione
├── scripts/
│   └── fetch_bollettino.py
└── .github/workflows/
    └── update-bollettino.yml
```

## Limiti noti

- Nessuna garanzia di latenza sotto i 15 minuti (richiederebbe un cron
  dedicato su un server always-on, fuori scope).
- Nessuna notifica push (es. Telegram) sui cambi di stato — estensione
  naturale ma non inclusa in questa release.
- La vista a matrice zona×rischio con colori è un'estensione opzionale non
  ancora implementata; la pagina di stato mostra il JSON raw.
