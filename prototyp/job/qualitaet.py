"""Ergebnisse der dbt-Prüfungen -> Zeilen für die Tabelle qualitaet_lauf.

Die Prüfungen selbst stehen seit SW11 als SQL in transform/tests/ (Q01–Q14, je eine Datei).
dbt führt sie nach jedem Modell aus und schreibt das Ergebnis nach transform/target/run_results.json.
Diese Datei übersetzt das in die Sprache der Qualitätsschranke:

FEHLER  = bereinigte Daten verletzen eine Regel -> kein Bestellentwurf (Workflow-Schritt «schranke»)
WARNUNG = Mangel in den Rohdaten, nach Regel behandelt -> Entwurf ja, Ampel und Begründung zeigen es
"""
import json
from pathlib import Path

# dbt-Status -> Ergebnis in qualitaet_lauf. «fail» heisst: Prüfung mit Schwere error hat Zeilen gefunden.
ERGEBNIS = {"pass": "OK", "warn": "WARNUNG", "fail": "FEHLER", "error": "FEHLER", "skipped": "ÜBERSPRUNGEN"}


def aus_dbt(ordner):
    """transform/target -> Liste von {pruefung, dimension, regel, ergebnis, zeilen}."""
    ordner = Path(ordner)
    lauf_datei, manifest_datei = ordner / "run_results.json", ordner / "manifest.json"
    if not lauf_datei.exists():
        # dbt ist gar nicht bis zu den Prüfungen gekommen (z. B. keine Verbindung zu BigQuery).
        return [{"pruefung": "dbt", "dimension": "Transformation", "regel": "dbt ist gelaufen (run_results.json fehlt)",
                 "ergebnis": "FEHLER", "zeilen": 0}]
    ergebnisse = json.loads(lauf_datei.read_text(encoding="utf-8"))["results"]
    knoten = json.loads(manifest_datei.read_text(encoding="utf-8")).get("nodes", {}) if manifest_datei.exists() else {}

    zeilen = []
    for r in ergebnisse:
        uid = r["unique_id"]
        art = uid.split(".")[0]            # test, model, seed
        k = knoten.get(uid, {})
        if art == "test":
            # id, dimension und regel stehen im config(meta=...) am Anfang jeder Prüfdatei
            meta = (k.get("config") or {}).get("meta") or k.get("meta") or {}
            zeilen.append({"pruefung": meta.get("id", k.get("name", uid)), "dimension": meta.get("dimension"),
                           "regel": meta.get("regel"), "ergebnis": ERGEBNIS.get(r["status"], r["status"]),
                           "zeilen": int(r.get("failures") or 0)})
        elif r["status"] == "error":
            # Ein Modell konnte nicht gebaut werden (z. B. Text, der keine Zahl ist): das ist ebenfalls ein FEHLER.
            zeilen.append({"pruefung": k.get("name", uid), "dimension": "Transformation",
                           "regel": f"{art} gebaut: {(r.get('message') or '')[:300]}", "ergebnis": "FEHLER", "zeilen": 0})
    return sorted(zeilen, key=lambda z: z["pruefung"])
