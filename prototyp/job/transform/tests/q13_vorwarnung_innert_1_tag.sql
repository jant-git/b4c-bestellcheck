-- Q13 · Aktualität · WARNUNG · neu aus dem Anforderungskatalog, Akzeptanzkriterium IR-01:
-- Jede Vorwarnung ist innert 1 Tag nach der Ankündigung notiert.
-- Eine spät notierte Vorwarnung kann eine Bestellung verpassen, obwohl der Lieferant rechtzeitig gewarnt hat.
{{ config(severity='warn', meta={'id': 'Q13', 'dimension': 'Aktualität', 'regel': 'IR-01: Vorwarnung innert 1 Tag notiert'}) }}

select vorwarnung_id, angekuendigt_am, notiert_am
from {{ ref('fakt_vorwarnung') }}
where notiert_am is null
   or date_diff(notiert_am, angekuendigt_am, day) > 1
