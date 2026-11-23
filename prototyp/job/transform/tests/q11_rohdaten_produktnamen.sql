-- Q11 · Gültigkeit · WARNUNG: In den Rohdaten der Strichliste stehen die Produktnamen genau wie in der Produktliste.
-- R1 korrigiert Abweichungen ('cookies' -> 'Cookies'). Die Warnung zeigt, dass bei der Erfassung etwas schiefging.
{{ config(severity='warn', meta={'id': 'Q11', 'dimension': 'Gültigkeit', 'regel': 'Rohdaten: Produktnamen exakt wie in der Produktliste'}) }}

select datum, produkt
from {{ source('roh', 'roh_strichliste') }}
where lauf_id = '{{ var("lauf_id") }}'
  and produkt not in (select produkt from {{ ref('dim_produkt') }})
