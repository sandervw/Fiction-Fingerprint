---
title: Author Profile
---

# {params.author}

```sql profile
select
    da.name,
    da.tradition,
    da.era,
    count(distinct dw.work_key) as works,
    sum(dw.word_count) as total_words
from warehouse.dim_author da
join warehouse.dim_work dw
    on dw.author_key = da.author_key
where da.name = '${params.author}'
group by da.name, da.tradition, da.era
```

Writes in the **<Value data={profile} column=tradition/>** tradition · <Value data={profile} column=era/>.

<Grid cols=2>
    <BigValue data={profile} value=works title="Works in corpus" />
    <BigValue data={profile} value=total_words title="Total words" fmt=num0 />
</Grid>

## Signature traits

Average z-score on each metric, sorted by distance from the corpus norm. The top bars are what most define this author; right = more than average, left = less.

```sql distinctive
select
    dm.display_name,
    avg(fsm.zscore) as zscore
from warehouse.fact_style_measurement fsm
join warehouse.dim_metric dm
    on fsm.metric_key = dm.metric_key
join warehouse.dim_author da
    on fsm.author_key = da.author_key
where da.name = '${params.author}'
    and dm.is_multivalue = false
    and dm.metric_name <> 'jaccard'
group by dm.display_name
order by abs(avg(fsm.zscore)) asc
```

<BarChart
    data={distinctive}
    x=display_name
    y=zscore
    swapXY=true
    yFmt=num2
    sort=false
    title="Distinctive metrics (z-score vs corpus)"
/>

## Sentence construction

How their sentences break down by type.

```sql sentence_types
select
    replace(fsm.metric_name, 'senttype_', '') as sentence_type,
    avg(fsm.value) as proportion
from warehouse.fact_style_measurement fsm
join warehouse.dim_metric dm
    on fsm.metric_key = dm.metric_key
join warehouse.dim_author da
    on fsm.author_key = da.author_key
where da.name = '${params.author}'
    and dm.metric_name = 'sentence_type_mix'
group by fsm.metric_name
order by proportion desc
```

<BarChart
    data={sentence_types}
    x=sentence_type
    y=proportion
    swapXY=true
    yFmt=pct1
    sort=false
    title="Sentence-type mix"
/>

## Punctuation profile

Which marks they over- or under-use versus the corpus (z-score; right = more).

```sql punctuation
select
    replace(fsm.metric_name, 'punct_', '') as mark,
    avg(fsm.zscore) as zscore
from warehouse.fact_style_measurement fsm
join warehouse.dim_metric dm
    on fsm.metric_key = dm.metric_key
join warehouse.dim_author da
    on fsm.author_key = da.author_key
where da.name = '${params.author}'
    and dm.metric_name = 'punctuation_frequency'
group by fsm.metric_name
order by zscore asc
```

<BarChart
    data={punctuation}
    x=mark
    y=zscore
    swapXY=true
    yFmt=num2
    sort=false
    title="Punctuation (z-score vs corpus)"
/>

## Function-word tells

The function words that most set this author apart (top 12 by absolute z-score).

```sql function_words
select word, zscore
from (
    select
        replace(fsm.metric_name, 'funcword_', '') as word,
        avg(fsm.zscore) as zscore
    from warehouse.fact_style_measurement fsm
    join warehouse.dim_metric dm
        on fsm.metric_key = dm.metric_key
    join warehouse.dim_author da
        on fsm.author_key = da.author_key
    where da.name = '${params.author}'
        and dm.metric_name = 'function_word_frequency'
    group by fsm.metric_name
    order by abs(avg(fsm.zscore)) desc
    limit 12
)
order by abs(zscore) asc
```

<BarChart
    data={function_words}
    x=word
    y=zscore
    swapXY=true
    yFmt=num2
    sort=false
    title="Distinctive function words (z-score)"
/>

## Works

```sql works
select
    dw.title,
    dw.prose_type,
    dw.word_count
from warehouse.dim_work dw
join warehouse.dim_author da
    on dw.author_key = da.author_key
where da.name = '${params.author}'
order by dw.word_count desc
```

<DataTable data={works} rows=all>
    <Column id=title title="Title" />
    <Column id=prose_type title="Type" />
    <Column id=word_count title="Words" fmt=num0 />
</DataTable>
