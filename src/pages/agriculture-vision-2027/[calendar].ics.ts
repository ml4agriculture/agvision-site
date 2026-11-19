import type { APIRoute, GetStaticPaths } from 'astro';
import { getEntry } from 'astro:content';
import { createWorkshopCalendar } from '../../lib/workshop-calendar.mjs';

export const getStaticPaths: GetStaticPaths = async () => {
  const edition = await getEntry('editions', '2027');
  if (!edition) throw new Error('Missing 2027 edition content');
  const calendar = createWorkshopCalendar(edition.data);
  // No route or placeholder download is emitted for a pending schedule.
  return calendar ? [{ params: { calendar: 'workshop' }, props: { calendar } }] : [];
};

export const GET: APIRoute = ({ props }) => new Response(props.calendar.ics, {
  headers: { 'Content-Type': 'text/calendar; charset=utf-8' },
});
