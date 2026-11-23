-- Q12 · Vollständigkeit · WARNUNG · neu aus dem Anforderungskatalog, Akzeptanzkriterium IR-05:
-- Die Strichliste ist in den 4 Wochen vor dem Stichtag an mindestens 90 % der Öffnungstage geführt.
-- Darunter ist S1 (Ausverkauf in 2 von 4 Wochen) nicht verlässlich.
{{ config(severity='warn', meta={'id': 'Q12', 'dimension': 'Vollständigkeit', 'regel': 'IR-05: Strichliste an ≥ 90 % der Öffnungstage (4 Wochen vor Stichtag)'}) }}

with fenster as (
    select
        count(*)                                  as oeffnungstage,
        countif(strichliste_status = 'geführt')   as gefuehrt
    from {{ ref('dim_datum') }}
    where datum >= date_sub(date '{{ var("stichtag") }}', interval 28 day)
      and datum < date '{{ var("stichtag") }}'
)
select oeffnungstage, gefuehrt, round(gefuehrt / oeffnungstage, 3) as anteil
from fenster
where oeffnungstage > 0
  and gefuehrt < 0.9 * oeffnungstage
