// One-time round-27 assembly: image-tool pigment only, onto untouched inherited rock.
// Requires the generated sieve pigment at wall-v8.png; do not rerun on final wall.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {decode, encode, thumbnail} = require('../line-1/media/finish-wall.cjs');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const oldBytes = fs.readFileSync('artifacts/line-2/wall-v7.png');
const pigmentBytes = fs.readFileSync('artifacts/line-2/wall-v8.png');
const old = decode(oldBytes), pigment = decode(pigmentBytes);
const result = {...old, pixels:Buffer.from(old.pixels)};
const bounds = {left:255, top:230, right:415, bottom:390};
const crop = {left:190, top:245, right:1060, bottom:1100};
for (let y=bounds.top;y<bounds.bottom;y++) for(let x=bounds.left;x<bounds.right;x++) {
  const x0=crop.left+(x-bounds.left)*(crop.right-crop.left)/(bounds.right-bounds.left);
  const x1=crop.left+(x+1-bounds.left)*(crop.right-crop.left)/(bounds.right-bounds.left);
  const y0=crop.top+(y-bounds.top)*(crop.bottom-crop.top)/(bounds.bottom-bounds.top);
  const y1=crop.top+(y+1-bounds.top)*(crop.bottom-crop.top)/(bounds.bottom-bounds.top);
  let opacity=0, area=0, sums=[0,0,0];
  for(let sy=Math.floor(y0);sy<Math.ceil(y1);sy++) for(let sx=Math.floor(x0);sx<Math.ceil(x1);sx++) {
    const weight=(Math.min(x1,sx+1)-Math.max(x0,sx))*(Math.min(y1,sy+1)-Math.max(y0,sy));
    const i=(sy*pigment.width+sx)*3;
    const [r,g,b]=pigment.pixels.subarray(i,i+3);
    const a=Math.min(0.86,Math.max(0,(235-Math.min(r,g,b))/190));
    // White source is transparent; earth pigment keeps destination rock texture.
    const color=r-g>35 ? (g-b>55 ? [83,48,18] : [124,48,23]) : [29,24,17];
    area+=weight; opacity+=a*weight;
    for(let c=0;c<3;c++) sums[c]+=color[c]*a*weight;
  }
  if(opacity===0) continue;
  const i=(y*old.width+x)*3, alpha=opacity/area;
  const texture=0.65+(old.pixels[i]+old.pixels[i+1]+old.pixels[i+2])/1500;
  for(let c=0;c<3;c++) result.pixels[i+c]=Math.round(old.pixels[i+c]*(1-alpha)+sums[c]/opacity*texture*alpha);
}
let changed=0,outside=0;
for(let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
  const i=(y*old.width+x)*3;
  if(!old.pixels.subarray(i,i+3).equals(result.pixels.subarray(i,i+3))) {
    changed++;
    if(x<bounds.left||x>=bounds.right||y<bounds.top||y>=bounds.bottom) outside++;
  }
}
if(outside || !changed) throw Error('preservation or mark failed');
const png=encode(result), jpg=thumbnail(result);
if(!decode(png).pixels.equals(result.pixels)) throw Error('PNG roundtrip failed');
if(jpg.length>100000) throw Error('preview over 100 KB');
fs.writeFileSync('artifacts/line-2/wall-v8.png',png);
fs.writeFileSync('artifacts/line-2/wall.png',png);
fs.writeFileSync('dist/line-2/27.jpg',jpg);
const report={previous_sha256:hash(oldBytes),pigment_sha256:hash(pigmentBytes),sha256:hash(png),
  width:old.width,height:old.height,format:'PNG',png_bytes:png.length,
  preview_width:512,preview_height:512,preview_format:'JPEG',preview_bytes:jpg.length,
  bounds,changed_pixels:changed,unchanged_pixels:old.width*old.height-changed,
  outside_mark_changed_pixels:outside,png_roundtrip_passed:true};
fs.writeFileSync('line-2/media-check-27.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
