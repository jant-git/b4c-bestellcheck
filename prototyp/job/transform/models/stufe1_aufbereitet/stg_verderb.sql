-- Stufe 1 · aufbereitet: Verderb pro Woche und Produkt (IR-07).

select
    cast(roh.woche_ab as date)               as woche_ab,
    coalesce(p.produkt, trim(roh.produkt))   as produkt,  -- R1
    cast(roh.entsorgt_stueck as int64)       as entsorgt_stueck,
    nullif(trim(roh.grund), '')              as grund,
    roh.herkunft
from {{ source('roh', 'roh_verderb') }} as roh
left join {{ ref('dim_produkt') }} as p
    on lower(trim(roh.produkt)) = lower(p.produkt)
where roh.lauf_id = '{{ var("lauf_id") }}'
