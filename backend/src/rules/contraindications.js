// Hard-coded safety fallback checks, independent of any model output.
// These run on every combination result before it reaches a client.
// Extend this list as new absolute contraindications are identified --
// do NOT rely on the GNN to learn these; they must never be soft-overridden
// by a model score.

const ABSOLUTE_CONTRAINDICATION_PAIRS = [
  ['maoi', 'ssri'],
  ['warfarin', 'nsaid'],
  ['ace_inhibitor', 'potassium_sparing_diuretic'],
];

function normalizeDrugSet(drugSet = []) {
  return (Array.isArray(drugSet) ? drugSet : []).map((drug) => String(drug).trim().toLowerCase());
}

/**
 * @param {string[]} drugSet - candidate drug identifiers returned by the ML engine
 * @returns {{ type: string, pair: string[], message: string } | null}
 */
export function checkHardContraindications(drugSet) {
  const normalized = normalizeDrugSet(drugSet);

  for (const [a, b] of ABSOLUTE_CONTRAINDICATION_PAIRS) {
    if (normalized.includes(a) && normalized.includes(b)) {
      return {
        type: 'hard_contraindication',
        pair: [a, b],
        message: `Absolute contraindication: ${a} + ${b}`,
      };
    }
  }

  return null;
}

export { normalizeDrugSet };
