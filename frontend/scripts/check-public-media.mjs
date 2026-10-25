import { readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const publicDir = fileURLToPath(new URL('../public/', import.meta.url));
const maxBytes = 25 * 1024 * 1024;
const mediaExtensions = new Set([
  '.3g2', '.3gp', '.aac', '.aiff', '.alac', '.amr', '.apng', '.asf', '.avi',
  '.avif', '.bmp', '.flac', '.flv', '.gif', '.heic', '.heif', '.ico', '.jfif',
  '.jpe', '.jpeg', '.jpg', '.m2ts', '.m4a', '.m4v', '.mkv', '.mov', '.mp3',
  '.mp4', '.mpeg', '.mpg', '.mts', '.oga', '.ogg', '.ogv', '.opus', '.png',
  '.psd', '.raw', '.svg', '.tif', '.tiff', '.ts', '.vob', '.wav', '.webm',
  '.webp', '.wma', '.wmv',
]);

function walk(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(path) : [path];
  });
}

const oversized = walk(publicDir).filter((path) => {
  const extension = path.slice(path.lastIndexOf('.')).toLowerCase();
  return mediaExtensions.has(extension) && statSync(path).size > maxBytes;
});

if (oversized.length) {
  console.error('Public media exceeds the 25 MiB repository limit:');
  for (const path of oversized) {
    console.error(`- ${relative(publicDir, path)} (${(statSync(path).size / 1024 / 1024).toFixed(2)} MiB)`);
  }
  process.exitCode = 1;
} else {
  console.log('Public media size check passed (all media files are at or below 25 MiB).');
}
