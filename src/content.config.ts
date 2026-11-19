import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { editionSchema } from './lib/edition-schema';

export const collections = {
  editions: defineCollection({
    loader: glob({ pattern: '*.json', base: './src/content/editions' }),
    schema: editionSchema,
  }),
};
