---
title: Author Summary
---

# {params.author}

```sql summary
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

Writes in the **<Value data={summary} column=tradition/>** genre. Era: <Value data={summary} column=era/>.

<Grid cols=2>
    <BigValue data={summary} value=works title="Works in corpus" />
    <BigValue data={summary} value=total_words title="Total words" fmt=num0 />
</Grid>

## Signature Stylometrics*

```sql distinctive
select
    display_name,
    avg(zscore) as zscore
from warehouse.mart_style_long
where author = '${params.author}'
    and is_multivalue = false
group by display_name
order by abs(avg(zscore)) desc
```

<BarChart
    data={distinctive}
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

## Sentence Breakdown

```sql sentence_types
select
    series_label as sentence_type,
    avg(value) as proportion
from warehouse.mart_style_long
where author = '${params.author}'
    and concept_name = 'sentence_type_mix'
group by series_label
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

## Punctuation Preferences

```sql punctuation
select
    series_label as mark,
    avg(zscore) as zscore
from warehouse.mart_style_long
where author = '${params.author}'
    and concept_name = 'punctuation_frequency'
group by series_label
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

```sql function_words
select word, zscore
from (
    select
        series_label as word,
        avg(zscore) as zscore
    from warehouse.mart_style_long
    where author = '${params.author}'
        and concept_name = 'function_word_frequency'
    group by series_label
    order by abs(avg(zscore)) desc
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
