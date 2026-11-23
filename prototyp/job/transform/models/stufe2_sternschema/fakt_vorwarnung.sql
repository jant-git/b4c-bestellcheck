-- Stufe 2 · Sternschema: Fakt Vorwarnung. Körnung: eine Ankündigung des Lieferanten (Grundlage für S6
-- und die Entscheidregel des Briefs: in 2 von 3 Fällen mindestens 7 Tage Vorlauf).

select
    -- Nummer in der Reihenfolge der Ankündigung: VW-01, VW-02, ...
    format('VW-%02d', row_number() over (order by angekuendigt_am, stoerung_von))  as vorwarnung_id,
    angekuendigt_am,
    kanal,
    stoerung_von,
    stoerung_bis,
    erwartete_menge_prozent,
    notiert_am,
    date_diff(stoerung_von, angekuendigt_am, day)                                  as vorlauf_tage,
    herkunft
from {{ ref('stg_vorwarnungen') }}
