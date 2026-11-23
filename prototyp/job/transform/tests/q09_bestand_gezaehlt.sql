-- Q09 · Vollständigkeit · WARNUNG: Der Bestand am Stichtag ist gezählt, nicht geschätzt.
-- Ein geschätzter Bestand (R4, Vorwochenwert) macht den Entwurf gelb: «bitte zählen».
{{ config(severity='warn', meta={'id': 'Q09', 'dimension': 'Vollständigkeit', 'regel': 'Bestand am Stichtag gezählt, nicht geschätzt'}) }}

select produkt, datum, bestand
from {{ ref('fakt_bestand') }}
where datum = date '{{ var("stichtag") }}'
  and bestand_status = 'geschätzt'
