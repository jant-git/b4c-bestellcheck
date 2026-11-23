"""Regeln des Bestell-Checks B4C: eine Datei, die lokal (Tests) und im Cloud-Run-Job dieselbe ist.

Leitfrage: «Wie viel soll ich pro Snack bestellen, und gibt es ein Warnsignal?»
  Q-01 (Rang 1) Reicht die Ware bis Störungsende?  -> Reichweite (IR-02), S6 Reserve erhöhen = Warnsignal
  Q-02 (Rang 2) Wie viel fehlt bis zum Soll?       -> Bestellmenge (IR-03, S2), S3 offene Bestellungen

Grundsatz: Die Regeln rechnen und bereiten vor. Sie bestellen nie. Jede Menge braucht eine Freigabe
(Inhaber, sonst Stellvertretung), siehe freigabe_pruefen().

Alle Schwellen sind begründete Annahmen aus Mission Brief (SW06 A) und Anforderungskatalog (SW06 B),
nicht belegt, mit dem Inhaber zu bestätigen. Daten im Prototyp: SYNTHETISCH.
Datumswerte sind überall ISO-Strings 'YYYY-MM-DD'.
"""
import datetime as dt
import math

# ---------------------------------------------------------------- Parameter (Annahmen, mit Inhaber bestätigen)
PRODUKTE = {"Muesliriegel": 80, "Cookies": 70, "Chips": 70, "Nuesse": 60}  # Plan-Absatz/Woche, Modell v5, Summe 280
RESERVE_NORMAL = 0.75        # Wochen; Soll 210 Snacks
RESERVE_STOERUNG = 1.5       # Wochen bei Vorwarnung (S6); Soll 420 Snacks = Lieferzeit in der Störung
S1_UHRZEIT = "15:00"         # S1: leer vor 15 Uhr ...
S1_WOCHEN = 2                # ... in mind. 2 von 4 Wochen
S3_PUFFER_TAGE = 2           # S3: zugesagt + 2 Tage überschritten -> nachfragen, nicht neu bestellen
S4_FENSTER = 8               # S4: letzte 8 Lieferungen ...
S4_MIN_PROBLEME = 2          # ... davon mind. 2 zu spät oder unvollständig
VOLLSTAENDIG_AB = 0.9        # Katalog B1: unvollständig = weniger als 90 % der bestellten Menge
S5_QUOTE = 0.03              # S5: Verderb > 3 % des Plan-Absatzes pro Woche (= Widerlegung H3)
REGEL_MIN_FAELLE = 3         # Entscheidregel Brief: in 2 von 3 Fällen ...
REGEL_ANTEIL = 2 / 3
REGEL_MIN_VORLAUF_TAGE = 7   # ... mindestens 1 Woche vorher gewarnt
OBERGRENZE_WOCHEN = 1.0      # Annahme: eine Bestellung pro Produkt höchstens 1 Wochen-Plan-Absatz

GRUEN = "automatisch vorbereitet"
GELB = "Freigabe nötig"
ROT = "Eskalation"


def tag(s):
    return dt.date.fromisoformat(s)


def plus_tage(s, n):
    return (tag(s) + dt.timedelta(days=n)).isoformat()


# ---------------------------------------------------------------- Vorwarnung (IR-01) und Entscheidregel
def entscheidregel(vorwarnungen, stichtag):
    """Brief: S6 nur, wenn der Lieferant in 2 von 3 Fällen mind. 1 Woche vorher warnt, sonst S4.
    Gezählt werden nur Vorwarnungen, die am Stichtag schon bekannt sind."""
    bekannt = [w for w in vorwarnungen if w["angekuendigt_am"] <= stichtag]
    n = len(bekannt)
    rechtzeitig = sum(1 for w in bekannt if w["vorlauf_tage"] >= REGEL_MIN_VORLAUF_TAGE)
    if n < REGEL_MIN_FAELLE:
        status = "zu wenig Fälle"
    elif rechtzeitig / n >= REGEL_ANTEIL:
        status = "erfüllt"
    else:
        status = "nicht erfüllt"
    text = f"Entscheidregel: {status} ({rechtzeitig} von {n} Vorwarnungen mit ≥ {REGEL_MIN_VORLAUF_TAGE} Tagen Vorlauf, nötig 2 von 3)"
    return {"status": status, "faelle": n, "rechtzeitig": rechtzeitig, "text": text}


def relevante_vorwarnung(vorwarnungen, stichtag):
    """Eine Vorwarnung ist relevant, wenn sie am Stichtag bekannt ist und die Störung noch nicht vorbei ist.
    Kein Eintrag heisst «keine Vorwarnung bekannt», nicht «keine Störung» (Katalog IR-01)."""
    offen = [w for w in vorwarnungen if w["angekuendigt_am"] <= stichtag <= w["stoerung_bis"]]
    return min(offen, key=lambda w: w["stoerung_von"]) if offen else None


