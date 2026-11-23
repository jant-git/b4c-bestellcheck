-- Q06 · Vollständigkeit · FEHLER: Für jedes Produkt gibt es am Stichtag einen Bestand.
-- Schützt Q-02: Ohne Bestand am Montag gibt es keine Bestellmenge. Dann lieber kein Entwurf und ein Alarm
-- (Rückfall: Bestellblatt von Hand) als eine Zahl aus alten Daten.
{{ config(severity='error', meta={'id': 'Q06', 'dimension': 'Vollständigkeit', 'regel': 'Bestand am Stichtag für jedes Produkt vorhanden'}) }}

select p.produkt
from {{ ref('dim_produkt') }} as p
where not exists (
    select 1
    from {{ ref('fakt_bestand') }} as b
    where b.produkt = p.produkt
      and b.datum = date '{{ var("stichtag") }}'
)
