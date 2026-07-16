/// <reference types="astro/client" />

declare module 'node:fs' {
  export function existsSync(path: string): boolean;
  export function readFileSync(path: string, encoding: 'utf-8'): string;
}

declare module 'node:url' {
  export function fileURLToPath(url: string | URL): string;
}
