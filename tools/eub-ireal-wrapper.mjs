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

const { Playlist, Converter } = await import(pathToFileURL(args.lib).href);
const input = fs.readFileSync(args.input, 'utf-8');

let playlist;
try {
  playlist = new Playlist(input);
} catch (error) {
  fail(`Input does not look like iReal Pro data: ${error}`);
}

const songs = [];
for (const song of playlist.songs) {
  try {
    const musicXml = Converter.convert(song);
    songs.push({ title: song.title, musicxml: musicXml });
  } catch (error) {
    console.error(`[${song.title}] ${error}`);
  }
}

if (songs.length === 0) {
  fail('No songs could be converted from the iReal input');
}

process.stdout.write(JSON.stringify({ songs }));
