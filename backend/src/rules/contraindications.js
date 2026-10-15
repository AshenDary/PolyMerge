import { readFileSync } from 'node:fs';

const mapping = JSON.parse(readFileSync(new URL('../../../data/rules/research_rule_mapping.json', import.meta.url), 'utf8'));
const ABSOLUTE_CONTRAINDICATION_PAIRS = mapping.pairs;
const tokens = new Set(mapping.pairs.flat());

function normalizeDrugSet(drugSet = []) {
  return (Array.isArray(drugSet) ? drugSet : []).map((drug) => {
    const value = String(drug).trim();
    return /^(compound::)?DB\d{5}$/i.test(value)
      ? `Compound::${value.split('::').at(-1).toUpperCase()}` : value.toLowerCase();
  });
}

export function resolveRuleIdentity(drug) {
  const [drugId] = normalizeDrugSet([drug]);
  return mapping.mappings[drugId] ? { drugId, ...mapping.mappings[drugId] }
    : { drugId, tokens: tokens.has(drugId) ? [drugId] : [], complete: tokens.has(drugId),
      source: tokens.has(drugId) ? 'legacy_literal' : null };
}

export function evaluateRuleApplicability(drugSet) {
  const identities = drugSet.map(resolveRuleIdentity);
  const known = new Set(identities.flatMap(identity => identity.tokens));
  const complete = identities.length > 0 && identities.every(identity => identity.complete);
  const rules = mapping.pairs.map(pair => {
    const triggered = pair.every(token => known.has(token));
    return { pair, status: triggered || complete ? 'evaluated'
      : pair.some(token => known.has(token)) ? 'partially_evaluated' : 'not_evaluable', triggered };
  });
  return { status: rules.every(rule => rule.status === 'evaluated') ? 'evaluated'
    : rules.some(rule => rule.status !== 'not_evaluable') ? 'partially_evaluated' : 'not_evaluable',
  mappingVersion: mapping.version, scope: mapping.scope, clinicallyValidated: false,
  source: mapping.ruleSource, rules, identities,
  unmappedDrugIds: identities.filter(identity => !identity.tokens.length).map(identity => identity.drugId) };
}

/**
 * @param {string[]} drugSet - candidate drug identifiers returned by the ML engine
 * @returns {{ type: string, pair: string[], message: string } | null}
 */
export function checkHardContraindications(drugSet) {
  const normalized = (drugSet ?? []).flatMap(drug => resolveRuleIdentity(drug).tokens);

  for (const [a, b] of ABSOLUTE_CONTRAINDICATION_PAIRS) {
    if (normalized.includes(a) && normalized.includes(b)) {
      return {
        type: 'hard_contraindication',
        pair: [a, b],
        message: `Configured research exclusion: ${a} + ${b}`,
      };
    }
  }

  return null;
}

export { normalizeDrugSet };
