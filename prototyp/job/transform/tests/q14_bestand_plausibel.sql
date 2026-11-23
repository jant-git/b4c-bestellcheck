-- Q14 · Plausibilität · WARNUNG · neu: Der gezählte Bestand ist nicht höher als der Bestand der Vorwoche
-- plus die Ware, die seither geliefert wurde. Mehr kann nicht da sein. Sonst ist vermutlich falsch gezählt
-- oder ein Lieferschein fehlt.
{{ config(severity='warn', meta={'id': 'Q14', 'dimension': 'Plausibilität', 'regel': 'Bestand ≤ Bestand Vorwoche + seither geliefert'}) }}

with bestand as (
    select
        produkt,
        datum,
        bestand,
        bestand_status,
        lag(datum)   over (partition by produkt order by datum) as datum_vorher,
        lag(bestand) over (partition by produkt order by datum) as bestand_vorher
    from {{ ref('fakt_bestand') }}
)
select
    b.produkt,
    b.datum,
    b.bestand,
    b.bestand_vorher,
    coalesce(sum(l.ist_stueck), 0) as geliefert
from bestand as b
left join {{ ref('fakt_lieferung') }} as l
    on  l.produkt = b.produkt
    and l.geliefert_am >= b.datum_vorher
    and l.geliefert_am <  b.datum
where b.bestand_status = 'gezählt'
  and b.bestand_vorher is not null
group by b.produkt, b.datum, b.bestand, b.bestand_vorher
having b.bestand > b.bestand_vorher + coalesce(sum(l.ist_stueck), 0)
