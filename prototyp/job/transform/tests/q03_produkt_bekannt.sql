-- Q03 · Gültigkeit · FEHLER: Jedes Produkt in den Fakten steht in der Produktliste (dim_produkt).
-- Schützt die Regeln: Ein unbekanntes Produkt (Tippfehler, den R1 nicht kennt) hätte keinen Plan-Absatz.
{{ config(severity='error', meta={'id': 'Q03', 'dimension': 'Gültigkeit', 'regel': 'Jedes Produkt der Fakten steht in dim_produkt'}) }}

with alle as (
    select 'fakt_strichliste' as tabelle, produkt from {{ ref('fakt_strichliste') }}
    union all
    select 'fakt_bestand', produkt from {{ ref('fakt_bestand') }}
    union all
    select 'fakt_lieferung', produkt from {{ ref('fakt_lieferung') }}
    union all
    select 'fakt_verderb', produkt from {{ ref('fakt_verderb') }}
)
select tabelle, produkt
from alle
where produkt not in (select produkt from {{ ref('dim_produkt') }})
