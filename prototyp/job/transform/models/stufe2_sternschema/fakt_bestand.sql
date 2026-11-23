-- Stufe 2 · Sternschema: Fakt Bestand. Körnung: Produkt × Montag (Grundlage für Q-01 Reichweite und Q-02 Menge).
-- R4: Fehlt die Zählung, gilt der Wert der Vorwoche, markiert «geschätzt» (Katalog IR-03).
-- Der Entwurf wird dann gelb («bitte zählen»), statt still mit einer falschen Zahl zu rechnen.

select
    datum,
    produkt,
    -- letzter gezählter Wert bis und mit diesem Montag; ist heute gezählt, ist es der heutige Wert
    last_value(bestand_gezaehlt ignore nulls) over (
        partition by produkt
        order by datum
        rows between unbounded preceding and current row
    )                                                       as bestand,
    if(bestand_gezaehlt is null, 'geschätzt', 'gezählt')    as bestand_status,
    unterwegs,
    soll_erfasst,
    bestellt,
    erfasst_von,
    herkunft
from {{ ref('stg_bestand') }}
