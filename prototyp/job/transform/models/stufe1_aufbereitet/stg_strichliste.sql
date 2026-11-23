-- Stufe 1 · aufbereitet: Strichliste der Theke (IR-05). Eine Zeile pro Tag und Produkt.
-- Liest nur die Rohdaten-Kopie dieses Laufs (lauf_id). So rechnet jeder Lauf genau mit den Daten,
-- die er selbst geladen hat.

with roh as (
    select *
    from {{ source('roh', 'roh_strichliste') }}
    where lauf_id = '{{ var("lauf_id") }}'
),

-- R1: Produktname auf die Produktliste abbilden, z. B. 'cookies ' -> 'Cookies'. Sonst zählt es als 5. Produkt.
-- Unbekannte Namen bleiben stehen; Prüfung Q03 stoppt dann den Lauf.
benannt as (
    select
        cast(roh.datum as date)                    as datum,
        coalesce(p.produkt, trim(roh.produkt))     as produkt,
        -- Uhrzeit bleibt Text 'HH:MM' (leer = nicht ausverkauft), damit der Vergleich mit '15:00' in regeln.py gleich bleibt.
        nullif(trim(roh.leer_um), '')              as leer_um,
        cast(roh.nachfragen_nach_leer as int64)    as nachfragen_nach_leer,
        roh.erfasst_von,
        roh.herkunft
    from roh
    left join {{ ref('dim_produkt') }} as p
        on lower(trim(roh.produkt)) = lower(p.produkt)
)

-- R2: Nach R1 steht ein Tag doppelt da (Cookies am 3.11.). Zusammenführen mit dem frühesten Leer-Zeitpunkt
-- und der höchsten Nachfragezahl: Die Theke notiert einen Ausverkauf aktiv, der Eintrag gilt also.
select
    datum,
    produkt,
    min(leer_um)               as leer_um,
    max(nachfragen_nach_leer)  as nachfragen_nach_leer,
    min(erfasst_von)           as erfasst_von,
    min(herkunft)              as herkunft
from benannt
group by datum, produkt
