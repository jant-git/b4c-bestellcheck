-- Q07 · Herkunft · FEHLER: Jede Zeile ist als synthetisch gekennzeichnet.
-- Schützt vor einer Verwechslung: Echte und erfundene Daten dürfen nie unbemerkt gemischt werden (Risiko R09).
{{ config(severity='error', meta={'id': 'Q07', 'dimension': 'Herkunft', 'regel': 'Jede Zeile ist als synthetisch gekennzeichnet'}) }}

with alle as (
    select 'fakt_strichliste' as tabelle, herkunft from {{ ref('fakt_strichliste') }}
    union all select 'fakt_bestand', herkunft from {{ ref('fakt_bestand') }}
    union all select 'fakt_lieferung', herkunft from {{ ref('fakt_lieferung') }}
    union all select 'fakt_verderb', herkunft from {{ ref('fakt_verderb') }}
    union all select 'fakt_vorwarnung', herkunft from {{ ref('fakt_vorwarnung') }}
)
select tabelle, herkunft
from alle
where coalesce(herkunft, '') != 'synthetisch'
