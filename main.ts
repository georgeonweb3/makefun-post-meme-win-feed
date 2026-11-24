// Post the Meme, Win the Feed -- make.fun entry (Node 22, stdlib only).
// u-myronera-post-the-meme-win-the-feed-2de960bf -- the meme is made by
// make_meme.py in this same repository (stdlib-only PNG rasterizer).
// The entry is the X post itself: an agent's payslip meme about make.fun,
// posted from @georgebuilding2 with @_myronera tagged and the play code
// makefun-fresco-moose-pony in the post text. This program copies POST.json
// from the repository root to /output/POST.json, where the gate reads it.
// That is all it has to do: the house reads the post's counts from X.
//
// Outside the grader's container, MAKEFUN_BOT_DIR and MAKEFUN_OUTPUT_DIR
// stand in for /bot and /output:
//   mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts

import { copyFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

const BOT_DIR = process.env.MAKEFUN_BOT_DIR ?? '/bot';
const OUTPUT_DIR = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';

mkdirSync(OUTPUT_DIR, { recursive: true });
try {
  copyFileSync(join(BOT_DIR, 'POST.json'), join(OUTPUT_DIR, 'POST.json'));
} catch (err) {
  console.error(`POST.json could not be copied from ${BOT_DIR}: ${(err as Error).message}`);
  process.exit(1);
}
