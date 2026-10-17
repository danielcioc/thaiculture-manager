import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const widget = await readFile(new URL('../../scripts/local_website_widget.js', import.meta.url), 'utf8');

test('local website inquiry widget does not collect or send a phone number', () => {
  assert.doesNotMatch(widget, /name=["']phone["']/i);
  assert.doesNotMatch(widget, /fields\.get\(['"]phone['"]\)/);
  assert.doesNotMatch(widget, /customer:\s*\{[^}]*phone\s*:/s);
});
