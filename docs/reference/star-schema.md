# Star schema / dimensional modeling reference

Local cheat-sheet for auditing a dbt star schema. Sources: Kimball Group ("Dimensional Modeling Techniques"), dbt docs, Microsoft Learn (full URLs at bottom). Fetched 2026-06-24. Use as a checklist, not an essay.

A star schema = central **fact** tables surrounded by **dimension** tables (the points of the star). Optimized for analytic queries (filter, group, sort, summarize) via few joins.

---

## Fact vs dimension: what goes where

| | Fact table | Dimension table |
|---|---|---|
| Holds | numeric **measures** from a business event | descriptive **context** (the things you model) |
| Columns | foreign keys to dimensions + numeric facts (+ optional degenerate dim keys, timestamps) | a key + many text/attribute columns for filtering and grouping |
| Rows | many, grows over time | relatively few, wide |
| Verb/noun | a verb (sale, payment, measurement event) | a noun (product, author, date, work) |

- Fact tables **summarize**; dimension tables **filter and group**.
- Do **not** mix the two in one table. A table is a fact OR a dimension.
- Store report labels and filter values **in dimensions**. Keep cryptic codes and bulky text **out of the fact table**.

---

## Grain: declare it first

Kimball's **four-step design process** (in order):
1. Select the business process.
2. **Declare the grain** (what exactly one fact row represents).
3. Identify the dimensions.
4. Identify the facts.

- The grain is declared **before** dimensions/facts. Every candidate dimension and fact must be **consistent with the grain**; only those that fit are allowed.
- "The most frequent design error is not declaring the grain of the fact table at the beginning." (Kimball)
- **Exactly one grain per fact table.** Mixed grain (rows at different levels of detail in one table) is a top red flag: it breaks aggregation and double-counts.
- Prefer **atomic** grain (lowest level captured) for maximum analytic flexibility.
- Dimensionality = which dim keys are present; granularity = the values of those keys (e.g. dates that are month-starts make the grain monthly).

---

## Star vs snowflake

- **Star**: dimensions are flat and **denormalized** (one table per dimension, hierarchies collapsed in). Fewer joins, easier to read, faster. This is the default to aim for.
- **Snowflake**: a dimension is normalized into sub-dimension tables. Kimball's stance: "resist your instinctive tendency to normalize or snowflake... dimension denormalization is the name of the game." Snowflaking "compromises cross-attribute browsing performance and may interfere with the legibility of the database." Acceptable only if it clearly improves understandability or performance.
- **Direct-connection principle**: a fact must connect **directly** to every relevant dimension via its own foreign key. Reaching a dimension **only through another dimension** is a red flag (that is accidental snowflaking / a normalized chain hanging off the fact). Each dimension gets its own FK in the fact.

---

## Keys

- **Surrogate key**: a meaningless integer (or hash) assigned by the warehouse, used to join fact to dimension. Benefits: smaller fact tables/indexes, insulates the model from source-system key changes, and is required for SCD type-2 versioning (the business key is no longer unique once you version).
- **Natural / business key**: the source system's own ID (e.g. `work_id`). Keep it in the dimension for reference, but join on the surrogate.
- In dbt: `dbt_utils.generate_surrogate_key([...])` (hash of the natural-key columns). Test surrogate keys `unique` + `not_null`.
- **Degenerate dimension**: a dimension-like value (e.g. order number, ticket number) that has no attributes of its own. It is left **in the fact table** as a bare key, not split into a separate dimension.

---

## Fact table types

| Type | One row = | Updated? | Example |
|---|---|---|---|
| **Transaction** | a single measurement event at an instant | insert-only | a sale, a metric reading |
| **Periodic snapshot** | the state over a fixed period (day/month) | insert-only | end-of-day inventory, monthly balance |
| **Accumulating snapshot** | one instance of a process with milestones | **rows revisited and updated** | an order/claim moving through a pipeline (date FK per milestone) |
| **Factless fact** | an event/relationship with **no numeric measure** | insert-only | "student attended class on day" (records a many-to-many it happened) |

---

## Measure additivity (critical for audits)

| Class | Sum across...? | Examples |
|---|---|---|
| **Additive** | all dimensions | quantity, amount, count |
| **Semi-additive** | all dimensions **except time** | balances, inventory on hand, headcount |
| **Non-additive** | **no** dimensions (cannot be summed across rows at all) | **ratios, percentages, averages, z-scores, Jaccard / similarity indices** |

- Additive facts are the most useful: analytic queries fetch thousands of rows and "the only useful thing to do with so many records is to add them up." (Kimball)
- **Non-additive measures must never be summed across rows.** A z-score, an average, a standardized score, or a Jaccard index is non-additive by construction.
- Correct pattern for a ratio: store the **additive numerator and denominator** as separate facts, sum each, then compute the ratio **at query time**. Do not store/aggregate the ratio itself.
- Semi-additive: sum across other dims, but for time take the period-ending value or average over the periods (never a raw sum across time).
- If a fact column is non-additive, it should be **flagged** (naming, docs, or a separate model) so no one sums it.

