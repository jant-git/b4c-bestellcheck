-- Q05 · Konsistenz · FEHLER: Eine Lieferung ist nie vor ihrer Bestellung zugesagt.
-- Schützt S3 und S4: Ein vertauschtes Datum ergäbe eine falsche Verspätung.
{{ config(severity='error', meta={'id': 'Q05', 'dimension': 'Konsistenz', 'regel': 'Lieferung: bestellt ≤ zugesagt'}) }}

select lieferschein, produkt, bestellt_am, zugesagt_am
from {{ ref('fakt_lieferung') }}
where bestellt_am > zugesagt_am
