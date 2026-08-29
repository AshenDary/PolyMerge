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

/**
 * @param {string[]} drugSet - candidate drug identifiers returned by the ML engine
 * @returns {string | null} a human-readable violation reason, or null if safe
 */
export function checkHardContraindications(drugSet) {
  const normalized = drugSet.map((d) => String(d).toLowerCase());

  for (const [a, b] of ABSOLUTE_CONTRAINDICATION_PAIRS) {
    if (normalized.includes(a) && normalized.includes(b)) {
      return `Absolute contraindication: ${a} + ${b}`;
    }
  }
  return null;
}
