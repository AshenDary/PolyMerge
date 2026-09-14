import { test } from 'node:test';
import assert from 'node:assert/strict';

import { checkHardContraindications, normalizeDrugSet } from '../src/rules/contraindications.js';

test('flags MAOI + SSRI as an absolute contraindication with structured evidence', () => {
  const violation = checkHardContraindications(['maoi', 'ssri']);
  assert.deepEqual(violation, {
    type: 'hard_contraindication',
    pair: ['maoi', 'ssri'],
    message: 'Absolute contraindication: maoi + ssri',
  });
});

test('normalizes drug identifiers before applying safety rules', () => {
  const normalized = normalizeDrugSet(['MAOI', 'SSRI']);
  assert.deepEqual(normalized, ['maoi', 'ssri']);
});

test('allows a drug set with no known hard conflicts', () => {
  const violation = checkHardContraindications(['metformin', 'lisinopril']);
  assert.equal(violation, null);
});
