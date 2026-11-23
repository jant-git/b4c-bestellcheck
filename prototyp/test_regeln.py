"""Wenige Tests der Regeln (nur Standardbibliothek). Aufruf aus prototyp/:  python3 -m unittest -v test_regeln

Jeder Test prüft eine Regel aus 02-konzept.md bzw. ein Risiko aus 03-risiken.md.
"""
import copy
import unittest

from lokal_lauf import bereinigen, lade_roh, regeln

STERN, _ = bereinigen.bereinigen(lade_roh())


def vorwarnung(id_, angekuendigt, von, bis):
    import datetime as dt
    vorlauf = (dt.date.fromisoformat(von) - dt.date.fromisoformat(angekuendigt)).days
    return {"vorwarnung_id": id_, "angekuendigt_am": angekuendigt, "kanal": "Mail", "stoerung_von": von,
            "stoerung_bis": bis, "erwartete_menge_prozent": 50, "notiert_am": angekuendigt, "vorlauf_tage": vorlauf,
            "herkunft": "synthetisch"}


class Regeln(unittest.TestCase):

    def test_s6_verdoppelt_soll_nur_vorbereitet(self):
        """S6: Soll 210 -> 420, aber nur vorbereitet (Ampel gelb, Inhaber entscheidet)."""
        e = regeln.bestellentwurf(STERN, "2026-11-09")
        self.assertEqual(sum(z["soll"] for z in e), 420)
        self.assertTrue(all(z["s6"] and z["ampel"] == regeln.GELB for z in e))

    def test_ohne_vorwarnung_normale_reserve_und_klartext(self):
        """Kein Eintrag heisst «keine Vorwarnung bekannt», nicht «keine Störung»."""
        e = regeln.bestellentwurf(STERN, "2026-10-26")
        self.assertEqual(sum(z["soll"] for z in e), 211)  # 60+53+53+45, aufgerundet
        self.assertIn("keine Vorwarnung bekannt", e[0]["begruendung"])
        self.assertTrue(all(z["ampel"] == regeln.GRUEN for z in e))

    def test_entscheidregel_mit_synthetischen_daten_nicht_entscheidbar(self):
        r = regeln.entscheidregel(STERN["fakt_vorwarnung"], "2026-11-16")
        self.assertEqual((r["status"], r["faelle"], r["rechtzeitig"]), ("zu wenig Fälle", 2, 1))

    def test_entscheidregel_nicht_erfuellt_sperrt_s6(self):
        """Brief: warnt der Lieferant nicht in 2 von 3 Fällen ≥ 1 Woche vorher, gilt S4 statt S6."""
        stern = copy.deepcopy(STERN)
        stern["fakt_vorwarnung"].append(vorwarnung("VW-03", "2026-11-06", "2026-11-09", "2026-11-12"))
        e = regeln.bestellentwurf(stern, "2026-11-16")
        self.assertEqual(e[0]["entscheidregel"], "nicht erfüllt")
        self.assertFalse(any(z["s6"] for z in e))
        self.assertEqual(sum(z["soll"] for z in e), 211)

    def test_zu_spaete_vorwarnung_eskaliert(self):
        stern = copy.deepcopy(STERN)
        stern["fakt_vorwarnung"] = [vorwarnung("VW-X", "2026-11-08", "2026-11-11", "2026-11-14")]
        e = regeln.bestellentwurf(stern, "2026-11-09")
        self.assertTrue(all(z["ampel"] == regeln.ROT for z in e))

    def test_geschaetzter_bestand_braucht_freigabe(self):
        """IR-03: keine Zählung -> Vorwochenwert, «geschätzt», nicht grün durchwinken."""
        cookies = next(z for z in regeln.bestellentwurf(STERN, "2026-11-02") if z["produkt"] == "Cookies")
        self.assertEqual((cookies["bestand"], cookies["bestand_status"], cookies["ampel"]), (25, "geschätzt", regeln.GELB))

    def test_s4_ohne_blick_in_die_zukunft(self):
        """MVP zählt Lieferungen nach dem Stichtag und angekündigte mit. Richtig: S4 ruhig am 16.11."""
        s4 = regeln.s4_lieferant(STERN["fakt_lieferung"], STERN["fakt_vorwarnung"], "2026-11-16")
        self.assertEqual((s4["aktiv"], s4["probleme"], s4["bewertet"], s4["ausgenommen"]), (False, 0, 5, 1))

    def test_obergrenze_eskaliert(self):
        stern = copy.deepcopy(STERN)
        for z in stern["fakt_bestand"]:
            if z["datum"] == "2026-11-16" and z["produkt"] == "Chips":
                z["bestand"], z["unterwegs"] = 0, 0
        chips = next(z for z in regeln.bestellentwurf(stern, "2026-11-16") if z["produkt"] == "Chips")
        self.assertEqual((chips["menge_vorschlag"], chips["obergrenze"], chips["ampel"]), (105, 70, regeln.ROT))

    def test_freigabe_gegen_gewohnheit_und_unbefugte(self):
        e = regeln.bestellentwurf(STERN, "2026-11-16")  # alle gelb (S6)
        # «Durchklicken»: freigeben ohne Einzelbestätigung gibt gelbe Zeilen NICHT frei
        p = regeln.freigabe_pruefen(e, {"rolle": "Inhaber", "entscheid": "freigeben"}, "inhaber")
        self.assertTrue(all(z["menge_freigegeben"] is None for z in p))
        # Stellvertretung in der Inhaber-Phase: nicht befugt
        p = regeln.freigabe_pruefen(e, {"rolle": "Stellvertretung", "entscheid": "freigeben",
                                        "einzeln": {"Chips": 38}}, "inhaber")
        self.assertTrue(all(z["status"].startswith("nicht befugt") for z in p))
        # Über Obergrenze ohne Begründung: abgelehnt; mit Begründung durch Inhaber: freigegeben
        p = regeln.freigabe_pruefen(e, {"rolle": "Inhaber", "entscheid": "freigeben", "einzeln": {"Chips": 90}}, "inhaber")
        self.assertIn("über Obergrenze", next(z for z in p if z["produkt"] == "Chips")["status"])
        p = regeln.freigabe_pruefen(e, {"rolle": "Inhaber", "entscheid": "freigeben", "einzeln": {"Chips": 90},
                                        "kommentar": "Event am Samstag"}, "inhaber")
        self.assertEqual(next(z for z in p if z["produkt"] == "Chips")["menge_freigegeben"], 90)

    def test_alles_bleibt_synthetisch_markiert(self):
        e = regeln.bestellentwurf(STERN, "2026-11-16")
        p = regeln.freigabe_pruefen(e, None, "keine_antwort")
        self.assertTrue(all(z["herkunft"] == "synthetisch" for z in e + p))
        self.assertTrue(all(z["menge_freigegeben"] is None for z in p))


if __name__ == "__main__":
    unittest.main()
