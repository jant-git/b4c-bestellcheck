-- Q01 · Eindeutigkeit · FEHLER: Strichliste hat pro Tag und Produkt genau eine Zeile.
-- Schützt S1: Ein doppelter Tag würde Ausverkauf und Nachfrage doppelt zählen. Zeigt, dass R2 gewirkt hat.
{{ config(severity='error', meta={'id': 'Q01', 'dimension': 'Eindeutigkeit', 'regel': 'Strichliste: pro Tag und Produkt genau 1 Zeile'}) }}

select datum, produkt, count(*) as anzahl
from {{ ref('fakt_strichliste') }}
group by datum, produkt
having count(*) > 1
