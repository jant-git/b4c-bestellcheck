-- Q08 · Vollständigkeit · WARNUNG: Die Strichliste ist an jedem Öffnungstag geführt.
-- Ein fehlender Tag ist nach R3 als «fehlt» markiert, der Entwurf entsteht trotzdem und nennt ihn.
{{ config(severity='warn', meta={'id': 'Q08', 'dimension': 'Vollständigkeit', 'regel': 'Strichliste an jedem Öffnungstag geführt'}) }}

select datum, wochentag
from {{ ref('dim_datum') }}
where strichliste_status = 'fehlt'
