const instantPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$/;
const encoder = new TextEncoder();

function instant(value, field) {
  if (typeof value !== 'string' || !instantPattern.test(value) || !Number.isFinite(Date.parse(value))) {
    throw new Error(`Calendar ${field} must be an ISO date/time with seconds and an explicit UTC offset.`);
  }
  return new Date(value);
}

function utc(date) {
  return date.toISOString().replace(/[-:]/g, '').replace('.000', '');
}

function text(value) {
  return value.replace(/\\/g, '\\\\').replace(/\r\n|\r|\n/g, '\\n').replace(/;/g, '\\;').replace(/,/g, '\\,');
}

// RFC 5545 content lines: CRLF, at most 75 UTF-8 octets per physical
// line, and a single leading space on continuation lines.
function fold(line) {
  const lines = [];
  let current = '', bytes = 0;
  for (const character of line) {
    const size = encoder.encode(character).length;
    if (bytes + size > 75) {
      lines.push(current);
      current = ' ';
      bytes = 1;
    }
    current += character;
    bytes += size;
  }
  lines.push(current);
  return lines.join('\r\n');
}

function requiredText(value, field) {
  if (typeof value !== 'string' || !value.trim() || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(value)) {
    throw new Error(`Calendar ${field} must be nonempty text without control characters.`);
  }
  return value;
}

/** Return no payload at all until the organizer explicitly confirms a schedule. */
export function createWorkshopCalendar(workshop) {
  const schedule = workshop.schedule;
  if (schedule?.status !== 'confirmed') return null;

  const title = requiredText(workshop.title, 'title');
  const uid = requiredText(workshop.uid, 'UID');
  const officialUrl = new URL(requiredText(workshop.url, 'official URL'));
  if (officialUrl.protocol !== 'https:' || officialUrl.username || officialUrl.password || /[\r\n]/.test(workshop.url)) {
    throw new Error('Calendar official URL must be an HTTPS page without credentials or line breaks.');
  }
  const start = instant(schedule.start, 'start');
  const end = instant(schedule.end, 'end');
  if (end <= start) throw new Error('Calendar end must be after start.');
  const updated = instant(schedule.updatedAt, 'updatedAt');
  if (updated.toISOString().replace('.000Z', 'Z') !== schedule.updatedAt) {
    throw new Error('Calendar updatedAt must be a valid UTC date/time ending in Z.');
  }
  const timeZone = requiredText(schedule.timeZone, 'timezone');
  if (timeZone !== 'UTC' && !/^[A-Za-z_+-]+\/[A-Za-z0-9_+/-]+$/.test(timeZone)) {
    throw new Error('Calendar timezone must be an IANA timezone name.');
  }
  const wallClock = new Intl.DateTimeFormat('en-CA', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  });
  for (const [name, date] of [['start', start], ['end', end]]) {
    const parts = Object.fromEntries(wallClock.formatToParts(date).map(({type, value}) => [type, value]));
    const local = `${parts.year}-${parts.month}-${parts.day}T${parts.hour}:${parts.minute}:${parts.second}`;
    if (local !== schedule[name].slice(0, 19)) {
      throw new Error(`Calendar ${name} date/time or offset does not match ${timeZone}.`);
    }
  }
  const description = `${workshop.description ? requiredText(workshop.description, 'description') + '\n\n' : ''}Official workshop page: ${officialUrl.href}`;
  const location = schedule.location?.trim() ? requiredText(schedule.location.trim(), 'location') : undefined;
  const google = new URL('https://calendar.google.com/calendar/render');
  google.search = new URLSearchParams({
    action: 'TEMPLATE', text: title, dates: `${utc(start)}/${utc(end)}`,
    ctz: timeZone, details: description,
    ...(location ? { location } : {}),
  }).toString();

  // UTC instants avoid floating times and do not require a VTIMEZONE block.
  // No METHOD, ORGANIZER, ATTENDEE, or alarm: this is a visitor-owned import.
  const ics = [
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Agriculture-Vision//Workshop calendar//EN',
    'CALSCALE:GREGORIAN', 'BEGIN:VEVENT', `UID:${text(uid)}`, `DTSTAMP:${utc(updated)}`,
    `DTSTART:${utc(start)}`, `DTEND:${utc(end)}`, `SUMMARY:${text(title)}`,
    `DESCRIPTION:${text(description)}`, `URL:${officialUrl.href}`,
    ...(location ? [`LOCATION:${text(location)}`] : []),
    'STATUS:CONFIRMED', 'END:VEVENT', 'END:VCALENDAR',
  ].map(fold).join('\r\n') + '\r\n';

  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone, year: 'numeric', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
  });
  return {
    ics, googleUrl: google.href,
    downloadPath: '/agriculture-vision-2027/workshop.ics',
    start: schedule.start, end: schedule.end,
    dateLabel: `${formatter.format(start)} – ${formatter.format(end)}`,
  };
}
