/// <reference types="vite/client" />

/**
 * Vite's ambient types: `import.meta.env`, `import.meta.glob`, and the module
 * declarations that make `import url from './thing.webp'` a string rather than
 * an error.
 *
 * This file did not exist, which is most of why src/ordering was never
 * type-checked: adding it to tsconfig produced three errors that were nothing
 * to do with the code — `Property 'env' does not exist on type 'ImportMeta'`
 * and two like it — so the module stayed outside and two thousand lines of
 * TypeScript went unchecked instead.
 */