---

## Conformed dimensions

A dimension shared, identically, across multiple fact tables (same keys and attribute meaning). This is what lets you compare/drill consistently across processes ("integration bus"). A reusable `dim_date` or `dim_author` across several facts = conformed.

---

## Slowly Changing Dimensions (SCD)

How a dimension handles attribute change over time:

| Type | Behavior |
|---|---|
| **0** | Retain original; never change. |
| **1** | Overwrite with the latest value; no history. |
| **2** | Add a **new row** (version) per change; needs surrogate key + `valid_from`/`valid_to` (+ `is_current` flag). Preserves history. |
| **3** | Add a **new column** (e.g. `previous_value`); limited history. |

Rapidly-changing attributes are usually better stored as a fact measure than as an SCD.

---

## Date and role-playing dimensions

- **Date dimension**: the most consistent dimension in any star; pre-built calendar table. Use one shared (conformed) date dim, not ad-hoc date math.
- **Role-playing dimension**: one physical dimension referenced multiple times by a fact under different roles (e.g. `order_date` vs `ship_date` both pointing at `dim_date`; departure vs arrival airport). One table, multiple FKs in the fact; expose distinct roles via views/aliases.

---

## RED FLAGS / audit checklist

- [ ] **No declared grain**, or a fact table mixing **multiple grains** in one table.
- [ ] A fact **fails to connect directly** to a dimension (the dimension is reachable only **through another dimension** = accidental snowflake / normalized chain).
- [ ] Dimensions **snowflaked / normalized** without a clear performance or clarity justification.
- [ ] **Missing surrogate keys** on dimensions (or facts joining on raw, mutable natural keys).
- [ ] **Non-additive measures** (ratios, averages, z-scores, Jaccard/similarity) stored without flagging, at risk of being summed; ratio stored instead of its additive numerator/denominator.
- [ ] **Semi-additive** balances summed across **time**.
- [ ] **Descriptive text or high-cardinality attributes stuffed into the fact** table instead of a dimension.
- [ ] A table that is **both fact and dimension** (mixed types).
- [ ] **Many-to-many** relationship handled inside a fact wrong (should be a bridge table or a factless fact, not duplicated/fan-out rows).
- [ ] Dimension that should be **conformed** is duplicated with diverging keys/attributes across facts.
- [ ] Surrogate keys not tested `unique` + `not_null`; fact FKs without a `relationships` test to their dimension.

---

## dbt layer mapping

- **staging/** (`stg_*`, views): 1:1 with sources, light cast/rename. Atomic building blocks.
- **intermediate/** (`int_*`, often ephemeral): join/denormalize 4-6 entities to prep marts.
- **marts/**: the star itself: `dim_*` and `fct_*`/`fact_*` tables, materialized as tables. Build surrogate keys here, apply `unique`/`not_null`/`relationships` tests.

---

## Sources

- Kimball Group, Four-Step Dimensional Design Process: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/four-4-step-design-process/
- Kimball Group, Grain: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/grain/
- Kimball Group, Fact Table Structure: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/fact-table-structure/
- Kimball Group, Additive / Semi-Additive / Non-Additive Facts: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/additive-semi-additive-non-additive-fact/
- Kimball Group, Accumulating Snapshot Fact Tables: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/accumulating-snapshot-fact-table/
- Kimball Group, Dimension Surrogate Keys: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/dimension-surrogate-key/
- Kimball Group, The 10 Essential Rules of Dimensional Modeling: https://www.kimballgroup.com/2009/05/the-10-essential-rules-of-dimensional-modeling/
- Kimball Group, A Dimensional Modeling Manifesto: https://www.kimballgroup.com/1997/08/a-dimensional-modeling-manifesto/
- Kimball Group, Design Tip #46 Degenerate Dimensions: https://www.kimballgroup.com/2003/06/design-tip-46-another-look-at-degenerate-dimensions/
- dbt docs, A complete guide to dimensional modeling: https://docs.getdbt.com/terms/dimensional-modeling
- dbt Developer Blog, Building a Kimball dimensional model with dbt: https://docs.getdbt.com/blog/kimball-dimensional-model
- dbt docs, How we structure our dbt projects (staging / intermediate / marts): https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview
- Microsoft Learn, Understand star schema and the importance for Power BI: https://learn.microsoft.com/power-bi/guidance/star-schema
- Microsoft Learn, Dimensional modeling in Fabric Data Warehouse (overview, dimension tables, fact tables): https://learn.microsoft.com/fabric/data-warehouse/dimensional-modeling-overview
