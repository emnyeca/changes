#!/usr/bin/env node
/**
 * EUB Changes wrapper around the bundled ireal-musicxml library.
 *
 * Contract (consumed by src/changes/importers/ireal_converter.py):
 *   node eub-ireal-wrapper.mjs --lib <path/to/ireal-musicxml.mjs> --input <path/to/ireal-input>
 *
 * - stdout: one JSON document {"songs": [{"title": string, "musicxml": string}]}
 * - stderr: converter warnings (one per line; ireal-musicxml logs via console.warn/error)
 * - exit 0: at least one song converted
 * - exit 1: fatal error (bad arguments, unreadable input, playlist parse failure, no songs)
 *
 * The upstream CLI (src/cli/cli.js) is not used because it imports devDependencies
 * (sanitize-filename, validate-with-xmllint) that a production bundle does not ship.
 * The bundled build/ireal-musicxml.mjs is self-contained and needs no node_modules.
 *
 * We use Song directly rather than Playlist to bypass Playlist's multi-part song detection,
 * which auto-concatenates songs whose titles differ only in a trailing number
 * (e.g. "Afro 1" + "Afro 2" -> merged). Every === -separated entry is kept as a
 * distinct song.
 */

import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

function fail(message) {
  console.error(`[eub-ireal-wrapper] ${message}`);
  process.exit(1);
}

const { values: args } = (() => {
  try {
    return parseArgs({
      options: {
        lib: { type: 'string' },
        input: { type: 'string' },
      },
    });
  } catch (error) {
    fail(error.message);
  }
})();

if (!args.lib) fail('Missing --lib <path to ireal-musicxml.mjs>');
if (!args.input) fail('Missing --input <path to iReal input file>');
if (!fs.existsSync(args.lib)) fail(`ireal-musicxml library not found: ${args.lib}`);
if (!fs.existsSync(args.input)) fail(`Input file not found: ${args.input}`);

const { Song, Converter } = await import(pathToFileURL(args.lib).href);
const input = fs.readFileSync(args.input, 'utf-8');

// Parse the irealb:// URI manually.
// iReal Pro encodes songs as ===- separated entries; the last entry is the playlist name.
const match = /.*?(irealb(?:ook)?):\/\/([^"]*)/.exec(input);
if (!match) {
  fail('Input does not look like iReal Pro data: no irealb:// URI found');
}

const isOldFormat = match[1] === 'irealbook';
const parts = decodeURIComponent(match[2]).split('===');
if (parts.length > 1) parts.pop(); // last entry is the playlist name, not a song

if (parts.length === 0) {
  fail('No songs found in iReal input');
}

const songs = [];
for (const part of parts) {
  let song;
  try {
    song = new Song(part, isOldFormat);
  } catch (error) {
    const rawTitle = part.split('=')[0].trim() || '(unknown)';
    console.error(`[eub-ireal-wrapper] [${rawTitle}] parse error: ${error}`);
    continue;
  }
  try {
    const musicXml = Converter.convert(song);
    songs.push({ title: song.title, musicxml: musicXml });
  } catch (error) {
    console.error(`[eub-ireal-wrapper] [${song.title}] conversion error: ${error}`);
  }
}

if (songs.length === 0) {
  fail('No songs could be converted from the iReal input');
}

process.stdout.write(JSON.stringify({ songs }));
