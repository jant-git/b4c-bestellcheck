# So nutzt ihr den Prototyp (für das Team)

> Bestell-Check B4C · Google-Cloud-Projekt `b4c-bestellcheck-hs26` · Region Zürich (`europe-west6`) · **Alle Daten sind synthetisch.**
> Es gibt drei Wege: **A** nur anschauen, **B** selbst einen Lauf starten und freigeben, **C** lokal ohne Cloud.

## Voraussetzung: Zugang zum Projekt
Jan gibt euch einmal Zugang mit eurem ZHAW-Konto (`…@students.zhaw.ch`). **Dafür braucht eure ZHAW-Adresse ein Google-Konto.** Die ZHAW-Adresse ist ein Microsoft-Konto, deshalb müsst ihr das Google-Konto einmal selbst anlegen: [accounts.google.com/signup](https://accounts.google.com/signup) → «Konto erstellen» → «Bestehende E-Mail-Adresse verwenden», ca. 2 Minuten, ohne Kreditkarte. Sonst meldet Google beim Freischalten «User does not exist». Ihr bekommt drei Rollen:

| Rolle | Wozu |
|---|---|
| Betrachter (`roles/viewer`) | alles in der Konsole ansehen: Workflow, Job, Logs, Tabellen |
| BigQuery-Jobnutzer (`roles/bigquery.jobUser`) | Abfragen in BigQuery ausführen |
| Workflows Invoker (`roles/workflows.invoker`) | einen Lauf starten und die Freigabe senden |

Damit könnt ihr nichts löschen und nichts umbauen. Danach in der Konsole oben das Projekt **b4c-bestellcheck-hs26** wählen.

---

## A Nur anschauen (Browser, 5 Minuten)

| Was | Link | Was ihr seht |
|---|---|---|
| **Pipeline-Läufe** | [Workflows → b4c-bestellcheck → Ausführungen](https://console.cloud.google.com/workflows/workflow/europe-west6/b4c-bestellcheck/executions?project=b4c-bestellcheck-hs26) | Einen Lauf anklicken, Ansicht mit Grafik: welchen Weg der Lauf genommen hat. Lauf `7a261da2…` = niemand gibt frei → Eskalation. Lauf `9acdbe36…` = Inhaber gibt frei |
| Job | [Cloud Run → Jobs → b4c-wochenlauf](https://console.cloud.google.com/run/jobs/details/europe-west6/b4c-wochenlauf/executions?project=b4c-bestellcheck-hs26) | Je Lauf 4 Ausführungen (seit SW11): `laden`, `transformieren`, `entwurf`, `freigabe`; unter «Logs» die Meldungen |
| Daten und Ergebnis | [BigQuery](https://console.cloud.google.com/bigquery?project=b4c-bestellcheck-hs26) → Dataset `b4c_bestellcheck` | Sternschema (`dim_*`, `fakt_*`), `bestellentwurf`, `freigabe_protokoll`, `bestellmail_entwurf`. Fertige Abfragen: [`prototyp/abfragen.sql`](prototyp/abfragen.sql) einfügen und «Ausführen» |
| Eskalationen | [Logs Explorer](https://console.cloud.google.com/logs/query?project=b4c-bestellcheck-hs26), Abfrage `jsonPayload.b4c_ereignis:*` | FREIGABE_NOETIG, ESKALATION_STELLVERTRETUNG, ESKALATION_KEINE_FREIGABE |

### Data Engineering ansehen (SW11, Erklärung in [`04-data-engineering.md`](04-data-engineering.md))

| Was | Wo | Was ihr seht |
|---|---|---|
| **Transformation** (dbt) | Cloud Run → Jobs → b4c-wochenlauf → eine Ausführung `transformieren` → «Logs» | dbt baut Tabelle für Tabelle (`stg_*`, dann `dim_*`/`fakt_*`) und meldet jede Prüfung mit `PASS`, `WARN` oder `FAIL` (ein Modell, das nicht gebaut werden konnte, mit `ERROR`) |
| Stufen in BigQuery | Dataset `b4c_bestellcheck`: `roh_*` → `stg_*` → `dim_*`/`fakt_*` | Tabelle anklicken → «Schema»: Bei `fakt_bestand` stehen die Begriffe aus dem Anforderungskatalog als Beschreibung |
| **Prüfungen** Q01–Q14 | Abfrage 6 in [`prototyp/abfragen.sql`](prototyp/abfragen.sql) | OK / WARNUNG / FEHLER pro Prüfung im neuesten Lauf |
| Schranke zu | Workflows → Ausführungen → ein Lauf mit Status «Fehlgeschlagen» | In der Fehlermeldung steht, welche Prüfung FEHLER hatte (z. B. Q06 beim Stichtag 23.11.) |
| **Alarm** | [Monitoring → Alerting](https://console.cloud.google.com/monitoring/alerting?project=b4c-bestellcheck-hs26) | Richtlinie «b4c-bestellcheck fehlgeschlagen», Vorfälle (auch geschlossene: «Show closed») |
| **Zeitplan** | [Cloud Scheduler](https://console.cloud.google.com/cloudscheduler?project=b4c-bestellcheck-hs26) | `b4c-montag`, jeden Montag 07:30, nächste Ausführung |
| Rohdaten pro Lauf | Abfrage 7 | Jeder Lauf hat seine eigene Kopie, nichts wird überschrieben |
| Gleiches Ergebnis | Abfrage 8 | Alle Läufe mit Stichtag 9.11. (SW10 und SW11): pro Produkt genau 1 Ergebnis |
| Bereinigung | Abfrage 9 | Wie viele Zeilen R1–R5 im letzten Lauf betroffen haben |

---

## B Selbst einen Lauf starten und freigeben (Browser, ca. 10 Minuten, nichts installieren)

> Ausführlicher, mit erwarteten Ausgaben, fertigen Befehlen pro Stichtag und einem Ablauf für die Präsentation: [`SHOWCASE.md`](SHOWCASE.md).

**1 Lauf starten.** [Workflows → b4c-bestellcheck](https://console.cloud.google.com/workflows/workflow/europe-west6/b4c-bestellcheck/executions?project=b4c-bestellcheck-hs26) → **Ausführen**. Ins Eingabefeld:
```json
{"stichtag": "2026-11-16", "frist_inhaber_s": 1800, "frist_stellvertretung_s": 1800}
```
→ **Ausführen**. (Fristen in Sekunden: 1800 = 30 Minuten pro Rolle.)

**2 Warten, bis der Lauf auf euch wartet** (ca. 3 Minuten). In der Grafik steht der Lauf dann beim Schritt `warten`.

**3 Cloud Shell öffnen** (Symbol `>_` oben rechts in der Konsole; ein Terminal im Browser, gcloud und bq sind schon da):
```bash
gcloud config set project b4c-bestellcheck-hs26
```
Dann `freigeben.py` holen: entweder `git clone <Repo-URL>` (wenn Jan das Repo geteilt hat) oder im Cloud-Shell-Menü **⋮ → Hochladen** die Datei `prototyp/freigeben.py` hochladen.

**4 Entwurf ansehen:**
```bash
python3 freigeben.py --zeigen
```

**5 Freigeben** (als Inhaber, Mengen aus Schritt 4 übernehmen oder ändern):
```bash
python3 freigeben.py --rolle Inhaber --freigeben --menge Muesliriegel=50 --menge Cookies=23 --menge Chips=38 --menge Nuesse=26
```
Kommt «Antwort gesendet (HTTP 200)», verbucht der Workflow die Freigabe in ca. 1 Minute.

**6 Ergebnis ansehen:** in BigQuery Abfrage 4 und 5 aus [`prototyp/abfragen.sql`](prototyp/abfragen.sql).

### Stichtage, die funktionieren (die synthetischen Daten reichen vom 26.10. bis 21.11.2026)

| Stichtag | Was passiert | Mengen (Muesli/Cookies/Chips/Nüsse) |
|---|---|---|
| `2026-10-26` | Keine Vorwarnung: alles **grün** → Sammelfreigabe reicht (`--freigeben` ohne `--menge`) | 8 / 7 / 13 / 5 |
| `2026-11-02` | Vorwarnung VW-01 bekannt: alles **gelb**; Cookies zusätzlich «Bestand geschätzt» | 62 / 55 / 56 / 46 |
| `2026-11-09` | gelb (S6), Reichweite 0.8–1.1 Wochen < Ziel 1.5 | 30 / 40 / 33 / 42 |
| `2026-11-16` | Störungswoche: gelb (S6), Cookies zusätzlich S1 | 50 / 23 / 38 / 26 |

In der Cloud gelaufen ist bisher der 9.11. Die anderen Stichtage sind lokal mit denselben Regeln gerechnet.

### Was ihr ausprobieren könnt (gut für die Präsentation)

| Ausprobieren | Befehl (Schritt 5 abändern) | Erwartung im `freigabe_protokoll` |
|---|---|---|
| Menge ändern | `--menge Chips=35` statt 38 | «geändert freigegeben» |
| Gelb ohne Zahl freigeben («durchklicken») | `--rolle Inhaber --freigeben` ohne `--menge` | «nicht freigegeben: Einzelbestätigung fehlt» |
| Unbefugte Freigabe | `--rolle Stellvertretung …` während der Inhaber-Frist | «nicht befugt: Rolle 'Stellvertretung' in Phase inhaber» |
| Über der Obergrenze | `--menge Chips=90` (Obergrenze 70) ohne `--kommentar` | «nicht freigegeben: 90 über Obergrenze 70» |
| Ablehnen | `--rolle Inhaber --ablehnen --kommentar "Störung abgesagt"` | «abgelehnt», Menge 0 |
| Eskalation | gar nicht antworten | nach Frist 1: Anfrage an die Stellvertretung, nach Frist 2: «nichts bestellt, Inhaber anrufen» |

Pro Lauf wird genau eine Antwort verbucht. Danach ist der Lauf fertig. Für den nächsten Versuch startet ihr einen neuen Lauf.

### Bitte beachten
- Jeder Lauf kostet wenige Rappen (Education-Guthaben). Probiert ruhig ein paar Läufe, aber nicht in einer Schleife.
- Zwei Läufe gleichzeitig gehen, aber `freigeben.py` antwortet immer auf die **neueste** offene Anfrage.
- Nichts löschen, nichts umbauen. Aufbau und Aufräumen macht Jan ([`prototyp/ANLEITUNG.md`](prototyp/ANLEITUNG.md)).
- Die «Rolle» in der Freigabe ist im Prototyp eine Angabe. Geprüft und protokolliert wird euer Google-Konto.

---

## C Lokal ohne Cloud (Python 3, 1 Sekunde)

```bash
cd kleinklasse-automation/prototyp
python3 -m unittest -v test_regeln      # 10 Tests der Regeln
python3 lokal_lauf.py 2026-11-09        # Bestellentwurf für einen Stichtag
```
Nur Python-Standardbibliothek, keine Installation. Die Daten liegen in `prototyp/daten/`.
