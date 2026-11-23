"""Bereinigung R1–R5 und Sternschema, fachlich wie im MVP (B4C_SW09_Data_Product_MVP/pipeline.py), ohne pandas.

Eingabe: {dateiname: [ {spalte: str, ...}, ... ]}  (CSV unverändert, alle Werte Text)
Ausgabe: (stern, lineage) mit stern = {tabelle: [zeilen]} und lineage = [ {regel, tabelle, betroffene_zeilen} ]
Daten im Prototyp: SYNTHETISCH. Die Spalte herkunft wird unverändert durchgereicht.
"""
import datetime as dt
from regeln import PRODUKTE, S1_UHRZEIT

DATEIEN = ["strichliste.csv", "bestand_montag.csv", "vorwarnungen.csv", "lieferungen.csv", "verderb.csv"]


def produktname(s):
    """R1: 'cookies ' -> 'Cookies'. Unbekannte Namen bleiben stehen, die Qualitätsprüfung meldet sie."""
    s = s.strip()
    return next((p for p in PRODUKTE if p.lower() == s.lower()), s)


def leer(x):
    return x is None or str(x).strip() == ""


def bereinigen(roh):
    lineage = []

    def log(tabelle, regel, n):
        lineage.append({"tabelle": tabelle, "regel": regel, "betroffene_zeilen": int(n)})

    for datei in DATEIEN:
        log(datei, "unverändert geladen (Staging)", len(roh[datei]))

    # Strichliste: R1 Namen, R2 Doppelte zusammenführen (frühester Leer-Zeitpunkt, höchste Nachfragezahl)
    namen_geaendert, zusammen = 0, {}
    for z in roh["strichliste.csv"]:
        p = produktname(z["produkt"])
        namen_geaendert += p != z["produkt"]
        k = (z["datum"], p)
        neu = {"datum": z["datum"], "produkt": p, "leer_um": None if leer(z["leer_um"]) else z["leer_um"],
               "nachfragen_nach_leer": int(z["nachfragen_nach_leer"]), "erfasst_von": z["erfasst_von"],
               "herkunft": z["herkunft"]}
        if k in zusammen:
            alt = zusammen[k]
            zeiten = [t for t in (alt["leer_um"], neu["leer_um"]) if t]
            alt["leer_um"] = min(zeiten) if zeiten else None
            alt["nachfragen_nach_leer"] = max(alt["nachfragen_nach_leer"], neu["nachfragen_nach_leer"])
        else:
            zusammen[k] = neu
    strichliste = sorted(zusammen.values(), key=lambda z: (z["datum"], z["produkt"]))
    for z in strichliste:
        z["ausverkauft_vor_15"] = bool(z["leer_um"] and z["leer_um"] < S1_UHRZEIT)
    log("fakt_strichliste", "R1 Produktname vereinheitlicht", namen_geaendert)
    log("fakt_strichliste", "R2 Doppelte (datum, produkt) zusammengeführt", len(roh["strichliste.csv"]) - len(strichliste))

    # R3 Datumsliste Mo–Sa; Tag ohne Strichliste = «fehlt», nicht 0
    daten = sorted({z["datum"] for z in strichliste})
    von, bis = dt.date.fromisoformat(daten[0]), dt.date.fromisoformat(daten[-1])
    gefuehrt = set(daten)
    dim_datum = []
    d = von
    while d <= bis:
        if d.weekday() < 6:
            s = d.isoformat()
            dim_datum.append({"datum": s, "wochentag": ["Mo", "Di", "Mi", "Do", "Fr", "Sa"][d.weekday()],
                              "woche_ab": (d - dt.timedelta(days=d.weekday())).isoformat(),
                              "strichliste_status": "geführt" if s in gefuehrt else "fehlt"})
        d += dt.timedelta(days=1)
    log("dim_datum", "R3 Tag ohne Strichliste als «fehlt» markiert", sum(x["strichliste_status"] == "fehlt" for x in dim_datum))

    # R4 Bestand: fehlende Zählung = Vorwochenwert, Status «geschätzt»
    bestand, letzter = [], {}
    for z in sorted(roh["bestand_montag.csv"], key=lambda z: (produktname(z["produkt"]), z["datum"])):
        p = produktname(z["produkt"])
        geschaetzt = leer(z["bestand_gezaehlt"])
        wert = letzter.get(p) if geschaetzt else int(z["bestand_gezaehlt"])
        letzter[p] = wert
        bestand.append({"datum": z["datum"], "produkt": p, "bestand": wert,
                        "bestand_status": "geschätzt" if geschaetzt else "gezählt",
                        "unterwegs": int(z["unterwegs"]), "soll_erfasst": int(z["soll"]), "bestellt": int(z["bestellt"]),
                        "erfasst_von": z["erfasst_von"], "herkunft": z["herkunft"]})
    log("fakt_bestand", "R4 Fehlende Zählung = Vorwochenwert, «geschätzt»", sum(z["bestand_status"] == "geschätzt" for z in bestand))

    # R5 Lieferungen: Verspätung und Vollständigkeit; fehlendes Lieferdatum = unbekannt (None)
    lieferungen = []
    for z in roh["lieferungen.csv"]:
        geliefert = None if leer(z["geliefert_am"]) else z["geliefert_am"]
        soll, ist = int(z["soll_stueck"]), int(z["ist_stueck"])
        lieferungen.append({"lieferschein": z["lieferschein"], "bestellt_am": z["bestellt_am"], "zugesagt_am": z["zugesagt_am"],
                            "geliefert_am": geliefert, "produkt": produktname(z["produkt"]), "soll_stueck": soll,
                            "ist_stueck": ist,
                            "verspaetung_tage": None if geliefert is None else
                            (dt.date.fromisoformat(geliefert) - dt.date.fromisoformat(z["zugesagt_am"])).days,
                            "vollstaendig": ist >= 0.9 * soll, "herkunft": z["herkunft"]})
    log("fakt_lieferung", "R5 Verspätung (Tage) und Vollständigkeit (≥ 90 %) abgeleitet", len(lieferungen))

    verderb = [{"woche_ab": z["woche_ab"], "produkt": produktname(z["produkt"]), "entsorgt_stueck": int(z["entsorgt_stueck"]),
                "grund": None if leer(z["grund"]) else z["grund"], "herkunft": z["herkunft"]} for z in roh["verderb.csv"]]

    vorwarnungen = []
    for i, z in enumerate(sorted(roh["vorwarnungen.csv"], key=lambda z: z["angekuendigt_am"])):
        vorwarnungen.append({"vorwarnung_id": f"VW-{i + 1:02d}", "angekuendigt_am": z["angekuendigt_am"], "kanal": z["kanal"],
                             "stoerung_von": z["stoerung_von"], "stoerung_bis": z["stoerung_bis"],
                             "erwartete_menge_prozent": int(z["erwartete_menge_prozent"]), "notiert_am": z["notiert_am"],
                             "vorlauf_tage": (dt.date.fromisoformat(z["stoerung_von"]) - dt.date.fromisoformat(z["angekuendigt_am"])).days,
                             "herkunft": z["herkunft"]})

    dim_produkt = [{"produkt": p, "plan_absatz_woche": a, "herkunft": "Annahme Modell v5"} for p, a in PRODUKTE.items()]
    stern = {"dim_produkt": dim_produkt, "dim_datum": dim_datum, "fakt_strichliste": strichliste, "fakt_bestand": bestand,
             "fakt_lieferung": lieferungen, "fakt_verderb": verderb, "fakt_vorwarnung": vorwarnungen}
    return stern, lineage