# ---------------------------------------------------------------- Signale
def s1_ausverkauf(strichliste, dim_datum, produkt, stichtag):
    """S1 (Q-03, nur Hinweis): Wochen mit Ausverkauf vor 15 Uhr in den 4 Wochen VOR dem Stichtag."""
    von = plus_tage(stichtag, -28)
    tage = [d for d in dim_datum if von <= d["datum"] < stichtag]
    woche = {d["datum"]: d["woche_ab"] for d in tage}
    fehlt = sum(1 for d in tage if d["strichliste_status"] == "fehlt")
    zeilen = [z for z in strichliste if z["produkt"] == produkt and z["datum"] in woche]
    wochen = {woche[z["datum"]] for z in zeilen if z["leer_um"] and z["leer_um"] < S1_UHRZEIT}
    nachfragen = sum(z["nachfragen_nach_leer"] for z in zeilen)
    return {"aktiv": len(wochen) >= S1_WOCHEN, "wochen": len(wochen), "nachfragen": nachfragen, "tage_fehlt": fehlt}


def s3_ueberfaellig(lieferungen, produkt, stichtag):
    """S3 (Q-02): Bestellung länger offen als zugesagt + 2 Tage? Dann nachfragen, nicht neu bestellen (IR-04)."""
    return [l["lieferschein"] for l in lieferungen
            if l["produkt"] == produkt
            and plus_tage(l["zugesagt_am"], S3_PUFFER_TAGE) < stichtag
            and (l["geliefert_am"] is None or l["geliefert_am"] > stichtag)]


def _angekuendigt(lieferschein, vorwarnungen):
    # Katalog B1: eine angekündigte Störung zählt nicht als «zu spät / unvollständig».
    return any(w["angekuendigt_am"] < lieferschein["zugesagt_am"]
               and w["stoerung_von"] <= lieferschein["zugesagt_am"] <= w["stoerung_bis"] for w in vorwarnungen)


def s4_lieferant(lieferungen, vorwarnungen, stichtag):
    """S4 (Rückfall zu S6): von den letzten 8 Lieferungen, die am Stichtag fällig waren, mind. 2 zu spät
    oder unvollständig, ohne Vorwarnung. Ein Wert pro Lieferant, nicht pro Produkt.
    Lieferungen nach dem Stichtag zählen nicht (die kennt am Montagmorgen niemand)."""
    ls = {}
    for l in lieferungen:
        if l["zugesagt_am"] >= stichtag:
            continue  # noch nicht fällig
        e = ls.setdefault(l["lieferschein"], {"zugesagt_am": l["zugesagt_am"], "zu_spaet": False,
                                               "unvollstaendig": False, "unbekannt": False})
        if l["geliefert_am"] is None:
            e["unbekannt"] = True  # IR-06: Lieferschein fehlt -> «unbekannt», nicht «pünktlich»
        elif l["geliefert_am"] > stichtag:
            e["zu_spaet"] = True  # am Stichtag fällig, aber noch nicht da
        else:
            e["zu_spaet"] |= l["geliefert_am"] > l["zugesagt_am"]
            e["unvollstaendig"] |= l["ist_stueck"] < VOLLSTAENDIG_AB * l["soll_stueck"]
    ausgenommen = [k for k, e in ls.items() if _angekuendigt(e, vorwarnungen)]
    bewertet = sorted((k for k in ls if k not in ausgenommen), key=lambda k: ls[k]["zugesagt_am"])[-S4_FENSTER:]
    probleme = sum(1 for k in bewertet if ls[k]["zu_spaet"] or ls[k]["unvollstaendig"])
    unbekannt = sum(1 for k in bewertet if ls[k]["unbekannt"])
    return {"aktiv": probleme >= S4_MIN_PROBLEME, "probleme": probleme, "bewertet": len(bewertet),
            "unbekannt": unbekannt, "ausgenommen": len(ausgenommen)}


def s5_verderb(verderb, produkt, stichtag):
    """S5 (Hinweis, H3): Verderb der letzten abgeschlossenen Woche > 3 % des Plan-Absatzes.
    Woche fehlt -> «fehlt», S5 wird nicht ausgelöst (IR-07)."""
    woche = plus_tage(stichtag, -7)
    z = [v for v in verderb if v["produkt"] == produkt and v["woche_ab"] == woche]
    if not z:
        return {"aktiv": False, "quote": None, "status": "fehlt"}
    quote = z[0]["entsorgt_stueck"] / PRODUKTE[produkt]
    return {"aktiv": quote > S5_QUOTE, "quote": round(quote, 3), "status": "erfasst"}


