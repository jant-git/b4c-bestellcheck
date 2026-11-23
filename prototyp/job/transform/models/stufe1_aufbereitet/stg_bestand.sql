-- Stufe 1 · aufbereitet: Bestandszählung am Montag (IR-03). Eine Zeile pro Montag und Produkt.
-- Ein leerer Bestand bleibt hier leer (NULL). Was dann gilt, entscheidet R4 in Stufe 2 (fakt_bestand).

select
    cast(roh.datum as date)                                as datum,
    coalesce(p.produkt, trim(roh.produkt))                 as produkt,          -- R1
    cast(nullif(trim(roh.bestand_gezaehlt), '') as int64)  as bestand_gezaehlt, -- leer = nicht gezählt
    cast(roh.unterwegs as int64)                           as unterwegs,
    cast(roh.soll as int64)                                as soll_erfasst,
    cast(roh.bestellt as int64)                            as bestellt,
    roh.erfasst_von,
    roh.herkunft
from {{ source('roh', 'roh_bestand_montag') }} as roh
left join {{ ref('dim_produkt') }} as p
    on lower(trim(roh.produkt)) = lower(p.produkt)
where roh.lauf_id = '{{ var("lauf_id") }}'
