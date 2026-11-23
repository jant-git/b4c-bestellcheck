-- Stufe 2 · Sternschema: Fakt Verderb. Körnung: Produkt × Woche (Grundlage für S5).
-- Keine Regel nötig; die Tabelle steht hier, damit alle Fakten in derselben Stufe liegen.

select
    woche_ab,
    produkt,
    entsorgt_stueck,
    grund,
    herkunft
from {{ ref('stg_verderb') }}
