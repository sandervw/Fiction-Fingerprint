# Author Style Summaries

Data-backed style breakdowns of individual works/authors, from the warehouse z-scores
(`mart_style_long`, corpus of 141 works). Reusable source material for the Evidence site.

---

## The Night Land — William Hope Hodgson

The Night Land is the most extreme work in the 141-work corpus, and its strangeness is
syntactic, not ornamental. Its single biggest anomaly is the function word **"be"
(z = +7.6)**, the largest deviation of any series on any work — driven by Hodgson's
invented auxiliary construction *"did be"* (1,552 occurrences). The connective
scaffolding follows: *that* (+5.0), *so* (+4.7), *to* (+3.7), *and* (+3.3); 1,785
paragraphs open with "And," and 86% of sentences are complex. Its **archaic-word rate
(z = +5.0)** ranks #2 of 141, behind only *The Worm Ouroboros* (*unto* ×957, *doth*
×226, *in verity* ×189). Yet its **mean word length is the lowest in the entire corpus
(z = −3.2)** — the paradox at the style's heart: the vocabulary is plain, short,
Anglo-Saxon; the archaism lives entirely in grammar. Sentences average 39 words (#2)
with the corpus's second-highest length variance; semicolons run at +4.0z;
contractions: **zero** in 198k words. High Yule's K with low Honoré's R means a small
vocabulary hammered repetitively — incantation, not decoration. Even against Hodgson's
own eight other works, "be" sits +6.9z above his norm.

**Data caveat:** the recorded dialogue ratio (0.92, corpus rank #1) is an extractor
artifact — a desynced straight-quote toggle counted most of the book as dialogue. The
book has essentially zero quoted speech. The extractor has since been fixed; the number
corrects on the next extract + dbt build.
