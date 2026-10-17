# Reviewed Research-Rule Mapping

Version v2 (2026-10-17) adds eight positive ingredient/category mappings to the
existing aspirin mapping. Canonical IDs and names are checked against the
tracked Hetionet fragment, not guessed from user input. Each added record gives
its NLM source identifier, reference, date and ingredient/salt/prodrug boundary.
References support category membership, not PolyMerge's exclusion semantics.

The artifact is open-world: a known ACE inhibitor is not automatically a
verified nonmember of every other category. Missing class edges, absent labels,
different primary classes and unlisted terms are all **unknown**, not negative
evidence. No verified nonmember records are asserted in this version. Every
canonical record retains `complete: false`; neither runtime trusts that flag
to establish canonical negative membership. Legacy literal-category inputs are
closed-world test fixtures only, not canonical clinical evidence.

Graph pharmacologic-class edges remain unchanged. In particular, decreased
blood pressure is not equated with ACE inhibition, and aldosterone antagonism
alone is not automatically equated with the configured diuretic category.
Unreviewed compounds, combination products, brands and metabolites are not
silently aliased. Eplerenone and other unreviewed compounds remain unknown.

## Sources and Reuse

- Existing identity/aspirin graph evidence retains Hetionet provenance and the
  upstream source-license boundaries documented by the project's data sources.
- DailyMed label references are supplied by manufacturers/labelers and hosted by
  NLM. This artifact stores factual classifications and short original review
  notes, not redistributed label documents or images. DailyMed hosting is not
  an assertion of blanket ownership or unrestricted licensing of all content.
- NLM MeSH is the classification source for spironolactone (D013148). Preserve
  NLM attribution and applicable [MeSH use/reuse terms](https://www.nlm.nih.gov/databases/download/mesh.html)
  in downstream distribution. The project acknowledges the U.S. National
  Library of Medicine; NLM does not endorse PolyMerge or its modifications.
- No restricted DrugBank dataset was downloaded or redistributed. Existing
  Compound::DB identifiers are retained from the graph; source-label IDs are
  distinct identifiers, not newly asserted DrugBank cross-reference records.

Further publication should independently review source terms and the category
mappings. No dosing, clinical suitability, safety, synergy or formulation
conclusion follows from this dataset.

See also [NLM web policies](https://www.nlm.nih.gov/web_policies.html) for
third-party content restrictions and [DailyMed's description of submitted
labeling](https://dailymed.nlm.nih.gov/dailymed/about-dailymed.cfm).
