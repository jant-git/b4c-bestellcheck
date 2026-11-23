-- Protokoll: wie viele Zeilen jede Bereinigungsregel in diesem Lauf betroffen hat (wie das
-- Lineage-Protokoll im MVP SW09). Ändert sich eine Zahl plötzlich stark, stimmt etwas mit der Erfassung nicht.

with roh_strichliste as (
    select * from {{ source('roh', 'roh_strichliste') }}
    where lauf_id = '{{ var("lauf_id") }}'
),

zaehlung as (
    select 'roh_strichliste' as tabelle, 'unverändert geladen (Rohdaten)' as regel, count(*) as betroffene_zeilen
    from roh_strichliste
    union all
    select 'roh_bestand_montag', 'unverändert geladen (Rohdaten)', count(*)
    from {{ source('roh', 'roh_bestand_montag') }} where lauf_id = '{{ var("lauf_id") }}'
    union all
    select 'roh_lieferungen', 'unverändert geladen (Rohdaten)', count(*)
    from {{ source('roh', 'roh_lieferungen') }} where lauf_id = '{{ var("lauf_id") }}'
    union all
    select 'roh_verderb', 'unverändert geladen (Rohdaten)', count(*)
    from {{ source('roh', 'roh_verderb') }} where lauf_id = '{{ var("lauf_id") }}'
    union all
    select 'roh_vorwarnungen', 'unverändert geladen (Rohdaten)', count(*)
    from {{ source('roh', 'roh_vorwarnungen') }} where lauf_id = '{{ var("lauf_id") }}'
    union all
    select 'stg_strichliste', 'R1 Produktname vereinheitlicht', countif(coalesce(p.produkt, trim(r.produkt)) != r.produkt)
    from roh_strichliste as r
    left join {{ ref('dim_produkt') }} as p on lower(trim(r.produkt)) = lower(p.produkt)
    union all
    select 'stg_strichliste', 'R2 Doppelte (datum, produkt) zusammengeführt',
           (select count(*) from roh_strichliste) - (select count(*) from {{ ref('stg_strichliste') }})
    union all
    select 'dim_datum', 'R3 Tag ohne Strichliste als «fehlt» markiert', countif(strichliste_status = 'fehlt')
    from {{ ref('dim_datum') }}
    union all
    select 'fakt_bestand', 'R4 Fehlende Zählung = Vorwochenwert, «geschätzt»', countif(bestand_status = 'geschätzt')
    from {{ ref('fakt_bestand') }}
    union all
    select 'fakt_lieferung', 'R5 Verspätung (Tage) und Vollständigkeit (≥ 90 %) abgeleitet', count(*)
    from {{ ref('fakt_lieferung') }}
)

select
    '{{ var("lauf_id") }}'  as lauf_id,
    current_timestamp()     as zeitpunkt,
    tabelle,
    regel,
    betroffene_zeilen
from zaehlung
