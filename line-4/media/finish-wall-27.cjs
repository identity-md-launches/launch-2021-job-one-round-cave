// One-time assembly of the image tool's addition. Run only on the raw edit.
// The final PNG overwrites the raw edit; the older wall is never overwritten.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {decode, encode, thumbnail} = require('../../line-1/media/finish-wall.cjs');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const base = fs.readFileSync('artifacts/line-4/wall-v7.png');
if(sha(base)!=='d3496f7d910ac2de6db7bf9df12cc6daaac17d3e865b8f48230d433383b22081') throw Error('unexpected ancestral wall');
const raw = fs.readFileSync('artifacts/line-4/wall-v8.png');
const old = decode(base), generated = decode(raw);
const out = {...old, pixels:Buffer.from(old.pixels)};
const clamp = n => Math.max(0, Math.min(1,n));
function segment(x,y,ax,ay,bx,by) {
  const t=clamp(((x-ax)*(bx-ax)+(y-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2));
  return Math.hypot(x-ax-t*(bx-ax),y-ay-t*(by-ay));
}
function mask(x,y) {
  // These narrow silhouettes sit entirely on previously unpainted lower rock.
  const trail=Math.min(segment(x,y,624,917,624,969),
    segment(x,y,624,969,565,996),segment(x,y,624,969,699,1010));
  const left=Math.hypot((x-534)/32,(y-1021)/34);
  const right=Math.hypot((x-736)/34,(y-1022)/35);
  const pebble=Math.hypot(x-705,y-1046);
  return Math.max(clamp((10-trail)/3),clamp((1.10-left)/.15),
    clamp((1.10-right)/.15),clamp((14-pebble)/3));
}
let changed=0, outside=0;
const bounds=[498,906,774,1061];
for(let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
  const at=(y*old.width+x)*3;
  const inBounds=x>=bounds[0]&&x<=bounds[2]&&y>=bounds[1]&&y<=bounds[3];
  const alpha=inBounds?mask(x,y):0;
  for(let c=0;c<3;c++) out.pixels[at+c]=Math.round(old.pixels[at+c]*(1-alpha)+generated.pixels[at+c]*alpha);
  if(!old.pixels.subarray(at,at+3).equals(out.pixels.subarray(at,at+3))) {
    changed++;
    if(!inBounds || !alpha) outside++;
  }
}
if(changed<1000||outside) throw Error('empty mark or preservation failure');
const png=encode(out), jpg=thumbnail(out);
if(!decode(png).pixels.equals(out.pixels)||jpg.length>100000) throw Error('media check failed');
fs.writeFileSync('artifacts/line-4/wall-v8.png',png);
// Unlink rather than follow a canonical symlink or overwrite a hard-linked ancestor.
fs.unlinkSync('artifacts/line-4/wall.png');
fs.linkSync('artifacts/line-4/wall-v8.png','artifacts/line-4/wall.png');
fs.writeFileSync('artifacts/line-4/27.jpg',jpg);
fs.linkSync('artifacts/line-4/27.jpg','dist/line-4/27.jpg');
const report={source:'artifacts/line-4/wall-v7.png',source_sha256:sha(base),generated_sha256:sha(raw),
  wall:'artifacts/line-4/wall-v8.png',canonical_wall:'artifacts/line-4/wall.png',sha256:sha(png),
  width:out.width,height:out.height,format:'PNG',mode:'RGB',bytes:png.length,
  preview:'dist/line-4/27.jpg',preview_width:512,preview_height:512,preview_format:'JPEG',
  preview_bytes:jpg.length,preview_sha256:sha(jpg),addition_bounds_inclusive:bounds,
  changed_pixels:changed,changed_pixels_outside_addition:outside,png_roundtrip_passed:true};
fs.writeFileSync('line-4/media-check-27.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
