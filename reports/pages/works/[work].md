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

By <a href={work[0]?.author_link}><Value data={work} column=author/></a> - <Value data={work} column=prose_type/>, <Value data={work} column=word_count fmt=num0/> words.

## Departure from the Author's Norm*

This work's z-score minus the author's average across all their works.

```sql deviation
with this_author as (
    select distinct author_key
    from warehouse.mart_style_long
    where work_id = '${params.work}'
),
author_avg as (
    select metric_key, avg(zscore) as author_z
    from warehouse.mart_style_long
    where author_key = (select author_key from this_author)
    group by metric_key
)
select
    msl.display_name,
    msl.zscore - a.author_z as delta
from warehouse.mart_style_long msl
join author_avg a
    on a.metric_key = msl.metric_key
where msl.work_id = '${params.work}'
    and msl.is_multivalue = false
order by abs(msl.zscore - a.author_z) desc
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
    display_name,
    zscore
from warehouse.mart_style_long
where work_id = '${params.work}'
    and is_multivalue = false
order by abs(zscore) desc
```

<BarChart
    data={signature}
    x=display_name
    y=zscore
    swapXY=true
    yFmt=num2
    sort=false
/>

## Sentence Type Mix

Share of simple, compound, and complex sentences in this work.

```sql sentence_types
select
    series_label as sentence_type,
    value as proportion
from warehouse.mart_style_long
where work_id = '${params.work}'
    and concept_name = 'sentence_type_mix'
order by proportion desc
```

<BarChart
    data={sentence_types}
    x=sentence_type
    y=proportion
    swapXY=true
    yFmt=pct1
    sort=false
/>

## Punctuation

How this work's punctuation rates sit against the whole corpus (z-scores).

```sql punctuation
select
    series_label as mark,
    zscore
from warehouse.mart_style_long
where work_id = '${params.work}'
    and concept_name = 'punctuation_frequency'
order by zscore desc
```

<BarChart
    data={punctuation}
    x=mark
    y=zscore
    swapXY=true
    yFmt=num2
    sort=false
/>

## Function-word Loves/Hates

The work's 12 most unusual function-word rates vs the whole corpus (z-scores).

```sql function_words
select word, zscore
from (
    select
        series_label as word,
        zscore
    from warehouse.mart_style_long
    where work_id = '${params.work}'
        and concept_name = 'function_word_frequency'
    order by abs(zscore) desc
    limit 12
)
order by abs(zscore) desc
```

<BarChart
    data={function_words}
    x=word
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
