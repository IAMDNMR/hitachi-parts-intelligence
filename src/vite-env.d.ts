/// <reference types="vite/client" />

/**
 * Vite's ambient types: `import.meta.env`, `import.meta.glob`, and the module
 * declarations that make `import url from './thing.webp'` a string rather than
 * an error.
 *
 * Without it, anything in tsconfig's `include` that touches `import.meta.env`
 * fails with `Property 'env' does not exist on type 'ImportMeta'` — an error
 * about the ambient types, not about the code.
 */
