import { z } from 'astro/zod';

const text = z.string().trim().min(1);
const path = z.string().regex(/^\/[a-z0-9]+(?:[/-][a-z0-9]+)*$/);
const httpsUrl = z.url().refine((value) => {
  const url = new URL(value);
  return url.protocol === 'https:' && !url.username && !url.password;
}, 'Use an HTTPS URL without credentials');
const heading = z.object({ eyebrow: text, title: text, intro: text.optional() });

export const scheduleSchema = z.discriminatedUnion('status', [
  z.object({ status: z.literal('pending') }).strict(),
  z.object({
    status: z.literal('confirmed'),
    start: text, end: text, timeZone: text, updatedAt: text,
    location: text.optional(),
  }).strict(),
]);

// Keep public editorial data separate from the imported historical snapshot.
// Calendar validation also checks real wall-clock dates and timezone offsets.
export const editionSchema = z.object({
  path,
  year: z.number().int().min(2020),
  label: text,
  title: text,
  titlePrefix: text,
  description: text,
  url: httpsUrl,
  uid: text,
  metaTitle: text,
  metaDescription: text,
  noIndex: z.boolean().default(true),
  hero: z.object({ image: z.string().regex(/^\/media\/[\w.-]+$/), context: text }),
  notice: z.object({ title: text, text }).optional(),
  overview: heading.extend({
    paragraphs: z.array(text).min(1),
    link: z.object({ label: text, href: path }).optional(),
  }),
  status: z.object({
    edition: text, proposal: text, acceptance: text,
    notification: z.object({ label: text, url: httpsUrl, date: z.iso.date(), dateLabel: text }).optional(),
  }),
  schedule: scheduleSchema,
  speakers: heading.extend({
    people: z.array(z.object({ name: text, role: text, organization: text, url: httpsUrl })).min(1),
  }).optional(),
  research: heading.extend({
    areas: z.array(z.object({ title: text, text })).min(1),
    note: text.optional(),
  }).optional(),
  archive: heading.extend({
    years: z.array(z.object({ year: z.number().int(), href: path, label: text })).min(1),
    note: text.optional(),
  }).optional(),
}).refine(({ title, titlePrefix }) => title.startsWith(`${titlePrefix} `), {
  message: 'The heading prefix must match the start of the full workshop title', path: ['titlePrefix'],
});

export type Edition = z.infer<typeof editionSchema>;
