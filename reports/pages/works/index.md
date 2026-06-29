---
title: Style by Work
neverShowQueries: true
---

```sql author_list
select distinct author as name
from warehouse.mart_style_long
order by name
```

```sql chosen
select
    author as name,
    count(*) as works,
    sum(word_count) as total_words
from (
    select distinct author, work_key, word_count
    from warehouse.mart_style_long
    where author = '${inputs.author.value}'
)
group by author
```

<Dropdown data={author_list} name=author value=name title="Author" defaultValue="Sander VanWilligen" />

**<Value data={chosen} column=works/>** measured works, **<Value data={chosen} column=total_words fmt=num0/>** words.

## Book-to-book Spread*

```sql spread
select
    display_name as metric,
    min(zscore) as min_z,
    quantile_cont(zscore, 0.25) as q1_z,
    median(zscore) as median_z,
    quantile_cont(zscore, 0.75) as q3_z,
    max(zscore) as max_z
from warehouse.mart_style_long
where is_multivalue = false
    and author = '${inputs.author.value}'
group by display_name
order by max(zscore) - min(zscore) desc
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
        select work_key from warehouse.mart_style_long
    )
order by dw.word_count desc nulls last
```

<DataTable data={works} link=link rows=all>
    <Column id=title title="Title" />
    <Column id=prose_type title="Type" />
    <Column id=word_count title="Words" fmt=num0 />
</DataTable>
