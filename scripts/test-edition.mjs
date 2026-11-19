import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { editionSchema } from '../src/lib/edition-schema.ts';
import { formatLocalSchedule } from '../src/lib/local-schedule.ts';

const source = JSON.parse(readFileSync(new URL('../src/content/editions/2027.json', import.meta.url), 'utf8'));

test('edition content validates and missing index policy defaults to noindex', () => {
  assert.equal(editionSchema.parse(source).speakers.people.length, 4);
  const { noIndex, speakers, research, archive, notice, ...minimal } = source;
  const edition = editionSchema.parse(minimal);
  assert.equal(edition.noIndex, true);
  assert.equal(edition.speakers, undefined);
  assert.equal(edition.research, undefined);
  assert.equal(edition.archive, undefined);
});

test('bad content and ambiguous pending schedules fail validation', () => {
  for (const change of [
    { path: '//outside.example' },
    { path: '/edition?unreviewed=1' },
    { url: 'javascript:alert(1)' },
    { titlePrefix: 'A different workshop' },
    { speakers: { ...source.speakers, people: [] } },
    { schedule: { status: 'pending', start: '2030-01-01T00:00:00Z' } },
    { schedule: { status: 'confirmed' } },
  ]) assert.equal(editionSchema.safeParse({ ...source, ...change }).success, false);
});

test('visitor time conversion uses both dates and handles DST independently of the build host', () => {
  const start = '2030-03-10T01:30:00-08:00';
  const end = '2030-03-10T03:30:00-07:00';
  const tokyo = formatLocalSchedule(start, end, 'en-US', 'Asia/Tokyo');
  assert.match(tokyo.label, /6:30 PM/);
  assert.match(tokyo.label, /7:30 PM/);
  const la = formatLocalSchedule(start, end, 'en-US', 'America/Los_Angeles');
  assert.match(la.label, /1:30 AM PST/);
  assert.match(la.label, /3:30 AM PDT/);
  const overnight = formatLocalSchedule('2030-01-02T07:30:00Z', '2030-01-02T08:30:00Z', 'en-US', 'America/Los_Angeles');
  assert.match(overnight.label, /Jan 1, 2030/);
  assert.match(overnight.label, /Jan 2, 2030/);
  assert.equal(formatLocalSchedule(start, end, 'en-US', 'Invalid/Zone'), null);
  assert.equal(formatLocalSchedule('invalid', end, 'en-US', 'UTC'), null);
});