# ---------------------------------------------------------------- Bestellentwurf (Q-01 + Q-02)
def bestellentwurf(stern, stichtag):
    """Eine Zeile pro Produkt: Menge, Begründung, Ampel, Obergrenze, wer freigeben darf."""
    vw = stern["fakt_vorwarnung"]
    regel = entscheidregel(vw, stichtag)
    warnung = relevante_vorwarnung(vw, stichtag)
    s4 = s4_lieferant(stern["fakt_lieferung"], vw, stichtag)
    # S6 wird vorbereitet, solange die Entscheidregel ihn nicht ausschliesst. «nicht erfüllt» -> S4 gilt.
    s6 = warnung is not None and regel["status"] != "nicht erfüllt"
    reserve = RESERVE_STOERUNG if s6 else RESERVE_NORMAL

    entwurf = []
    for produkt, absatz in PRODUKTE.items():
        b = next((z for z in stern["fakt_bestand"] if z["produkt"] == produkt and z["datum"] == stichtag), None)
        if b is None:
            raise ValueError(f"Kein Bestand für {produkt} am {stichtag}: Qualitätsschranke hätte stoppen müssen")
        bestand, unterwegs = b["bestand"], b["unterwegs"]
        soll = math.ceil(absatz * reserve)
        menge = max(soll - bestand - unterwegs, 0)
        obergrenze = math.ceil(absatz * OBERGRENZE_WOCHEN)
        rueckfall = min(max(math.ceil(absatz * RESERVE_NORMAL) - bestand - unterwegs, 0), obergrenze)
        reichweite = round((bestand + unterwegs) / absatz, 2)
        s1 = s1_ausverkauf(stern["fakt_strichliste"], stern["dim_datum"], produkt, stichtag)
        s3 = s3_ueberfaellig(stern["fakt_lieferung"], produkt, stichtag)
        s5 = s5_verderb(stern["fakt_verderb"], produkt, stichtag)

        text = [f"Q-02: Soll {soll} ({absatz}/Wo. × {reserve} Wo.) − Bestand {bestand} − unterwegs {unterwegs} = {menge} Stück"]
        if warnung:
            reicht = reichweite >= RESERVE_STOERUNG
            text.append(f"Q-01: Reichweite {reichweite:.1f} Wo. {'≥' if reicht else '<'} Ziel {RESERVE_STOERUNG} → "
                        f"{'reicht' if reicht else 'reicht NICHT'} bis Störungsende {warnung['stoerung_bis']}")
            text.append(f"S6: Vorwarnung {warnung['vorwarnung_id']} ({warnung['kanal']}, {warnung['vorlauf_tage']} Tage Vorlauf, "
                        f"Störung {warnung['stoerung_von']}–{warnung['stoerung_bis']}, {warnung['erwartete_menge_prozent']} % Menge)")
            text.append(regel["text"] + (" → S6 vorbereitet, Inhaber entscheidet" if s6 else " → S6 gesperrt, S4 gilt"))
        else:
            reicht = None
            text.append(f"Q-01: keine Vorwarnung bekannt (heisst nicht «keine Störung»); Reichweite {reichweite:.1f} Wo.")

        ampel, gruende = GRUEN, []
        if s6:
            ampel = GELB; gruende.append("S6 erhöht das Soll")
        if b["bestand_status"] == "geschätzt":
            ampel = GELB; gruende.append("Bestand geschätzt (Vorwochenwert), bitte zählen")
        if s3:
            ampel = GELB; gruende.append(f"S3: {', '.join(s3)} überfällig, zuerst nachfragen, nicht neu bestellen")
        if s6 and warnung["vorlauf_tage"] < REGEL_MIN_VORLAUF_TAGE:
            ampel = ROT; gruende.append(f"Vorwarnung zu spät ({warnung['vorlauf_tage']} < {REGEL_MIN_VORLAUF_TAGE} Tage)")
        if menge > obergrenze:
            ampel = ROT; gruende.append(f"Menge {menge} über Obergrenze {obergrenze}")

        hinweise = []
        if s1["aktiv"]:
            hinweise.append(f"S1: {s1['wochen']} Wochen vor 15 Uhr leer, {s1['nachfragen']} Nachfragen → Soll prüfen (Q-03)")
        if s4["aktiv"]:
            hinweise.append(f"S4: {s4['probleme']} von {s4['bewertet']} Lieferungen problematisch → Reserve leicht erhöhen (Höhe offen)")
        if s5["aktiv"]:
            hinweise.append(f"S5: Verderb {s5['quote']:.0%} > 3 % → Reserve senken"
                            + (" (nicht während Störung)" if s6 else ""))
        if s1["tage_fehlt"]:
            hinweise.append(f"Strichliste fehlt an {s1['tage_fehlt']} Tag(en), «fehlt», nicht 0")

        freigabe = {GRUEN: "Inhaber oder Stellvertretung (Sammelfreigabe)",
                    GELB: "Inhaber einzeln; nach Frist Stellvertretung",
                    ROT: "nur Inhaber einzeln; sonst Rückfallmenge"}[ampel]
        entwurf.append({
            "stichtag": stichtag, "produkt": produkt, "bestand": bestand, "bestand_status": b["bestand_status"],
            "unterwegs": unterwegs, "plan_absatz_woche": absatz, "reserve_wochen": reserve, "soll": soll,
            "reichweite_wochen": reichweite, "reicht_bis_stoerungsende": reicht,
            "menge_vorschlag": menge, "menge_rueckfall": rueckfall, "obergrenze": obergrenze,
            "s1": s1["aktiv"], "s2": menge > 0, "s3": bool(s3), "s4": s4["aktiv"], "s5": s5["aktiv"], "s6": s6,
            "entscheidregel": regel["status"], "ampel": ampel, "ampel_grund": "; ".join(gruende) or "Regelfall",
            "freigabe_durch": freigabe, "begruendung": " | ".join(text + hinweise), "herkunft": "synthetisch",
        })
    return entwurf


