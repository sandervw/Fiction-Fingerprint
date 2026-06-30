-- Standardize a measurement WITHIN its own metric group: express a value as
-- "how many standard deviations it sits from that metric's corpus average".
-- This puts every metric (sentence length, adjective density, Yule's K, ...)
-- onto one comparable, unitless scale so a work's metrics can form a fingerprint.
--
--   z = (value - avg(value)) / stddev_pop(value)   , both windowed per metric
{% macro zscore(value_col, partition_col) %}
  ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_col }}))
  / nullif({{ stddev_pop_expr(value_col) }} over (partition by {{ partition_col }}), 0)
{% endmacro %}


-- Population stddev, dispatched per engine: DuckDB stddev_pop, T-SQL/Fabric stdevp.
{% macro stddev_pop_expr(col) %}
  {{ return(adapter.dispatch('stddev_pop_expr', 'prose_fingerprint')(col)) }}
{% endmacro %}

{% macro default__stddev_pop_expr(col) %}stddev_pop({{ col }}){% endmacro %}

{% macro fabric__stddev_pop_expr(col) %}stdevp({{ col }}){% endmacro %}
