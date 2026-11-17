import type { APIRoute } from 'astro';
import pages from '../content/snapshot.json';

export const GET: APIRoute = () => {
  const index = (pages as Array<{ path: string; title: string; html: string }>).map(({ path, title, html }) => ({
    path, title,
    text: html.replace(/<[^>]+>/g, ' ').replace(/&(?:nbsp|#160);/g, ' ').replace(/\s+/g, ' ').trim(),
  }));
  return new Response(JSON.stringify(index), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
};
