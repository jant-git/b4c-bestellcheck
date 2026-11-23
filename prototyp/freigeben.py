"""Freigabe des Bestellentwurfs durch einen Menschen (Inhaber, sonst Stellvertretung). Daten: SYNTHETISCH.

    python3 freigeben.py --zeigen
    python3 freigeben.py --rolle Inhaber --freigeben --menge Muesliriegel=50 --menge Chips=38 [--kommentar "..."]
    python3 freigeben.py --rolle Inhaber --ablehnen --kommentar "Lieferant hat Störung abgesagt"

Grüne Zeilen gibt --freigeben gesammelt frei. Gelbe und rote Zeilen nur mit --menge Produkt=Zahl (einzeln, damit
niemand aus Gewohnheit durchklickt). Über der Obergrenze nur Inhaber mit --kommentar.
Wer die Antwort senden darf, regelt IAM (Rolle Workflows Invoker). Die Rolle im Text ist im Prototyp eine Angabe,
keine geprüfte Identität; das Konto (gcloud) wird mitprotokolliert.
Nutzt nur gcloud, bq (Google Cloud SDK) und die Python-Standardbibliothek.
"""
import argparse
import json
import subprocess
import sys
import urllib.request

DS = "b4c_bestellcheck"


def cli(*befehl):
    return subprocess.run(befehl, check=True, capture_output=True, text=True).stdout.strip()


def bq_json(sql, **params):
    args = ["bq", "query", "--use_legacy_sql=false", "--location=europe-west6", "--format=json", "--quiet"]
    args += [f"--parameter={k}:STRING:{v}" for k, v in params.items()]
    return json.loads(cli(*args, sql) or "[]")


def offene_anfrage(projekt):
    # Neueste Anfrage, deren Frist läuft und zu deren Lauf es noch kein Protokoll gibt (nur eigene Tabellen).
    zeilen = bq_json(f"""
        SELECT a.lauf_id, a.rolle_erwartet, a.callback_url, CAST(a.frist AS STRING) AS frist
        FROM `{projekt}.{DS}.freigabe_anfrage` a
        WHERE a.frist > CURRENT_TIMESTAMP()
          AND NOT EXISTS (SELECT 1 FROM `{projekt}.{DS}.freigabe_protokoll` p WHERE p.lauf_id = a.lauf_id)
        ORDER BY a.erstellt_um DESC LIMIT 1""")
    return zeilen[0] if zeilen else None


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--zeigen", action="store_true")
    a.add_argument("--rolle", choices=["Inhaber", "Stellvertretung"])
    g = a.add_mutually_exclusive_group()
    g.add_argument("--freigeben", action="store_true")
    g.add_argument("--ablehnen", action="store_true")
    a.add_argument("--menge", action="append", default=[], metavar="PRODUKT=ZAHL")
    a.add_argument("--kommentar", default="")
    args = a.parse_args()

    projekt = cli("gcloud", "config", "get-value", "project")
    anfrage = offene_anfrage(projekt)
    if not anfrage:
        sys.exit("Keine offene Freigabe-Anfrage (Frist abgelaufen oder schon beantwortet).")
    print(f"Lauf {anfrage['lauf_id']} · erwartet: {anfrage['rolle_erwartet']} · Frist bis {anfrage['frist']} UTC · DATEN SYNTHETISCH\n")
    for z in bq_json(f"""SELECT produkt, ampel, menge_vorschlag, menge_rueckfall, obergrenze, freigabe_durch, begruendung
                         FROM `{projekt}.{DS}.bestellentwurf` WHERE lauf_id = @lauf ORDER BY produkt""",
                     lauf=anfrage["lauf_id"]):
        print(f"{z['produkt']:<13} {z['menge_vorschlag']:>4} Stück  [{z['ampel']}]  Obergrenze {z['obergrenze']}, "
              f"Rückfall {z['menge_rueckfall']} · {z['freigabe_durch']}\n{'':<13} {z['begruendung']}\n")
    if args.zeigen:
        return
    if not args.rolle or not (args.freigeben or args.ablehnen):
        sys.exit("Bitte --rolle und --freigeben oder --ablehnen angeben (oder --zeigen).")

    einzeln = {}
    for m in args.menge:
        produkt, _, zahl = m.partition("=")
        einzeln[produkt.strip()] = int(zahl)
    antwort = {"rolle": args.rolle, "entscheid": "freigeben" if args.freigeben else "ablehnen", "einzeln": einzeln,
               "kommentar": args.kommentar, "konto": cli("gcloud", "config", "get-value", "account")}

    token = cli("gcloud", "auth", "print-access-token")
    req = urllib.request.Request(anfrage["callback_url"], data=json.dumps(antwort).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        print(f"Antwort gesendet (HTTP {r.status}). Der Workflow prüft sie und schreibt freigabe_protokoll.")


if __name__ == "__main__":
    main()
