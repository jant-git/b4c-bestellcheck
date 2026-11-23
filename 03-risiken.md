# 03 · Fehlentscheidungen, Missbrauch, Rückfall

> **Leitfrage:** «Wie viel soll ich pro Snack bestellen, und gibt es ein Warnsignal?»
> ✓ = im Prototyp umgesetzt und, wo angegeben, getestet (`test_regeln.py`). ○ = offen, für den Betrieb nötig.
> Daten **synthetisch**: Die Risiken sind fachlich hergeleitet, nicht in echten Daten beobachtet.

## 1 Risiken

| ID | Typ | Auslöser | Folge | Erkennung | Gegenmassnahme |
|---|---|---|---|---|---|
| **R01** | Fehlentscheidung | **Falsche Vorwarnung**: Der Lieferant kündigt eine Störung an, die nicht kommt | S6 verdoppelt das Soll (210 → 420): Überbestand, mehr Verderb (H3, im Modell 49 → 56) | Lieferungen im Störungszeitraum pünktlich und vollständig; Verderb > 3 % (S5) | ✓ S6 nur vorbereitet, gelb, Einzelfreigabe. ✓ Reserve fällt nach Störungsende von selbst auf 0.75 zurück. ✓ Obergrenze. ○ Fehlalarm zählen; ab 1 falschen Vorwarnung zurück auf Stufe 2 |
| **R02** | Missbrauch | **Gefälschte Vorwarnung**: eine Phishing-Mail oder ein Eintrag von jemandem ohne Befugnis | wie R01, gezielt herbeigeführt | Kanal und Datum stehen in der Begründung; Vorwarnung ohne passende Mail des Lieferanten | ✓ Kein Automatismus, der Mensch sieht Kanal und Vorlauf. ○ Nur der Inhaber darf die Vorwarnungs-Liste ändern (Schreibrecht auf den Bucket). ○ Bei S6 beim Lieferanten zurückrufen (zweite Quelle) |
| **R03** | Fehlentscheidung | **Vorwarnung zu spät** (< 7 Tage, z. B. VW-02 mit 1 Tag) | Die Reserve kommt nicht mehr rechtzeitig (Lieferzeit in der Störung 1.5 Wochen), Verkäufe fallen aus (Modell: bis 145) | `vorlauf_tage`; Prüfung Q10 WARNUNG | ✓ Ampel **rot**, nur der Inhaber gibt frei (getestet). ✓ Zählt in der Entscheidregel als «nicht rechtzeitig». Rückfall: S4 |
| R04 | Fehlentscheidung | **Störung ohne erfasste Vorwarnung** (Mail nicht notiert) | S6 bleibt ruhig, das Soll ist zu klein | IR-01-Akzeptanz: Abgleich der Liste mit den Mails | ✓ Text sagt «keine Vorwarnung bekannt», nicht «keine Störung» (getestet). ✓ S4 als Rückfall bleibt im Blick |
| **R05** | Daten | **Bestand nicht gezählt** | Menge falsch, weil der Vorwochenwert gilt | Status «geschätzt», Prüfung Q09 | ✓ Ampel gelb, «bitte zählen», Einzelfreigabe (getestet). Rückfall: zählen und den Lauf neu starten |
| R06 | Daten | Strichliste an einem Tag nicht geführt | Als 0 gelesen, würde S1 zu tief liegen | `dim_datum.strichliste_status = fehlt`, Q08 | ✓ «fehlt», nicht 0; Hinweis im Entwurf |
| **R07** | Betrieb | **S4 immer aktiv** (Alarmmüdigkeit) | Die Warnung wird ignoriert, auch wenn sie stimmt | Wie oft S4 hintereinander aktiv ist | ✓ S4 korrigiert: Im MVP war es nur aktiv, weil Lieferungen nach dem Stichtag und angekündigte mitgezählt wurden. Am 16.11. jetzt ruhig, 0 von 5 (getestet). ✓ S4 nur als Hinweis im Entwurf, keine Mail. ○ 4 Wochen aktiv ohne Reaktion → Stufe 1 |
| **R08** | Fehlentscheidung | **Schwellen nur Annahmen** (2 von 4, 2 von 8, 3 %, 7 Tage, 90 %, Obergrenze) | Signale feuern zu oft oder zu selten | Auswertung nach dem 4-Wochen-Test: Signal gegen tatsächlichen Ausverkauf | ✓ Alle an einer Stelle (`regeln.py`, oben), als Annahme beschriftet. ○ Mit dem Inhaber bestätigen, vorher keine Stufe höher |
| **R09** | Daten | **Synthetische Daten** | Nutzen wird behauptet, ist aber nicht belegt | Spalte `herkunft`, Prüfung Q07 | ✓ Jede Zeile trägt `synthetisch`; fehlt das, schliesst die Schranke (FEHLER). ✓ In jeder Datei steht der Hinweis. Die Ladder steigt nur mit echten Daten |
| **R10** | Mensch | **Freigabe aus Gewohnheit** («durchklicken») | Fehler aus R01 bis R05 gehen ungeprüft durch | `freigabe_protokoll`: Anteil unveränderter Freigaben, Zeit zwischen Anfrage und Antwort | ✓ Sammelfreigabe nur für grün. Gelb und rot nur einzeln mit selbst geschriebener Zahl (getestet). ○ Hoher Anteil unveränderter Freigaben in kurzer Zeit → Stichprobe durch den Inhaber |
| **R11** | Missbrauch | **Unbefugte Freigabe** (falsche Person, falsche Rolle) | Bestellung ohne Verantwortung | `freigabe_protokoll.konto` und `rolle` | ✓ Senden nur mit IAM-Rolle Workflows Invoker. ✓ In der Inhaber-Phase nur die Rolle Inhaber, rot nie durch die Stellvertretung (getestet). ○ Die Rolle ist im Prototyp eine Angabe; im Betrieb an das Konto koppeln (je ein Konto pro Person) |
| **R12** | Kosten | **Überbestellung und Verderb** (H3) | Kapital gebunden, Ware entsorgt | S5 > 3 %, `menge_freigegeben` > `obergrenze` | ✓ Obergrenze 1 Wochen-Plan-Absatz, darüber nur der Inhaber mit Begründung (getestet). ✓ S5 als Hinweis. ✓ Reserve nach Störungsende zurück. ○ Obergrenze mit dem Inhaber festlegen |
| **R13** | Fehlentscheidung | **Bestellformel bestellt zu wenig**: IR-03 (Soll − Bestand − unterwegs) deckt nur die Lücke zur Reserve, nicht den Absatz bis zur nächsten Lieferung | Ohne S6 schlägt die Regel oft 0 vor (Rückfallmenge am 9. und 16.11. überall 0), obwohl 280 Snacks pro Woche verkauft werden; Ausverkauf | Vergleich mit `bestellt` in den Daten: Der Inhaber bestellt Absatz + Lücke (z. B. 26.10. Muesliriegel 88 statt 8); S1 | ○ **Vor jedem Einsatz mit dem Inhaber klären.** Im Prototyp gilt bewusst die Katalog-Formel, damit er mit dem MVP vergleichbar bleibt. Deshalb bleibt S2 auf Stufe 3 |
| R14 | Daten | Blick in die Zukunft (MVP: S4, S5 und S1 mit Daten nach dem Stichtag) | Signale, die am Montagmorgen niemand kennen kann | Test `test_s4_ohne_blick_in_die_zukunft` | ✓ Alle Fenster enden vor dem Stichtag |
| R15 | Betrieb | Lauf scheitert oder die Schranke schliesst | Kein Entwurf am Montag | Alarm Fehlschlag per E-Mail | ✓ Alarm seit SW11 angelegt und mit einem Fehllauf getestet (Stichtag ohne Zählung → Q06 → Mail). Rückfall: Bestellblatt von Hand (Formel im Alarmtext) |
| R16 | Betrieb | Niemand gibt frei | Es wird nichts bestellt | `ESKALATION_KEINE_FREIGABE` | ✓ Bewusst kein Automatismus («lieber nichts als falsch»); E-Mail an den Inhaber; protokolliert |
| R17 | Kosten | Kosten in Google Cloud | Education-Guthaben schrumpft | Abrechnung im Projekt | ✓ Kleine Tabellen, `list_rows` statt Abfragen, 1 Lauf pro Woche. ✓ Seit SW11 Kostenbremse in dbt: höchstens 1 GB pro Abfrage (BigQuery rechnet pro Tabelle mindestens 10 MB ab). Erwartung: Rappen pro Lauf (nicht gemessen) |

## 2 Rückfalloptionen auf einen Blick

| Ebene | Wenn … | dann … |
|---|---|---|
| Daten | Bestand fehlt, Tag fehlt, Lieferschein fehlt | Vorwochenwert «geschätzt», «fehlt» bzw. «unbekannt», Ampel gelb, nie stillschweigend 0 |
| Regel | Entscheidregel «nicht erfüllt» | S6 gesperrt, **S4** gilt (Brief) |
| Ladder | Fehlalarm, Verderb > 3 %, Mengen oft geändert | eine Stufe zurück (01-automation-decision.md) |
| Freigabe | Inhaber nicht erreichbar | Stellvertretung; rote Zeilen nur in der Rückfallmenge |
| Freigabe | Niemand antwortet | nichts bestellen, Inhaber anrufen |
| Technik | Lauf scheitert | Alarm; Bestellblatt von Hand wie vor dem Projekt |
| Gesamt | Projekt wird gestoppt | Ressourcen löschen (`prototyp/ANLEITUNG.md`), Erfassungslisten bleiben brauchbar |
