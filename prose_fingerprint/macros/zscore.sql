-- macros/zscore.sql
-- Standardize a measurement WITHIN its own metric group: express a value as
-- "how many standard deviations it sits from that metric's corpus average".
-- This puts every metric (sentence length, adjective density, Yule's K, ...)
-- onto one comparable, unitless scale so a work's metrics can form a fingerprint.
--
--   z = (value - avg(value)) / stddev_pop(value)   , both windowed per metric
--
-- stddev_pop (divide by N) is used on purpose: our 51 works ARE the entire
-- corpus, not a random sample of some larger population, so the population
-- standard deviation is the honest spread of THIS data.
--
-- nullif(..., 0) guards a zero-spread metric (every work identical) from a
-- divide-by-zero: that yields NULL instead of an error.
{% macro zscore(value_col, partition_col) %}
  ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_col }}))
  / nullif(stddev_pop({{ value_col }}) over (partition by {{ partition_col }}), 0)
{% endmacro %}
