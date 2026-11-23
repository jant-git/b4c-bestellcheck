-- Q02 · Eindeutigkeit · FEHLER: Bestand hat pro Montag und Produkt genau eine Zeile.
-- Schützt Q-02: Zwei Bestände für denselben Montag ergäben zwei verschiedene Bestellmengen.
{{ config(severity='error', meta={'id': 'Q02', 'dimension': 'Eindeutigkeit', 'regel': 'Bestand: pro Montag und Produkt genau 1 Zeile'}) }}

select datum, produkt, count(*) as anzahl
from {{ ref('fakt_bestand') }}
group by datum, produkt
having count(*) > 1
