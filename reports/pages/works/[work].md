---
title: Work Detail
neverShowQueries: true
---

```sql work
select
    dw.title,
    da.name as author,
    dw.prose_type,
    dw.word_count,
    '/authors/' || da.name as author_link
from warehouse.dim_work dw
join warehouse.dim_author da
    on dw.author_key = da.author_key
where dw.work_id = '${params.work}'
```

# <Value data={work} column=title/>

By [<Value data={work} column=author/>](<Value data={work} column=author_link/>) - <Value data={work} column=prose_type/>, <Value data={work} column=word_count fmt=num0/> words.

## Departure from the Author's Norm*

This work's z-score minus the author's average across all their works.

```sql deviation
with this_work as (
    select author_key
    from warehouse.dim_work
    where work_id = '${params.work}'
),
author_avg as (
    select fsm.metric_key, avg(fsm.zscore) as author_z
    from warehouse.fact_style_measurement fsm
    where fsm.author_key = (select author_key from this_work)
    group by fsm.metric_key
)
select
    dm.display_name,
    fsm.zscore - a.author_z as delta
from warehouse.fact_style_measurement fsm
join warehouse.dim_metric dm
    on fsm.metric_key = dm.metric_key
join warehouse.dim_work dw
    on fsm.work_key = dw.work_key
join author_avg a
    on a.metric_key = fsm.metric_key
where dw.work_id = '${params.work}'
    and dm.is_multivalue = false
    and dm.metric_name <> 'jaccard'
order by abs(fsm.zscore - a.author_z) desc
```

<BarChart
    data={deviation}
    x=display_name
    y=delta
    swapXY=true
    yFmt=num2
    sort=false
/>

## Work Signature

The work's z-scores against all measured works.

```sql signature
select
    dm.display_name,
    fsm.zscore
from warehouse.fact_style_measurement fsm
join warehouse.dim_metric dm
    on fsm.metric_key = dm.metric_key
join warehouse.dim_work dw
    on fsm.work_key = dw.work_key
where dw.work_id = '${params.work}'
    and dm.is_multivalue = false
    and dm.metric_name <> 'jaccard'
order by abs(fsm.zscore) desc
```

<BarChart
    data={signature}
    x=display_name
    y=zscore
    swapXY=true
    yFmt=num2
    sort=false
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
