---
title: Prose Fingerprint
neverShowQueries: true
---

How my prose compares to the authors in the measured corpus, (measured as **z-scores**). Positive means you do *more* of something than the typical work; negative, less.

## Vocabulary Overlap

Jaccard overlap of vocabulary. Higher = more shared words.

```sql kinship
select
    da.name as author,
    fvo.jaccard
from warehouse.fact_vocab_overlap fvo
join warehouse.dim_author da
    on fvo.author_key_b = da.author_key
order by fvo.jaccard desc
```

<BarChart
    data={kinship}
    x=author
    y=jaccard
    swapXY=true
    yFmt=pct2
/>

## Stylometric Fingerprint

```sql comparison
select
    dm.display_name,
    dm.metric_name,
    case when da.is_self then 'You' else da.name end as who,
    avg(fsm.zscore) as zscore
from warehouse.fact_style_measurement fsm
join warehouse.dim_metric dm
    on fsm.metric_key = dm.metric_key
join warehouse.dim_author da
    on fsm.author_key = da.author_key
where dm.is_multivalue = false
    and dm.metric_name <> 'jaccard'
    and (da.is_self or da.name = '${inputs.author.value}')
group by dm.display_name, dm.metric_name, who
order by dm.metric_name, who
```

Each metric* as a z-score: how far above (+) or below (–) the corpus average you and the chosen author sit. 0 = average.

<Dropdown data={kinship} name=author value=author title="Compare against" defaultValue="Karl Edward Wagner" />

<BarChart
    data={comparison}
    x=display_name
    y=zscore
    series=who
    type=grouped
    swapXY=true
    yFmt=num2
/>

```sql metric_defs
select
    dm.display_name,
    dm.description
from warehouse.dim_metric dm
where dm.is_multivalue = false
    and dm.metric_name <> 'jaccard'
order by dm.display_name
```

<Accordion>
    <AccordionItem title="*Definitions">

<DataTable data={metric_defs} rows=11>
    <Column id=display_name title="Metric" />
    <Column id=description title="Definition" wrap=true />
</DataTable>

    </AccordionItem>
</Accordion>

