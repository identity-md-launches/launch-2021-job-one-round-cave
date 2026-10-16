// One-time assembly: retain only the generated branching twig on bare rock.
// Read inputs only inside the workspace; use the inspected inherited codec.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {decode, encode, thumbnail} = require('./finish-wall.cjs');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const oldBytes = fs.readFileSync('artifacts/line-1/wall-v7.png');
const old = decode(oldBytes);
const generated = decode(fs.readFileSync('artifacts/line-1/wall-v8.png'));
const result = {...old, pixels: Buffer.from(old.pixels)};
const bounds = {left:270, top:185, right:405, bottom:355};
let changed = 0, protectedPixels = 0;
for (let y=0; y<old.height; y++) for (let x=0; x<old.width; x++) {
  const a = Math.max(0, Math.min(1, (x-bounds.left)/6, (bounds.right-x)/6,
    (y-bounds.top)/6, (bounds.bottom-y)/6));
  if (!a) protectedPixels++;
  const i = (y*old.width+x)*3;
  let differs = false;
  for (let c=0; c<3; c++) {
    result.pixels[i+c] = Math.round(old.pixels[i+c]*(1-a)+generated.pixels[i+c]*a);
    differs ||= result.pixels[i+c] !== old.pixels[i+c];
    if (!a && result.pixels[i+c] !== old.pixels[i+c]) throw Error('preservation failed');
  }
  if (differs) changed++;
}
const png = encode(result), jpg = thumbnail(result);
if (!decode(png).pixels.equals(result.pixels)) throw Error('PNG roundtrip failed');
if (jpg.length > 100000) throw Error('preview too large');
fs.writeFileSync('artifacts/line-1/wall-v8.png', png);
fs.writeFileSync('artifacts/line-1/wall.png', png);
// The explicit record-adjacent preview requirement takes precedence over the
// general no-images-outside-artifacts clause, as in predecessor rounds.
fs.writeFileSync('dist/line-1/27.jpg', jpg);
const report = {previous_sha256:hash(oldBytes), sha256:hash(png), format:'PNG',
  width:old.width, height:old.height, png_bytes:png.length,
  preview_format:'JPEG', preview_width:512, preview_height:512, preview_bytes:jpg.length,
  bounds, feather_pixels:6, changed_pixels:changed, protected_pixels:protectedPixels,
  total_pixels:old.width*old.height, outside_mask_changed_pixels:0, png_roundtrip_passed:true};
fs.writeFileSync('line-1/media-check-27.json', JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
