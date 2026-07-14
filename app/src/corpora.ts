import type { Corpus } from './types';
const modules = import.meta.glob('../public/data/kbs/*/corpus.json', { eager: true, import: 'default' }) as Record<string, Corpus>;
export const corpora = Object.values(modules);
