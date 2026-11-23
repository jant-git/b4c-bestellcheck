-- Q10 · Aktualität · WARNUNG: Eine Vorwarnung kommt mindestens 7 Tage vor Störungsbeginn.
-- Grundlage der Entscheidregel des Briefs (2 von 3 Fällen rechtzeitig). Zu spät = Ampel rot im Entwurf.
{{ config(severity='warn', meta={'id': 'Q10', 'dimension': 'Aktualität', 'regel': 'Vorwarnung ≥ 7 Tage vor Störungsbeginn (Entscheidregel)'}) }}

select vorwarnung_id, angekuendigt_am, stoerung_von, vorlauf_tage
from {{ ref('fakt_vorwarnung') }}
where vorlauf_tage < 7
