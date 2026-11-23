"""Lokaler Testlauf ohne Cloud: Regeln auf die synthetischen MVP-Daten anwenden und den Bestellentwurf zeigen.

Aufruf (aus kleinklasse-automation/prototyp/):
    python3 lokal_lauf.py                 # Stichtag 2026-11-16
    python3 lokal_lauf.py 2026-11-09      # Montag vor der Störung: S6 wird vorbereitet
Nur Standardbibliothek. Liest prototyp/daten/ (Kopie der synthetischen CSV aus dem MVP SW09).
"""
import csv
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "job"))
import bereinigen  # noqa: E402
import regeln  # noqa: E402

DATEN = HIER / "daten"  # Kopie der synthetischen CSV aus dem MVP SW09 (gen.py, Startwert 8)


def lade_roh(ordner=DATEN):
    roh = {}
    for datei in bereinigen.DATEIEN:
        with open(ordner / datei, newline="", encoding="utf-8") as f:
            roh[datei] = list(csv.DictReader(f))
    return roh


if __name__ == "__main__":
    stichtag = sys.argv[1] if len(sys.argv) > 1 else "2026-11-16"
    stern, _ = bereinigen.bereinigen(lade_roh())
    print(f"Bestellentwurf Stichtag {stichtag}  (DATEN SYNTHETISCH)\n")
    for e in regeln.bestellentwurf(stern, stichtag):
        print(f"{e['produkt']:<13} Menge {e['menge_vorschlag']:>3} (Rückfall {e['menge_rueckfall']:>3}, Obergrenze {e['obergrenze']:>3})"
              f"  Reichweite {e['reichweite_wochen']:.2f} Wo.  Ampel: {e['ampel']}  [{e['ampel_grund']}]")
        print(f"{'':<13} Freigabe: {e['freigabe_durch']}")
        print(f"{'':<13} {e['begruendung']}\n")
