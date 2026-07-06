---
title: Prose Fingerprint
neverShowQueries: true
---

How [my prose](https://wordleaves.com) compares to the authors in the measured corpus, (measured as **z-scores**). Positive means I do *more* of something than the typical work; negative, less.

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

## Stylometric* Likeness

```sql comparison
select
    display_name,
    case when is_self then 'Me' else author end as who,
    avg(zscore) as zscore
from warehouse.mart_style_long
where is_multivalue = false
    and (is_self or author = '${inputs.author.value}')
group by display_name, who
order by display_name, who
```

Z-score distance above (+) or below (–) the corpus average: me vs. the chosen author.

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

---

Built with dbt, DuckDB, and Evidence — [source on GitHub](https://github.com/sandervw/Fiction-Fingerprint).

