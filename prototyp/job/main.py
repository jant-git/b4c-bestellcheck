"""Cloud-Run-Job b4c-wochenlauf. Vier Modi, der Workflow b4c-bestellcheck ruft sie nacheinander auf:

  laden          CSVs aus dem Bucket -> Rohdaten-Kopie roh_* mit lauf_id (nur anhängen)        (Stufe: automatisieren)
  transformieren dbt: Rohdaten dieses Laufs -> stg_* (aufbereitet) -> dim_*/fakt_* (Sternschema),
                 danach Prüfungen Q01–Q14 -> qualitaet_lauf                                      (Stufe: automatisieren)
  entwurf        Signale S1–S6, Reichweite, Bestellmenge, Ampel, Obergrenze -> bestellentwurf   (Stufe: vorbereiten)
  freigabe       Antwort von Inhaber/Stellvertretung prüfen -> freigabe_protokoll, bestellmail_entwurf (Mensch entscheidet)

Seit SW11 macht dbt die Bereinigung R1–R5 und das Sternschema in SQL (Ordner transform/). Bis SW10 tat
das bereinigen.py in Python; die Datei bleibt nur für den lokalen Lauf ohne Cloud (lokal_lauf.py, Tests).
Der Job bestellt nie und schreibt nie an den Lieferanten. Daten: SYNTHETISCH.
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from google.cloud import bigquery, storage

import qualitaet
import regeln

DATASET = os.environ.get("DATASET", "b4c_bestellcheck")
LOCATION = os.environ.get("LOCATION", "europe-west6")
PREFIX = os.environ.get("PREFIX", "daten/")
DATEIEN = ["strichliste.csv", "bestand_montag.csv", "vorwarnungen.csv", "lieferungen.csv", "verderb.csv"]
TRANSFORM = Path(__file__).resolve().parent / "transform"   # dbt-Projekt
LAUF_ID_ERLAUBT = re.compile(r"^[A-Za-z0-9_-]{1,80}$")     # die lauf_id landet in SQL, darum nur harmlose Zeichen


def S(name, typ="STRING"):
    return bigquery.SchemaField(name, typ)


# Das Sternschema (dim_*, fakt_*) legt seit SW11 dbt an; Spalten und Typen stehen in transform/models/.
# Hier nur die Tabellen, die pro Lauf Zeilen anhängen (Historie, nichts wird überschrieben).
SCHEMA = {
    "qualitaet_lauf": [S("lauf_id"), S("zeitpunkt", "TIMESTAMP"), S("stichtag", "DATE"), S("pruefung"), S("dimension"),
                       S("regel"), S("ergebnis"), S("zeilen", "INT64")],
    "bestellentwurf":[S("lauf_id"), S("erstellt_um", "TIMESTAMP"), S("stichtag", "DATE"), S("produkt"), S("bestand", "INT64"),
                       S("bestand_status"), S("unterwegs", "INT64"), S("plan_absatz_woche", "INT64"),
                       S("reserve_wochen", "FLOAT64"), S("soll", "INT64"), S("reichweite_wochen", "FLOAT64"),
                       S("reicht_bis_stoerungsende", "BOOL"), S("menge_vorschlag", "INT64"), S("menge_rueckfall", "INT64"),
                       S("obergrenze", "INT64"), S("s1", "BOOL"), S("s2", "BOOL"), S("s3", "BOOL"), S("s4", "BOOL"),
                       S("s5", "BOOL"), S("s6", "BOOL"), S("entscheidregel"), S("ampel"), S("ampel_grund"),
                       S("freigabe_durch"), S("begruendung"), S("herkunft")],
    "freigabe_anfrage": [S("lauf_id"), S("phase"), S("rolle_erwartet"), S("callback_url"), S("frist", "TIMESTAMP"),
                         S("erstellt_um", "TIMESTAMP")],
    "freigabe_protokoll": [S("lauf_id"), S("zeitpunkt", "TIMESTAMP"), S("stichtag", "DATE"), S("produkt"), S("ampel"),
                           S("menge_vorschlag", "INT64"), S("menge_freigegeben", "INT64"), S("status"), S("rolle"),
                           S("konto"), S("phase"), S("kommentar"), S("herkunft")],
    "bestellmail_entwurf": [S("lauf_id"), S("erstellt_um", "TIMESTAMP"), S("text"), S("versendet", "BOOL")],
}
STERN = ["dim_produkt", "dim_datum", "fakt_strichliste", "fakt_bestand", "fakt_lieferung", "fakt_verderb", "fakt_vorwarnung"]
ANHAENGEN = ["qualitaet_lauf", "bestellentwurf", "freigabe_anfrage", "freigabe_protokoll", "bestellmail_entwurf"]


def log(ereignis, **felder):
    # Eine JSON-Zeile = ein strukturierter Eintrag in Cloud Logging (jsonPayload).
    print(json.dumps({"severity": "INFO", "message": ereignis, "b4c_job": ereignis, **felder},
                     ensure_ascii=False, default=str), flush=True)


def jetzt():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def schreiben(bq, tabelle, zeilen, ersetzen, schema=None):
    cfg = bigquery.LoadJobConfig(
        schema=schema or SCHEMA.get(tabelle) or [S(k) for k in zeilen[0]],
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE if ersetzen else bigquery.WriteDisposition.WRITE_APPEND)
    bq.load_table_from_json(zeilen, f"{bq.project}.{DATASET}.{tabelle}", job_config=cfg, location=LOCATION).result()


def als_text(wert):
    return wert.isoformat() if isinstance(wert, (dt.date, dt.datetime)) else wert


def lesen(bq, tabelle):
    # list_rows liest die Tabelle ohne Abfrage, kostet also keine verarbeiteten Bytes.
    return [{k: als_text(v) for k, v in r.items()} for r in bq.list_rows(f"{bq.project}.{DATASET}.{tabelle}")]


def laden(bq, lauf, stichtag):
    """Rohdaten ablegen: jede CSV unverändert (alles Text) als Kopie dieses Laufs anhängen, nie überschreiben.
    So lässt sich zu jedem Bestellentwurf zeigen, aus welchen Daten er gerechnet wurde."""
    bucket = storage.Client(project=bq.project).bucket(os.environ["BUCKET"])
    zeit, anzahl = jetzt(), {}
    for datei in DATEIEN:
        leser = csv.DictReader(io.StringIO(bucket.blob(PREFIX + datei).download_as_text(encoding="utf-8")))
        zeilen = [{**z, "lauf_id": lauf, "geladen_um": zeit} for z in leser]
        tabelle = "roh_" + datei.removesuffix(".csv")
        schema = [S(spalte) for spalte in leser.fieldnames] + [S("lauf_id"), S("geladen_um", "TIMESTAMP")]
        if zeilen:  # leere Liste: nichts anhängen; fehlt dann z. B. der Bestand, stoppt Q06 den Lauf
            schreiben(bq, tabelle, zeilen, ersetzen=False, schema=schema)
        anzahl[tabelle] = len(zeilen)
    for tabelle in ANHAENGEN:
        bq.create_table(bigquery.Table(f"{bq.project}.{DATASET}.{tabelle}", schema=SCHEMA[tabelle]), exists_ok=True)
    log("GELADEN", lauf_id=lauf, stichtag=stichtag, zeilen=anzahl)


def transformieren(bq, lauf, stichtag):
    """dbt baut aus den Rohdaten dieses Laufs Stufe 1 (stg_*) und Stufe 2 (Sternschema) und prüft Q01–Q14.
    Das Ergebnis jeder Prüfung landet in qualitaet_lauf. Ein FEHLER beendet den Job mit Fehler."""
    dt.date.fromisoformat(stichtag)  # nur ein gültiges Datum, denn es landet in SQL
    if not LAUF_ID_ERLAUBT.match(lauf):
        raise ValueError(f"lauf_id mit unerlaubten Zeichen: {lauf!r}")
    befehl = ["dbt", "build", "--profiles-dir", ".", "--target", "prod",
              "--vars", json.dumps({"lauf_id": lauf, "stichtag": stichtag})]
    # dbt schreibt Modell für Modell und Prüfung für Prüfung ins Log (Cloud Logging).
    umgebung = {**os.environ, "DBT_PROJECT": bq.project, "DBT_SEND_ANONYMOUS_USAGE_STATS": "false"}
    ergebnis = subprocess.run(befehl, cwd=TRANSFORM, env=umgebung)
    pruefungen = qualitaet.aus_dbt(TRANSFORM / "target")
    schreiben(bq, "qualitaet_lauf", [{"lauf_id": lauf, "zeitpunkt": jetzt(), "stichtag": stichtag, **p} for p in pruefungen], False)
    log("TRANSFORMIERT", lauf_id=lauf, stichtag=stichtag, dbt_exitcode=ergebnis.returncode,
        fehler=[p["pruefung"] for p in pruefungen if p["ergebnis"] == "FEHLER"],
        warnungen=[p["pruefung"] for p in pruefungen if p["ergebnis"] == "WARNUNG"])
    if ergebnis.returncode != 0:
        sys.exit(ergebnis.returncode)  # Job scheitert -> Workflow nennt in der Schranke die Prüfung -> Alarm-Mail


def entwurf(bq, lauf, stichtag):
    stern = {t: lesen(bq, t) for t in STERN}
    zeilen = regeln.bestellentwurf(stern, stichtag)
    zeit = jetzt()
    schreiben(bq, "bestellentwurf", [{"lauf_id": lauf, "erstellt_um": zeit, **z} for z in zeilen], False)
    for z in zeilen:
        log("ENTWURF", lauf_id=lauf, produkt=z["produkt"], menge=z["menge_vorschlag"], ampel=z["ampel"], grund=z["ampel_grund"])


def freigabe(bq, lauf, stichtag, phase, antwort_text):
    cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("lauf", "STRING", lauf)])
    sql = f"SELECT * FROM `{bq.project}.{DATASET}.bestellentwurf` WHERE lauf_id = @lauf ORDER BY produkt"
    entwurf_zeilen = [{k: als_text(v) for k, v in r.items()} for r in bq.query(sql, job_config=cfg, location=LOCATION).result()]
    antwort = json.loads(antwort_text) if antwort_text else {}
    protokoll = regeln.freigabe_pruefen(entwurf_zeilen, antwort, phase)
    zeit = jetzt()
    schreiben(bq, "freigabe_protokoll", [{"lauf_id": lauf, "zeitpunkt": zeit, "stichtag": stichtag,
                                          "konto": antwort.get("konto"), **z} for z in protokoll], False)
    mail = regeln.bestellmail_entwurf(protokoll, stichtag)
    if mail:
        schreiben(bq, "bestellmail_entwurf", [{"lauf_id": lauf, "erstellt_um": zeit, "text": mail, "versendet": False}], False)
    for z in protokoll:
        log("FREIGABE_VERBUCHT", lauf_id=lauf, produkt=z["produkt"], status=z["status"], menge=z["menge_freigegeben"],
            rolle=z["rolle"], phase=phase)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("modus", choices=["laden", "transformieren", "entwurf", "freigabe"])
    a.add_argument("--lauf", default="manuell-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    a.add_argument("--stichtag", default=os.environ.get("STICHTAG", "2026-11-16"))
    a.add_argument("--phase", default="inhaber")
    a.add_argument("--antwort", default="")
    args = a.parse_args()
    bq = bigquery.Client()
    if args.modus == "laden":
        laden(bq, args.lauf, args.stichtag)
    elif args.modus == "transformieren":
        transformieren(bq, args.lauf, args.stichtag)
    elif args.modus == "entwurf":
        entwurf(bq, args.lauf, args.stichtag)
    else:
        freigabe(bq, args.lauf, args.stichtag, args.phase, args.antwort)


if __name__ == "__main__":
    main()
