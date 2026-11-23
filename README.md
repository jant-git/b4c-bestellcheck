# Kleinklasse Automation · B4C Bestell-Check mit Freigabe

> **Leitfrage:** «Wie viel soll ich pro Snack bestellen, und gibt es ein Warnsignal?»
> Q-01 (Rang 1): Reicht die Ware bis Störungsende? → **Warnsignal**, Reserve erhöhen (S6)
> Q-02 (Rang 2): Wie viel fehlt bis zum Soll? → **Menge** (S2, S3)
> **Alle Daten sind synthetisch** (MVP SW09, Startwert 8). Gezeigt wird der Ablauf, nicht der Nutzen.

## Wer liest was

| Du willst … | Datei |
|---|---|
| **die Präsentation bauen** | [`PRAESENTATION.md`](PRAESENTATION.md): Kurzfassung, Folienplan, Demo, Zahlen, Fragen |
| **den Prototyp vorführen (Showcase)** | [`SHOWCASE.md`](SHOWCASE.md): Lauf starten, Entwurf ansehen, freigeben, Ergebnis zeigen; Ablauf für die Präsentation |
| **den Prototyp ansehen oder selbst laufen lassen** | [`NUTZUNG.md`](NUTZUNG.md): Konsole, Lauf starten, freigeben, ausprobieren |
| **verstehen, was entschieden wurde** | [`01-automation-decision.md`](01-automation-decision.md): Entscheidung, Ladder, Bedingungen für höher und Rückfall |
| **den Ablauf im Detail** | [`02-konzept.md`](02-konzept.md): Diagramm, Eingaben IR-01–07, Regeln, Dienste, Freigaben, Eskalationen |
| **die Risiken** | [`03-risiken.md`](03-risiken.md): 17 Risiken mit Erkennung, Gegenmassnahme, Rückfall |
| **die Data-Engineering-Ergänzung (SW11) verstehen und erklären** | [`04-data-engineering.md`](04-data-engineering.md): Transformation mit dbt, 14 Prüfungen, Zeitplan, Alarm, Nachweis, Kästen pro Rolle, Begriffe |
| **in Google Cloud aufbauen oder aufräumen** | [`prototyp/ANLEITUNG.md`](prototyp/ANLEITUNG.md) (nur wer das Projekt verwaltet) |

## Ergebnis in drei Sätzen
Der Bestell-Check **rechnet und warnt automatisch**, **bereitet** Reserve und Bestellmenge **vor** und **bestellt nie selbst**.
Jede Menge gibt der Inhaber frei, sonst nach einer Frist die Stellvertretung. Antwortet niemand, wird nichts bestellt.
Höher automatisieren lässt sich erst, wenn die Entscheidregel des Briefs mit echten Vorwarnungen erfüllt ist. In den synthetischen Daten ist sie nicht entscheidbar: 2 Fälle, 1 davon rechtzeitig.

## Ordner

```
kleinklasse-automation/
├── README.md                    ← du bist hier
├── PRAESENTATION.md             Vorlage für die Folien
├── NUTZUNG.md                   Anleitung für das Team
├── 01-automation-decision.md    Deliverable 1: Automation Decision
├── 02-konzept.md                Deliverable 2: Workflow-Konzept
├── 03-risiken.md                Deliverable 3: Fehlentscheidungen, Missbrauch, Rückfall
├── 04-data-engineering.md       SW11: Transformation, Prüfungen, Wiederholbarkeit (für alle Rollen)
├── prototyp/                    Deliverable 4: Mini-Prototyp auf Google Cloud
│   ├── ANLEITUNG.md             Aufbau, Testlauf, Zeitplan, Alarm, Aufräumen (Befehle)
│   ├── workflow.yaml            Google Workflows: laden, transformieren, Schranke, Freigabe, Fristen, Eskalation
│   ├── job/                     Cloud-Run-Job (Python + dbt): laden, transformieren, entwurf, freigabe
│   │   ├── transform/           SW11: dbt-Projekt, Stufe 1 stg_*, Stufe 2 Sternschema, Prüfungen Q01–Q14
│   │   ├── regeln.py            alle Regeln und Schwellen (S1–S6, Ampel, Obergrenze, Freigabe)
│   │   ├── qualitaet.py         Ergebnisse der dbt-Prüfungen → qualitaet_lauf
│   │   ├── bereinigen.py        Bereinigung R1–R5 in Python, nur noch für den lokalen Lauf
│   │   └── main.py, Dockerfile, requirements.txt
│   ├── freigeben.py             menschliche Freigabe (Inhaber / Stellvertretung)
│   ├── abfragen.sql             9 Abfragen zum Vorzeigen in BigQuery (6–9 neu in SW11)
│   ├── daten/                   5 synthetische CSV (Kopie aus dem MVP SW09)
│   ├── test_regeln.py           10 Tests · lokal_lauf.py: Lauf ohne Cloud
│   └── alarm-*.yaml             Alarme: Fehlschlag angelegt (SW11), Hinweis beschrieben
├── SHOWCASE.md                  Vorführen: Lauf starten, freigeben, Ergebnis zeigen
└── unterlagen/                  Mission Brief, Anforderungskatalog (PDF), Modell v5
```