# ---------------------------------------------------------------- Freigabe (menschlicher Schritt)
def freigabe_pruefen(entwurf, antwort, phase):
    """Prüft eine Freigabe-Antwort gegen Rolle, Phase, Ampel und Obergrenze. Gibt Protokollzeilen zurück.

    phase:   'inhaber' (erste Frist) | 'stellvertretung' (nach Frist) | 'keine_antwort' (beide Fristen verstrichen)
    antwort: {"rolle": "Inhaber"|"Stellvertretung", "entscheid": "freigeben"|"ablehnen",
              "einzeln": {"Chips": 38, ...}, "kommentar": "..."}
             Grüne Produkte gibt «freigeben» gesammelt frei. Gelbe und rote nur, wenn sie in «einzeln» stehen
             (gegen Freigabe aus Gewohnheit). Eine Menge in «einzeln» ersetzt den Vorschlag.
    """
    antwort = antwort or {}
    rolle = antwort.get("rolle")
    einzeln = antwort.get("einzeln") or {}
    kommentar = (antwort.get("kommentar") or "").strip()
    erlaubt = {"inhaber": {"Inhaber"}, "stellvertretung": {"Inhaber", "Stellvertretung"}}.get(phase, set())

    zeilen = []
    for e in entwurf:
        p, ampel = e["produkt"], e["ampel"]
        z = {"produkt": p, "ampel": ampel, "menge_vorschlag": e["menge_vorschlag"], "menge_freigegeben": None,
             "rolle": rolle, "phase": phase, "kommentar": kommentar, "herkunft": e["herkunft"]}
        if phase == "keine_antwort":
            z["status"] = "keine Freigabe bis Frist: nichts bestellt, Inhaber anrufen"
        elif rolle not in erlaubt:
            z["status"] = f"nicht befugt: Rolle {rolle!r} in Phase {phase}"
        elif antwort.get("entscheid") == "ablehnen":
            z["status"] = "abgelehnt"; z["menge_freigegeben"] = 0
        elif antwort.get("entscheid") != "freigeben":
            z["status"] = "ungültige Antwort (entscheid fehlt)"
        elif ampel == ROT and rolle != "Inhaber":
            z["status"] = "Rückfall: rote Zeile nur durch Inhaber, normale Reserve freigegeben"
            z["menge_freigegeben"] = e["menge_rueckfall"]
        elif ampel != GRUEN and p not in einzeln:
            z["status"] = "nicht freigegeben: Einzelbestätigung fehlt"
        else:
            menge = einzeln.get(p, e["menge_vorschlag"])
            if not isinstance(menge, int) or menge < 0:
                z["status"] = "ungültige Menge"
            elif menge > e["obergrenze"] and not (rolle == "Inhaber" and kommentar):
                z["status"] = f"nicht freigegeben: {menge} über Obergrenze {e['obergrenze']} (nur Inhaber mit Begründung)"
            else:
                z["menge_freigegeben"] = menge
                z["status"] = "freigegeben" if menge == e["menge_vorschlag"] else "geändert freigegeben"
        zeilen.append(z)
    return zeilen


def bestellmail_entwurf(protokoll, stichtag):
    """Nur ein Entwurf. Versand an den Lieferanten macht ein Mensch (Stufe: nicht automatisieren)."""
    pos = [f"- {z['produkt']}: {z['menge_freigegeben']} Stück" for z in protokoll if z["menge_freigegeben"]]
    if not pos:
        return None
    return ("ENTWURF, nicht versendet. Daten synthetisch.\n"
            f"Betreff: Bestellung B4C vom {stichtag}\n\nGuten Tag\n\nBitte liefern Sie:\n" + "\n".join(pos)
            + "\n\nBitte bestätigen Sie den Liefertag.\n\nFreundliche Grüsse\nB4C")
