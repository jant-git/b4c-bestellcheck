# 01 · Automation Decision: Bestellen bei Lieferstörungen (B4C)

> **Leitfrage:** «Wie viel soll ich pro Snack bestellen, und gibt es ein Warnsignal?»
> Daten im Prototyp: **synthetisch** (MVP SW09, Startwert 8). Belegt ist der Ablauf, nicht der Nutzen.

## 1 Entscheidung, priorisiert

| Rang | Frage (Mission Brief) | Entscheidung · Rolle | Antwort des Systems jeden Montag |
|---|---|---|---|
| **1 · Q-01** | Reicht die Ware bis Störungsende? | **Reserve erhöhen (S6)** von 0.75 auf 1.5 Wochen, Soll 210 → 420 · Inhaber, sonst Stellvertretung | **Warnsignal:** Reichweite (Bestand + unterwegs) ÷ Absatz neben dem Ziel 1.5 Wochen, mit Vorwarnung, Vorlauf und Entscheidregel |
| **2 · Q-02** | Wie viel fehlt bis zum Soll, inkl. Ware unterwegs? | **Bestellmenge (S2)**, Nachfragen statt neu bestellen (S3) · Inhaber, Stellvertretung | **Menge** pro Produkt mit Begründung, Ampel, Obergrenze |

Q-01 kommt zuerst: Dort ist die Wirkung am grössten (im Modell 145 statt 0 verlorene Verkäufe), und nur dort kommt das Feedback zu spät. Q-03 (S1, Soll anpassen) und S5 (Verderb) erscheinen nur als Hinweis im Entwurf.

**Automation Decision (ein Satz):**
Der Bestell-Check **rechnet und warnt automatisch**, **bereitet** Reserve und Bestellmenge **vor** und **bestellt nie selbst**. Jede Menge gibt ein Mensch frei: der Inhaber, sonst die Stellvertretung.

**Warum nicht mehr Automatisierung:**
1. **Die Entscheidregel des Briefs ist nicht entscheidbar.** S6 gilt nur, wenn der Lieferant in 2 von 3 Fällen mindestens 1 Woche vorher warnt. Die Daten enthalten 2 Vorwarnungen, eine mit 14 Tagen und eine mit 1 Tag Vorlauf. Das ergibt «zu wenig Fälle». Das MVP wendet S6 trotzdem an, ohne die Regel zu prüfen.
2. **S6 verdoppelt das Soll.** Eine falsche oder gefälschte Vorwarnung erzeugt sofort Überbestand und Verderb (H3).
3. **Die Schwellen sind Annahmen** (2 von 4, 2 von 8, 3 %, Obergrenze), vom Inhaber noch nicht bestätigt.
4. **Die Daten sind synthetisch.** Ob die Regeln in der Praxis stimmen, ist nicht gezeigt.
5. **Die Bestellformel ist offen.** IR-03 (Soll − Bestand − unterwegs) deckt nur die Lücke zur Reserve, nicht den Absatz bis zur nächsten Lieferung (siehe 03-risiken.md, R13).

## 2 Automation Ladder: vier Stufen

| Stufe | Was das System tut | Was der Mensch tut | Im Prototyp |
|---|---|---|---|
| **1 Anzeigen** | zeigt Zahlen und Signale | entscheidet und handelt selbst | Spalten S1–S6, Reichweite in `bestellentwurf` |
| **2 Empfehlen** | schlägt eine Handlung vor, mit Begründung | entscheidet, führt selbst aus | Hinweise S1, S3, S4, S5 in `begruendung` |
| **3 Vorbereiten** | erstellt die fertige Handlung (Menge, Entwurf), wartet auf Freigabe | gibt frei, ändert oder lehnt ab; ohne Freigabe passiert nichts | `bestellentwurf` → Callback → `freigabe_protokoll` |
| **4 Automatisieren** | handelt selbst, informiert | kann stoppen | Laden, Prüfen, Rechnen, Hinweis-Mails |

## 3 Schritte auf der Ladder

