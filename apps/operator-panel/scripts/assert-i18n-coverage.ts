import process from 'node:process';

import { dictionaries } from '../src/i18n.ts';
import { reasonCodeMessages } from '../src/control-plane/reasonCodes.ts';

function fail(message: string): never {
  console.error(`i18n coverage assertion failed: ${message}`);
  process.exit(1);
}

function assertParity(label: string, left: string[], right: string[]): void {
  const missingLeft = right.filter((key) => !left.includes(key));
  const missingRight = left.filter((key) => !right.includes(key));

  if (missingLeft.length > 0 || missingRight.length > 0) {
    fail(
      `${label} mismatch. missing in left=[${missingLeft.join(', ')}], missing in right=[${missingRight.join(', ')}]`,
    );
  }
}

const dictionaryLocales = Object.keys(dictionaries);
if (!dictionaryLocales.includes('en') || !dictionaryLocales.includes('tr')) {
  fail(`expected en and tr dictionaries, found ${dictionaryLocales.join(', ')}`);
}

assertParity('dictionary keys', Object.keys(dictionaries.en).sort(), Object.keys(dictionaries.tr).sort());
assertParity(
  'reason code keys',
  Object.keys(reasonCodeMessages.en).sort(),
  Object.keys(reasonCodeMessages.tr).sort(),
);

for (const [locale, dictionary] of Object.entries(dictionaries)) {
  for (const [key, value] of Object.entries(dictionary)) {
    if (!value.trim()) {
      fail(`empty dictionary value: ${locale}.${key}`);
    }
  }
}

for (const [locale, messages] of Object.entries(reasonCodeMessages)) {
  for (const [code, value] of Object.entries(messages)) {
    if (!value.trim()) {
      fail(`empty reason code message: ${locale}.${code}`);
    }
  }
}

console.log(
  JSON.stringify(
    {
      status: 'passed',
      dictionaryKeys: Object.keys(dictionaries.en).length,
      reasonCodeKeys: Object.keys(reasonCodeMessages.en).length,
      locales: dictionaryLocales,
    },
    null,
    2,
  ),
);
