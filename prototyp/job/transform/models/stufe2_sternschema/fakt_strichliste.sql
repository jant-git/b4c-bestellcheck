-- Stufe 2 · Sternschema: Fakt Strichliste. Körnung: Produkt × Öffnungstag (Grundlage für S1, Q-03).

select
    datum,
    produkt,
    leer_um,
    nachfragen_nach_leer,
    erfasst_von,
    herkunft,
    -- Ausverkauf vor 15 Uhr (Schwelle S1_UHRZEIT in regeln.py). Leer heisst nicht ausverkauft.
    (leer_um is not null and leer_um < '15:00')  as ausverkauft_vor_15
from {{ ref('stg_strichliste') }}
