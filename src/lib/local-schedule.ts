/** Pure formatter shared by the browser island and deterministic timezone tests. */
export function formatLocalSchedule(start: string, end: string, locale: string, timeZone: string) {
  try {
    const formatter = new Intl.DateTimeFormat(locale, {
      timeZone, year: 'numeric', month: 'short', day: 'numeric',
      hour: 'numeric', minute: '2-digit', timeZoneName: 'short',
    });
    return { timeZone, label: `${formatter.format(new Date(start))} – ${formatter.format(new Date(end))}` };
  } catch {
    // Leave the server-rendered host-time schedule usable on unsupported browsers.
    return null;
  }
}
