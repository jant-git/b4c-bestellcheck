-- Stufe 1 · aufbereitet: Lieferscheine (IR-04, IR-06). Eine Zeile pro Lieferschein und Produkt.

select
    roh.lieferschein,
    cast(roh.bestellt_am as date)                     as bestellt_am,
    cast(roh.zugesagt_am as date)                     as zugesagt_am,
    -- Leer heisst «unbekannt», nicht «pünktlich» (IR-06). Darum NULL statt eines Datums.
    cast(nullif(trim(roh.geliefert_am), '') as date)  as geliefert_am,
    coalesce(p.produkt, trim(roh.produkt))            as produkt,  -- R1
    cast(roh.soll_stueck as int64)                    as soll_stueck,
    cast(roh.ist_stueck as int64)                     as ist_stueck,
    roh.herkunft
from {{ source('roh', 'roh_lieferungen') }} as roh
left join {{ ref('dim_produkt') }} as p
    on lower(trim(roh.produkt)) = lower(p.produkt)
where roh.lauf_id = '{{ var("lauf_id") }}'
