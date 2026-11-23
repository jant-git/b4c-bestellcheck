-- Stufe 2 · Sternschema: Fakt Lieferung. Körnung: Lieferschein × Produkt (Grundlage für S3 und S4).
-- R5: Verspätung in Tagen und Vollständigkeit ableiten.

select
    lieferschein,
    bestellt_am,
    zugesagt_am,
    geliefert_am,
    produkt,
    soll_stueck,
    ist_stueck,
    -- NULL, wenn das Lieferdatum unbekannt ist: dann weiss man es nicht, statt «0 Tage zu spät» zu behaupten
    date_diff(geliefert_am, zugesagt_am, day)  as verspaetung_tage,
    -- Katalog B1: unvollständig heisst weniger als 90 % der bestellten Menge (VOLLSTAENDIG_AB in regeln.py)
    ist_stueck >= 0.9 * soll_stueck            as vollstaendig,
    herkunft
from {{ ref('stg_lieferungen') }}
