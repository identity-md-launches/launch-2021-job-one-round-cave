// One-shot preservation pass over the reviewed image-tool edit. Workspace only.
const fs = require('node:fs');
const crypto = require('node:crypto');
const media = require('./png_codec.cjs');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const destination = 'artifacts/line-3/wall-v8.png';
const oldBytes = fs.readFileSync('artifacts/line-3/wall-v7.png');
if (hash(oldBytes) !== '48e05788146b4cdd85d8e2b2a5f37cd66a3be26b646b0987ec8164e7a9208eca')
  throw Error('Inherited wall must match its unchanged record');
const generatedBytes = fs.readFileSync(destination);
if (hash(generatedBytes) !== 'f12bf5e4d51d28930e97c45e3abd21a98b199fec45045324a855324f9501f9f7')
  throw Error('Requires original generation; never rerun on finished wall');
const old = media.decode(oldBytes), generated = media.decode(generatedBytes);
const output = {...old, pixels: Buffer.from(old.pixels)};
const box = [715, 248, 150, 92];
function ellipseDistance(x,y,cx,cy,rx,ry) {
  return Math.abs(Math.hypot((x-cx)/rx,(y-cy)/ry)-1)*Math.min(rx,ry);
}
function bowl(x,y,cx,cy) {
  return ellipseDistance(x,y,cx,cy,27,8)<3.7 ||
    (y>=cy && ellipseDistance(x,y,cx,cy,27,25)<4.5);
}
function archDistance(x,y) {
  let closest=1000;
  for(let step=0;step<=100;step++) {
    const t=step/100, s=1-t;
    const ax=s*s*745+2*s*t*784+t*t*826;
    const ay=s*s*289+2*s*t*255+t*t*297;
    closest=Math.min(closest,Math.hypot(x-ax,y-ay));
  }
  return closest;
}
let changed = 0;
for (let y=box[1]; y<box[1]+box[3]; y++) for (let x=box[0]; x<box[0]+box[2]; x++) {
  const i=(y*old.width+x)*3;
  const [r,g,b] = generated.pixels.subarray(i,i+3);
  const chalk = Math.hypot((x-786)/8,(y-262)/9)<1 && r>165 && g>135 && b>90;
  const charcoal = (bowl(x,y,750,299) || bowl(x,y,825,308)) && r<105 && g<78 && b<55;
  const pebble = Math.hypot((x-750)/9,(y-302)/8)<1 || Math.hypot((x-825)/9,(y-310)/8)<1;
  const ochre = (pebble || archDistance(x,y)<4.5) && r>g*1.7 && r-b>45 && g<95;
  if (!chalk && !charcoal && !ochre) continue;
  const color = chalk ? [218,201,160] : charcoal ? [42,33,23] : [152,64,30];
  const alpha = chalk ? .82 : charcoal ? Math.min(.86,(135-r)/85) : Math.min(.8,(r-g)/90);
  for(let c=0;c<3;c++) output.pixels[i+c]=Math.round(old.pixels[i+c]*(1-alpha)+color[c]*alpha);
  if (!old.pixels.subarray(i,i+3).equals(output.pixels.subarray(i,i+3))) changed++;
}
if(changed<1000) throw Error('mark missing');
let outside=0;
const protectedHash=crypto.createHash('sha256');
for (let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
  if (x>=box[0] && x<box[0]+box[2] && y>=box[1] && y<box[1]+box[3]) continue;
  const i=(y*old.width+x)*3, a=old.pixels.subarray(i,i+3), b=output.pixels.subarray(i,i+3);
  if(!a.equals(b)) outside++;
  protectedHash.update(b);
}
if(outside) throw Error('ancestral pixel changed outside patch');
const bytes=media.encode(output), preview=media.thumbnail(output);
if(!media.decode(bytes).pixels.equals(output.pixels) || preview.length>100000) throw Error('encoding failed');
fs.writeFileSync(destination,bytes);
// Replace the canonical link instead of writing through to an ancestor wall.
if (fs.existsSync('artifacts/line-3/wall.png')) fs.unlinkSync('artifacts/line-3/wall.png');
fs.symlinkSync('wall-v8.png','artifacts/line-3/wall.png');
fs.writeFileSync('dist/line-3/27.jpg',preview);
const report={source:'artifacts/line-3/wall-v7.png',source_sha256:hash(oldBytes),
  generated_edit_sha256:hash(generatedBytes),output_sha256:hash(bytes),
  patch_xywh:box,changed_pixels:changed,changed_pixels_outside_patch:outside,
  protected_rgb_sha256:protectedHash.digest('hex'),
  method:'Image-tool charcoal, ochre and chalk selected within a bare-rock patch; pigment blended over original rock. All other RGB pixels retained.',
  png_dimensions:[old.width,old.height],png_bytes:bytes.length,
  jpeg_dimensions:[512,512],jpeg_bytes:preview.length};
fs.writeFileSync('line-3/asset-build/preservation-27.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
