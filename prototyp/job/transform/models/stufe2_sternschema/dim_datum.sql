-- Stufe 2 · Sternschema: Dimension Datum. Eine Zeile pro Öffnungstag (Montag bis Samstag).
-- R3: Ein Tag ohne Strichliste heisst «fehlt», nicht 0. Eine 0 würde «kein Ausverkauf» behaupten (IR-05).

with grenzen as (
    select min(datum) as von, max(datum) as bis
    from {{ ref('stg_strichliste') }}
),

tage as (
    select tag as datum
    from grenzen, unnest(generate_date_array(grenzen.von, grenzen.bis)) as tag
    where extract(dayofweek from tag) != 1  -- 1 = Sonntag, B4C ist dann zu
),

gefuehrt as (
    select distinct datum
    from {{ ref('stg_strichliste') }}
)

select
    tage.datum,
    ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'][offset(extract(dayofweek from tage.datum) - 1)]  as wochentag,
    date_trunc(tage.datum, week(monday))                                                      as woche_ab,
    if(gefuehrt.datum is null, 'fehlt', 'geführt')                                            as strichliste_status
from tage
left join gefuehrt
    on tage.datum = gefuehrt.datum
