---
title: Test Work
neverShowQueries: true
---

Stylometric measurements per work, shown as **z-scores** (standardized across the 51-work corpus: 0 = corpus average, ±1 = one standard deviation). Pick an author to filter.

```sql authors
select distinct author
from warehouse.mart_work_fingerprint
order by author
```
```sql metrics
select distinct metric_name
from warehouse.dim_metric
order by metric_name
```
<Grid cols=2>
    <Dropdown data={authors} name=author value=author title="Author" defaultValue="%">
      <DropdownOption value="%" valueLabel="All authors" />
    </Dropdown>
    <Dropdown data={metrics} name=metric_name value=metric_name title="Metric" multiple=true />
</Grid>

```sql works
select
    title,
    author,
    mean_word_length,
    mean_sentence_length,
    adjective_density,
    yules_k
from warehouse.mart_work_fingerprint
where author like '${inputs.author.value}'
order by author, title
```

```sql author_metrics
select
    da.name as author,
    dm.metric_name,
    avg(fsm.value) as value,
    avg(fsm.zscore) as zscore
from warehouse.fact_style_measurement fsm
inner join warehouse.dim_metric dm
  on fsm.metric_key = dm.metric_key
inner join warehouse.dim_author da
  on fsm.author_key = da.author_key
where author like '${inputs.author.value}'
  and dm.metric_name in ${inputs.metric_name.value}
group by author, dm.metric_name
order by zscore, value
```

<DataTable data={works} rows=15>
    <Column id=title />
    <Column id=author />
    <Column id=mean_word_length fmt=num2 />
    <Column id=mean_sentence_length fmt=num2 />
    <Column id=adjective_density fmt=num2 />
    <Column id=yules_k fmt=num2 />
</DataTable>

<DataTable data={author_metrics} rows=15>
    <Column id=author />
    <Column id=metric_name />
    <Column id=value />
    <Column id=zscore fmt=num2 />
</DataTable>

<Grid cols=2>
    <BarChart data={works} x=author y=mean_word_length yFmt=num2 />
    <BarChart data={works} x=author y=yules_k yFmt=num2 />
</Grid>
