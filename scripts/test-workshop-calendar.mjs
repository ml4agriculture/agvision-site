import assert from 'node:assert/strict';
import { test } from 'node:test';
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdtempSync, readFileSync, realpathSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createWorkshopCalendar } from '../src/lib/workshop-calendar.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
// Deliberately fictitious; never served, opened in a calendar, or assigned to
// the real workshop. Crosses the US spring DST change: elapsed time is 1 hour.
const fixture = {
  title: 'FICTITIOUS calendar test: Café, crops; vision & robotics 🌿 '.repeat(3),
  url: 'https://example.org/fictitious-workshop?source=calendar&edition=test',
  uid: 'fictitious-calendar-test@example.org',
  description: 'Fixture only: Café, crops; path\\test\nBEGIN:VALARM',
  schedule: {
    status: 'confirmed',
    start: '2030-03-10T01:30:00-08:00',
    end: '2030-03-10T03:30:00-07:00',
    timeZone: 'America/Los_Angeles',
    updatedAt: '2030-01-01T12:00:00Z',
  },
};
const withSchedule = (patch) => ({ ...fixture, schedule: { ...fixture.schedule, ...patch } });
const unfold = (ics) => ics.replace(/\r\n[ \t]/g, '');
const properties = (ics) => Object.fromEntries(unfold(ics).trimEnd().split('\r\n').map((line) => {
  const split = line.indexOf(':');
  return [line.slice(0, split), line.slice(split + 1)];
}));
const decodeText = (value) => value.replace(/\\([nN,;\\])/g, (_, character) => /n/i.test(character) ? '\n' : character);

test('pending or absent schedule never creates a link or calendar payload, even with stale dates', () => {
  assert.equal(createWorkshopCalendar({}), null);
  assert.equal(createWorkshopCalendar(withSchedule({ status: 'pending' })), null);
  const real = JSON.parse(readFileSync(join(root, 'src/content/workshop-2027.json'), 'utf8'));
  assert.equal(real.schedule.status, 'pending');
  assert.equal(createWorkshopCalendar(real), null);
});

test('Google template preserves title, official page, and timezone-correct UTC instants', () => {
  const calendar = createWorkshopCalendar(fixture);
  const google = new URL(calendar.googleUrl);
  assert.equal(google.origin, 'https://calendar.google.com');
  assert.equal(google.pathname, '/calendar/render');
  assert.equal(google.searchParams.get('action'), 'TEMPLATE');
  assert.equal(google.searchParams.get('text'), fixture.title);
  assert.equal(google.searchParams.get('dates'), '20300310T093000Z/20300310T103000Z');
  assert.equal(google.searchParams.get('ctz'), 'America/Los_Angeles');
  assert.equal(google.searchParams.get('details'), `${fixture.description}\n\nOfficial workshop page: ${fixture.url}`);
  assert.equal(google.searchParams.has('location'), false);
  assert.match(calendar.dateLabel, /PST/);
  assert.match(calendar.dateLabel, /PDT/);
});

test('iCalendar has required properties, CRLF, UTF-8 folding, escaped text, and no invitations', () => {
  const { ics } = createWorkshopCalendar(fixture);
  assert.ok(ics.startsWith('BEGIN:VCALENDAR\r\nVERSION:2.0\r\n'));
  assert.ok(ics.endsWith('END:VEVENT\r\nEND:VCALENDAR\r\n'));
  assert.equal(ics.replaceAll('\r\n', '').includes('\n'), false);
  assert.equal(ics.replaceAll('\r\n', '').includes('\r'), false);
  for (const line of ics.split('\r\n')) assert.ok(Buffer.byteLength(line, 'utf8') <= 75);
  assert.ok(ics.includes('\r\n '), 'Long UTF-8 text must fold');
  assert.equal(Buffer.from(ics).toString('utf8'), ics);
  const fields = properties(ics);
  assert.ok(fields.PRODID);
  assert.equal(fields.UID, fixture.uid);
  assert.equal(fields.DTSTAMP, '20300101T120000Z');
  assert.equal(fields.DTSTART, '20300310T093000Z');
  assert.equal(fields.DTEND, '20300310T103000Z');
  assert.equal(fields.STATUS, 'CONFIRMED');
  assert.equal(decodeText(fields.SUMMARY), fixture.title);
  assert.equal(decodeText(fields.DESCRIPTION), `${fixture.description}\n\nOfficial workshop page: ${fixture.url}`);
  assert.equal(fields.URL, fixture.url);
  assert.equal(fields.LOCATION, undefined);
  assert.doesNotMatch(unfold(ics), /\r\n(?:METHOD:|ORGANIZER:|ATTENDEE:|BEGIN:VALARM)/);
  assert.equal(properties(createWorkshopCalendar(fixture).ics).UID, fields.UID);
});

