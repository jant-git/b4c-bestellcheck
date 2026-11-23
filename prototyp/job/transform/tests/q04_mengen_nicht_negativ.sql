-- Q04 · Gültigkeit · FEHLER: Keine Menge ist negativ.
-- Schützt alle Rechnungen: Ein negativer Bestand würde die Bestellmenge künstlich erhöhen.
{{ config(severity='error', meta={'id': 'Q04', 'dimension': 'Gültigkeit', 'regel': 'Mengen nie negativ'}) }}

select 'fakt_bestand' as tabelle, produkt, datum from {{ ref('fakt_bestand') }}
where bestand < 0 or unterwegs < 0
union all
select 'fakt_lieferung', produkt, zugesagt_am from {{ ref('fakt_lieferung') }}
where ist_stueck < 0 or soll_stueck < 0
union all
select 'fakt_strichliste', produkt, datum from {{ ref('fakt_strichliste') }}
where nachfragen_nach_leer < 0
union all
select 'fakt_verderb', produkt, woche_ab from {{ ref('fakt_verderb') }}
where entsorgt_stueck < 0
