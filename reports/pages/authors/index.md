---
title: Author Summaries
---

```sql authors
select
    da.name,
    da.tradition,
    da.era,
    count(dw.work_key) as works,
    sum(dw.word_count) as words,
    '/authors/' || da.name as link
from warehouse.dim_author da
join warehouse.dim_work dw
    on dw.author_key = da.author_key
group by da.name, da.tradition, da.era
order by da.name
```

<DataTable data={authors} link=link rows=all>
    <Column id=name title="Author" />
    <Column id=tradition title="Tradition" />
    <Column id=era title="Era" />
    <Column id=works title="Works" />
    <Column id=words title="Words" fmt=num0 />
</DataTable>
