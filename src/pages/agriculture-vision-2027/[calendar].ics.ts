import type { APIRoute } from 'astro';
import workshop from '../../content/workshop-2027.json';
import { createWorkshopCalendar } from '../../lib/workshop-calendar.mjs';

export function getStaticPaths() {
  const calendar = createWorkshopCalendar(workshop);
  // No route or placeholder download is emitted for a pending schedule.
  return calendar ? [{ params: { calendar: 'workshop' }, props: { calendar } }] : [];
}

export const GET: APIRoute = ({ props }) => new Response(props.calendar.ics, {
  headers: { 'Content-Type': 'text/calendar; charset=utf-8' },
});
