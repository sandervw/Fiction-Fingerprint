---
title: Style by Work
neverShowQueries: true
---

```sql author_list
select distinct da.name
from warehouse.dim_author da
join warehouse.fact_style_measurement fsm
    on fsm.author_key = da.author_key
order by da.name
```

```sql chosen
select
    da.name,
    count(distinct dw.work_key) as works,
    sum(dw.word_count) as total_words
from warehouse.dim_author da
join warehouse.dim_work dw
    on dw.author_key = da.author_key
join warehouse.fact_style_measurement fsm
    on fsm.work_key = dw.work_key
where da.name = '${inputs.author.value}'
group by da.name
```

<Dropdown data={author_list} name=author value=name title="Author" defaultValue="Sander VanWilligen" />

**<Value data={chosen} column=works/>** measured works, **<Value data={chosen} column=total_words fmt=num0/>** words.

## Book-to-book Spread*

```sql spread
select
    dm.display_name as metric,
    min(fsm.zscore) as min_z,
    quantile_cont(fsm.zscore, 0.25) as q1_z,
    median(fsm.zscore) as median_z,
    quantile_cont(fsm.zscore, 0.75) as q3_z,
    max(fsm.zscore) as max_z
from warehouse.fact_style_measurement fsm
join warehouse.dim_metric dm
    on fsm.metric_key = dm.metric_key
join warehouse.dim_author da
    on fsm.author_key = da.author_key
where dm.is_multivalue = false
    and dm.metric_name <> 'jaccard'
    and da.name = '${inputs.author.value}'
group by dm.display_name
order by max(fsm.zscore) - min(fsm.zscore) desc
```

<BoxPlot
    data={spread}
    name=metric
    min=min_z
    intervalBottom=q1_z
    midpoint=median_z
    intervalTop=q3_z
    max=max_z
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

## Works

Click a work to see its details.

```sql works
select
    dw.title,
    dw.prose_type,
    dw.word_count,
    '/works/' || dw.work_id as link
from warehouse.dim_work dw
join warehouse.dim_author da
    on dw.author_key = da.author_key
where da.name = '${inputs.author.value}'
    and dw.work_key in (
        select work_key from warehouse.fact_style_measurement
    )
order by dw.word_count desc nulls last
```

<DataTable data={works} link=link rows=all>
    <Column id=title title="Title" />
    <Column id=prose_type title="Type" />
    <Column id=word_count title="Words" fmt=num0 />
</DataTable>