test('venue is included only when explicitly provided and is escaped in the calendar file', () => {
  const location = 'Fictitious Hall, Room A; Floor 2\nTest City';
  const calendar = createWorkshopCalendar(withSchedule({ location }));
  assert.equal(new URL(calendar.googleUrl).searchParams.get('location'), location);
  assert.equal(decodeText(properties(calendar.ics).LOCATION), location);
});

test('invalid confirmed schedules fail instead of creating misleading events', () => {
  for (const patch of [
    { start: undefined },
    { start: '2030-03-10T01:30:00' },
    { start: '2030-02-30T01:30:00-08:00' },
    { end: fixture.schedule.start },
    { end: '2030-03-10T00:30:00-08:00' },
    { start: '2030-03-10T02:30:00-08:00' }, // nonexistent wall time
    { end: '2030-03-10T03:30:00-08:00' }, // wrong daylight-saving offset
    { timeZone: 'Invalid/Zone' },
    { timeZone: '+01:00' },
    { updatedAt: '2030-02-30T12:00:00Z' },
  ]) assert.throws(() => createWorkshopCalendar(withSchedule(patch)), undefined, JSON.stringify(patch));
});

test('isolated Astro build renders confirmed links/file, then removes both on return to pending', { timeout: 60000 }, () => {
  // macOS aliases /var to /private/var; Vite needs one canonical root.
  const temp = realpathSync(mkdtempSync(join(tmpdir(), 'agvision-calendar-fixture-')));
  const realData = readFileSync(join(root, 'src/content/workshop-2027.json'), 'utf8');
  try {
    cpSync(join(root, 'src'), join(temp, 'src'), { recursive: true });
    for (const file of ['package.json', 'astro.config.mjs']) cpSync(join(root, file), join(temp, file));
    symlinkSync(join(root, 'node_modules'), join(temp, 'node_modules'), 'dir');
    symlinkSync(join(root, 'public'), join(temp, 'public'), 'dir');
    const dataPath = join(temp, 'src/content/workshop-2027.json');
    const build = () => execFileSync(process.execPath, [realpathSync(join(root, 'node_modules/.bin/astro')), 'build', '--root', temp], {
      cwd: temp, encoding: 'utf8', timeout: 25000, maxBuffer: 2 * 1024 * 1024,
    });
    writeFileSync(dataPath, JSON.stringify(fixture));
    build();
    const htmlPath = join(temp, 'dist/agriculture-vision-2027/index.html');
    const icsPath = join(temp, 'dist/agriculture-vision-2027/workshop.ics');
    const html = readFileSync(htmlPath, 'utf8').replaceAll('&amp;', '&');
    const expected = createWorkshopCalendar(fixture);
    assert.ok(html.includes(`href="${expected.googleUrl}"`));
    assert.ok(html.includes(`href="${expected.downloadPath}"`));
    assert.ok(html.includes('download="agriculture-vision-2027.ics"'));
    assert.ok(html.includes('id="calendar-title"'));
    assert.ok(!html.includes('Calendar links will be available'));
    assert.equal(readFileSync(icsPath, 'utf8'), expected.ics);

    writeFileSync(dataPath, JSON.stringify(withSchedule({ status: 'pending' })));
    build();
    const pending = readFileSync(htmlPath, 'utf8');
    assert.ok(pending.includes('Calendar links will be available once the workshop schedule is confirmed.'));
    assert.ok(!pending.includes('calendar.google.com'));
    assert.ok(!pending.includes('href="/agriculture-vision-2027/workshop.ics"'));
    assert.equal(existsSync(icsPath), false, 'A pending rebuild must remove the previously generated calendar');
    assert.equal(readFileSync(join(root, 'src/content/workshop-2027.json'), 'utf8'), realData);
  } finally {
    rmSync(temp, { recursive: true, force: true });
  }
});