Jede Regel aus dem Konzept steht in `prototyp/job/regeln.py`, jede Stufe der Ladder ist ein Schritt in `prototyp/workflow.yaml` (Tabelle in 02-konzept.md, Abschnitt 9).

## Was in Google Cloud läuft
Projekt `b4c-bestellcheck-hs26`, Region Zürich (`europe-west6`), Education-Guthaben:
- Bucket `b4c-bestellcheck-hs26-daten` (5 CSV)
- BigQuery-Dataset `b4c_bestellcheck`: Rohdaten-Kopie pro Lauf (`roh_*`), Stufe 1 (`stg_*`), Sternschema (2 Dimensionen, 5 Faktentabellen, Faktenkonstellation aus SW09), Prüfungen, Entwurf und Protokoll
- Cloud-Run-Job `b4c-wochenlauf` (Python und dbt)
- Workflow `b4c-bestellcheck`
- Cloud Scheduler `b4c-montag`, Montag 07:30 (seit SW11)
- Alarmrichtlinie `b4c-bestellcheck fehlgeschlagen` mit E-Mail-Kanal (seit SW11)
- Service-Accounts `b4c-job-sa` und `b4c-workflow-sa` (keine neuen in SW11)

**Nachweis (14.11.2026, Stichtag 9.11.):**

| Lauf | Ablauf | Ergebnis in `freigabe_protokoll` |
|---|---|---|
| 1 `7a261da2…` | Qualität 8 OK, 3 WARNUNG, 0 FEHLER → Entwurf 30/40/33/42, alle gelb (S6) → Inhaber antwortet nicht (15 Min.) → Stellvertretung antwortet nicht (15 Min.) | 4 × «keine Freigabe bis Frist: nichts bestellt, Inhaber anrufen», kein Mail-Entwurf |
| 2 `9acdbe36…` | gleicher Entwurf → Inhaber gibt mit `freigeben.py` einzeln frei | 4 × «freigegeben», Rolle Inhaber, Konto protokolliert; Bestellmail-Entwurf mit `versendet = false` |

## Befunde zur Vorleistung (MVP SW09)
1. Die **Entscheidregel** des Briefs fehlte im Code; S6 wurde immer angewendet. Jetzt geprüft, Ergebnis: «zu wenig Fälle».
2. **Q-01 war nicht beantwortet** (keine Reichweite nach IR-02). Jetzt: Reichweite neben dem Ziel 1.5. Am 16.11. reicht sie bei allen vier Produkten nicht (0.9–1.2 Wochen).
3. **Blick in die Zukunft:** S4, S5 und S1 nahmen Daten nach dem Stichtag mit. S4 «dauerhaft aktiv» war die Folge davon. Korrigiert: Am 16.11. sind S4 und S5 ruhig.
4. **Bestellformel IR-03** deckt nur die Lücke zur Reserve, nicht den Wochenabsatz. **Mit dem Inhaber zu klären** (03-risiken.md, R13).

## Bewusst weggelassen
- **Bestellung senden, Lieferanten kontaktieren**: nur als Mail-Entwurf, `versendet = false`.
- **Dashboard, Prognosemodell**: im Brief ausgeschlossen. Ausgabe sind Tabellen in BigQuery und ein Skript.
- **Sprachmodell** für Vorwarnungs-Mails: nur als Ausbaustufe beschrieben («Das Modell liest, die Regel entscheidet»), weil keine Mailtexte vorliegen.
- **Hinweis-Mail «Freigabe nötig»** (`alarm-hinweis.yaml`): beschrieben, nicht angelegt; die Hinweise stehen in Cloud Logging. Angelegt sind seit SW11 der Scheduler und der Fehlschlag-Alarm.
- **Dataplex für die Qualitätsprüfung**: Die dbt-Prüfungen in BigQuery reichen für 160 Zeilen und kosten weniger.
- **Historisierung des Plan-Absatzes** (SCD 2), Kaffee, Frischware, Lieferantenwechsel.
- **Geprüfte Identität in der Freigabe**: Die Rolle ist im Prototyp eine Angabe. Wer überhaupt antworten darf, regelt IAM.

## Mit dem Inhaber zu bestätigen
Schwellen (2 von 4, 2 von 8, 3 %, 7 Tage, 90 %), Obergrenze (1 Wochen-Plan-Absatz), Bestellformel (R13), Fristen (09:00 und 11:00), wie viel «leicht» bei S4 ist, wer Stellvertretung ist.