| # | Schritt | Bezug | Stufe | Begründung | Bedingung für höher | Bedingung für Rückfall |
|---|---|---|---|---|---|---|
| 1 | Daten laden, bereinigen (R1–R5), Qualität prüfen | Basis | **4 Automatisieren** | Datenarbeit ohne fachliche Folge; die Schranke stoppt bei FEHLER | (schon oben) | FEHLER → Lauf stoppt, Alarm. Stellvertretung bestellt nach Bestellblatt von Hand |
| 2 | Signale S1–S6 und Reichweite berechnen und anzeigen | Q-01, Q-02 | **4 Automatisieren** (Ergebnis wird angezeigt) | Rechnen ohne Handlung; jeder Wert steht mit Begründung in BigQuery | – | Qualität FEHLER → nichts anzeigen statt Falsches anzeigen |
| 3 | Warnsignal «reicht nicht bis Störungsende» melden | **Q-01** | **4 Automatisieren** (Hinweis-Mail) | Eine Warnung bewirkt allein nichts | – | 2 Fehlalarme in 4 Wochen → nur noch im Entwurf, keine Mail (gegen Alarmmüdigkeit) |
| 4 | **Reserve erhöhen (S6)**, Soll × 2 | **Q-01** | **3 Vorbereiten**, Einzelfreigabe Inhaber; nach Frist Stellvertretung | Entscheidregel nicht entscheidbar; verdoppelt das Soll; Risiko falsche Vorwarnung | → **4** (Soll automatisch erhöhen, Bestellung bleibt bei 3), wenn: Entscheidregel über ≥ 3 echte Vorwarnungen **erfüllt**; IR-01-Akzeptanz erfüllt (jede Vorwarnung innert 1 Tag mit 4 Feldern); H1 im 4-Wochen-Test nicht widerlegt; Vorwarnung kommt aus geprüftem Kanal; Schwellen vom Inhaber bestätigt | → **2 Empfehlen**, wenn die Entscheidregel «nicht erfüllt» ist (dann gilt S4), wenn eine Vorwarnung falsch war oder wenn der Verderb über 3 % steigt (H3 widerlegt) |
| 5 | **Bestellmenge (S2)** bei normaler Reserve, Ampel grün | **Q-02** | **3 Vorbereiten**, Sammelfreigabe durch Inhaber oder Stellvertretung | IR-03: Die Stellvertretung soll ohne Rückfrage bestellen können; Formel noch offen | → **4** (Bestellung ohne Klick), wenn: 8 Wochen echte Daten; ≥ 90 % der Freigaben unverändert; Abweichung ≤ ± 5 Stück (IR-03); Formel und Obergrenze mit Inhaber bestätigt; Bestellkanal mit Bestätigung | → **Einzelfreigabe (gelb)** bei geschätztem Bestand oder S3. → **2**, wenn in 2 Wochen Mengen um mehr als 5 Stück geändert wurden |
| 6 | Menge über Obergrenze, Vorwarnung zu spät (rot) | Q-01, Q-02 | **3 Vorbereiten**, nur Inhaber; sonst Rückfallmenge (normale Reserve) | Grösste Folgen, seltene Fälle | nie | – |
| 7 | Nachfragen statt neu bestellen (S3) | Q-02 | **2 Empfehlen** (Ampel gelb) | Kontakt zum Lieferanten macht ein Mensch; offene Bestellungen nur im Wochenlauf geprüft | → **3** (Nachfrage-Entwurf), wenn offene Bestellungen täglich erfasst werden (IR-04) | – |
| 8 | Reserve dauerhaft leicht erhöhen (S4, Rückfall zu S6) | Q-01 | **2 Empfehlen** | Wie viel «leicht» ist, ist nicht festgelegt; die Erhöhung wirkt jede Woche | → **3**, wenn der Inhaber die Höhe festlegt und der 6-Monats-Rückblick (IR-06) vorliegt | → **1 Anzeigen**, wenn S4 4 Wochen lang aktiv ist, ohne dass jemand reagiert |
| 9 | Soll anpassen (S1), Reserve senken (S5) | Q-03 (nur Bezug) | **2 Empfehlen** | Nebenthema, alle 4 Wochen | – | Während einer Störung (S6) wird S5 nur angezeigt |
| 10 | Bestellung an den Lieferanten senden | Q-02 | **3 Vorbereiten** (nur Mail-Entwurf), **Versand durch einen Menschen** | Wirkt nach aussen, nicht zurückholbar, keine Schnittstelle | Bestellportal mit Bestätigung und Schritt 5 auf Stufe 4 | – |
| 11 | Lieferanten informieren, nachfragen | – | **1 Anzeigen** | Beziehung und Tonfall bleiben beim Menschen | – | – |
| 12 | Freigabe anfragen, eskalieren | – | **4 Automatisieren** | Nur Benachrichtigung, keine fachliche Folge | – | – |

## 4 Prüfung der vorläufigen Annahme

Die Annahme aus dem Auftrag (anzeigen automatisieren, S6/S2 vorbereiten, Bestellung nicht automatisieren) **ist bestätigt**, mit drei Präzisierungen:

- **Die Bestellmenge ist nicht eine Stufe, sondern eine Ampel.** Grün bekommt eine Sammelfreigabe. Gelb braucht eine Einzelfreigabe (bei S6, geschätztem Bestand oder S3), rot darf nur der Inhaber freigeben. So bleibt die Freigabe dort schnell, wo das Risiko klein ist.
- **S3 und S4 nur empfehlen, nicht vorbereiten.** Bei S3 ist der Lieferant im Spiel. Bei S4 fehlt die Höhe der Erhöhung.
- **Das Warnsignal selbst wird automatisch gemeldet.** Es löst nichts aus und muss früh ankommen. Dafür ist Q-01 da.

## 5 Abbildung im Prototyp

`prototyp/workflow.yaml`: `laden` → `schranke` (Stufe 4) → `entwurf` (Stufe 3) → `freigabe_anfragen` Inhaber → Frist → Stellvertretung → Frist → `eskalation_keine_freigabe` → `freigabe_verbuchen`.
Eine Bestellung an den Lieferanten verschickt das System nicht. In `bestellmail_entwurf` steht immer `versendet = false`.
