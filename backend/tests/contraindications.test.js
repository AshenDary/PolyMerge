import { test } from 'node:test';
import assert from 'node:assert/strict';

import { checkHardContraindications } from '../src/rules/contraindications.js';

test('flags MAOI + SSRI as an absolute contraindication', () => {
  const violation = checkHardContraindications(['maoi', 'ssri']);
  assert.ok(violation);
});

test('allows a drug set with no known hard conflicts', () => {
  const violation = checkHardContraindications(['metformin', 'lisinopril']);
  assert.equal(violation, null);
});
