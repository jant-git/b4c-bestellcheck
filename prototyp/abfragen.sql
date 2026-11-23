-- Vorzeige-Abfragen für die Präsentation (BigQuery-Konsole, Projekt b4c-bestellcheck-hs26, Location europe-west6).
-- Nur eigene Tabellen, je wenige KB. DATEN SYNTHETISCH.

-- 1 Sternschema: Fakt Bestand mit den Dimensionen Produkt und Datum -> Reichweite (Q-01)
SELECT d.woche_ab, p.produkt, p.plan_absatz_woche, f.bestand, f.bestand_status, f.unterwegs,
       ROUND((f.bestand + f.unterwegs) / p.plan_absatz_woche, 2) AS reichweite_wochen
FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.fakt_bestand` f
JOIN `b4c-bestellcheck-hs26.b4c_bestellcheck.dim_produkt` p USING (produkt)
JOIN `b4c-bestellcheck-hs26.b4c_bestellcheck.dim_datum` d USING (datum)
ORDER BY d.woche_ab, p.produkt;

-- 2 Qualitätsschranke pro Lauf
SELECT lauf_id, ergebnis, COUNT(*) AS pruefungen
FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.qualitaet_lauf`
GROUP BY lauf_id, ergebnis ORDER BY lauf_id, ergebnis;

-- 3 Bestellentwurf (Stufe vorbereiten): Menge, Ampel, Obergrenze, Begründung
SELECT lauf_id, produkt, menge_vorschlag, ampel, obergrenze, reichweite_wochen, entscheidregel, begruendung
FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.bestellentwurf`
ORDER BY erstellt_um, produkt;

-- 4 Freigabeprotokoll (wer, wann, was): Lauf 1 ohne Antwort -> Eskalation, Lauf 2 Freigabe durch den Inhaber
--   Status beim Doppelpunkt geteilt, damit er in der Konsole ganz lesbar ist (Folge = was danach passiert).
SELECT SUBSTR(lauf_id, 1, 8) AS lauf, produkt, menge_vorschlag AS vorschlag, menge_freigegeben AS freigegeben,
       rolle, konto, FORMAT_TIMESTAMP('%d.%m. %H:%M', zeitpunkt, 'Europe/Zurich') AS um,
       SPLIT(status, ': ')[SAFE_OFFSET(0)] AS status, SPLIT(status, ': ')[SAFE_OFFSET(1)] AS folge
FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.freigabe_protokoll`
ORDER BY zeitpunkt, produkt;

-- 5 Bestellmail-Entwurf: wird nie versendet
SELECT lauf_id, versendet, text FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.bestellmail_entwurf`;

-- ============================================================ ab SW11: Data Engineering
-- 6 Automatisierte Prüfungen: Ergebnis von Q01–Q14 im neuesten Lauf (FEHLER stoppt, WARNUNG wird gemeldet)
SELECT SUBSTR(lauf_id, 1, 8) AS lauf, stichtag, pruefung, dimension, ergebnis, zeilen, regel
FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.qualitaet_lauf`
WHERE lauf_id = (SELECT lauf_id FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.qualitaet_lauf` ORDER BY zeitpunkt DESC LIMIT 1)
ORDER BY pruefung;

-- 7 Wiederholbarkeit: Jeder Lauf legt seine eigene Kopie der Rohdaten ab, nichts wird überschrieben
SELECT SUBSTR(lauf_id, 1, 8) AS lauf, FORMAT_TIMESTAMP('%d.%m. %H:%M', MIN(geladen_um), 'Europe/Zurich') AS geladen,
       tabelle, COUNT(*) AS zeilen
FROM (
  SELECT 'roh_strichliste' AS tabelle, lauf_id, geladen_um FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.roh_strichliste`
  UNION ALL SELECT 'roh_bestand_montag', lauf_id, geladen_um FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.roh_bestand_montag`
  UNION ALL SELECT 'roh_lieferungen', lauf_id, geladen_um FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.roh_lieferungen`
  UNION ALL SELECT 'roh_verderb', lauf_id, geladen_um FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.roh_verderb`
  UNION ALL SELECT 'roh_vorwarnungen', lauf_id, geladen_um FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.roh_vorwarnungen`
)
GROUP BY lauf_id, tabelle
ORDER BY MIN(geladen_um), tabelle;

-- 8 Wiederholbarkeit: Alle Läufe mit Stichtag 9.11. (SW10 mit Python, SW11 mit dbt) liefern denselben Entwurf.
--   Erwartung: pro Produkt «verschiedene_ergebnisse = 1».
SELECT produkt, COUNT(DISTINCT lauf_id) AS laeufe,
       COUNT(DISTINCT FORMAT('%d|%d|%s|%s', menge_vorschlag, menge_rueckfall, ampel, begruendung)) AS verschiedene_ergebnisse,
       ANY_VALUE(menge_vorschlag) AS menge, ANY_VALUE(ampel) AS ampel
FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.bestellentwurf`
WHERE stichtag = DATE '2026-11-09'
GROUP BY produkt
ORDER BY produkt;

-- 9 Transformation: wie viele Zeilen jede Bereinigungsregel R1–R5 im letzten Lauf betroffen hat
SELECT SUBSTR(lauf_id, 1, 8) AS lauf, tabelle, regel, betroffene_zeilen
FROM `b4c-bestellcheck-hs26.b4c_bestellcheck.meta_bereinigung`
ORDER BY tabelle, regel;
