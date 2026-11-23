-- Stufe 1 · aufbereitet: Vorwarnungen des Lieferanten (IR-01). Eine Zeile pro Ankündigung.
-- Fehlt eines der Datumsfelder, scheitert die Umwandlung und der Lauf stoppt: Ohne Beginn und Ende
-- kann die Regel S6 nicht rechnen.

select
    cast(roh.angekuendigt_am as date)               as angekuendigt_am,
    roh.kanal,
    cast(roh.stoerung_von as date)                  as stoerung_von,
    cast(roh.stoerung_bis as date)                  as stoerung_bis,
    cast(roh.erwartete_menge_prozent as int64)      as erwartete_menge_prozent,
    cast(nullif(trim(roh.notiert_am), '') as date)  as notiert_am,
    roh.herkunft
from {{ source('roh', 'roh_vorwarnungen') }} as roh
where roh.lauf_id = '{{ var("lauf_id") }}'
