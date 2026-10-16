// Build-time preservation pass over the image tool's additive painting.
// Reads only workspace image assets; writes only the wall and its thumbnail.
const fs = require('node:fs');
const crypto = require('node:crypto');
const media = require('../line-1/media/finish-wall.cjs');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const destination = 'artifacts/gathering/wall-v8.png';
const oldBytes = fs.readFileSync('artifacts/gathering/wall-v7.png');
const generatedBytes = fs.readFileSync(destination);
if(hash(generatedBytes)!=='73f4853967be464b2dce8455bfced65aefc54a7118c9795fba62f2654a5f9b1d') throw Error('Requires original reviewed generation; do not rerun on final wall');
const old = media.decode(oldBytes), generated = media.decode(generatedBytes);
const output = {...old, pixels: Buffer.from(old.pixels)};
// This small patch was visually checked to contain bare rock, no ancestor pigment.
const box = [735, 230, 180, 145];
let changed = 0;
for (let y=box[1]; y<box[1]+box[3]; y++) for(let x=box[0]; x<box[0]+box[2]; x++) {
  const i=(y*old.width+x)*3;
  const [r,g,b]=generated.pixels.subarray(i,i+3);
  const curve=((x-819)/65)**2+((y-350)/100)**2;
  const arch=((curve>.64 && curve<1.4 && y<355) || (y>=350 && y<=367)) && r<108 && g<87 && b<65;
  const stone=x>=780 && x<=829 && y>=315 && y<=358 && r>g*1.65 && r-b>40;
  const chalk=x>=830 && x<=865 && y>=311 && y<=349 && r>160 && g>140 && b>110 && r-b<80;
  if(!arch && !stone && !chalk) continue;
  const color=stone ? [150,60,28] : chalk ? [226,211,175] : [43,34,24];
  // The tool supplies the mark's silhouette; original stone stays visible.
  const alpha=stone ? Math.min(.78,(r-g)/110) : chalk ? .68 : Math.min(.85,(140-r)/100);
  for(let c=0;c<3;c++) output.pixels[i+c]=Math.round(old.pixels[i+c]*(1-alpha)+color[c]*alpha);
  if(!old.pixels.subarray(i,i+3).equals(output.pixels.subarray(i,i+3))) changed++;
}
if(changed<1000) throw Error('mark missing');
const protectedHash=crypto.createHash('sha256'); let outside=0;
for(let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
  if(x>=box[0] && x<box[0]+box[2] && y>=box[1] && y<box[1]+box[3]) continue;
  const i=(y*old.width+x)*3, a=old.pixels.subarray(i,i+3), b=output.pixels.subarray(i,i+3);
  if(!a.equals(b)) outside++;
  protectedHash.update(b);
}
if(outside) throw Error('inherited pixel changed outside mark');
const bytes=media.encode(output), preview=media.thumbnail(output);
if(!media.decode(bytes).pixels.equals(output.pixels) || preview.length>100000) throw Error('encoding check failed');
fs.writeFileSync(destination,bytes);
fs.writeFileSync('dist/gathering/27.jpg',preview);
if(fs.existsSync('artifacts/gathering/wall.png')) fs.unlinkSync('artifacts/gathering/wall.png');
fs.symlinkSync('wall-v8.png','artifacts/gathering/wall.png');
const report={inherited_wall_sha256:hash(oldBytes), generated_edit_sha256:hash(generatedBytes),output_sha256:hash(bytes),
  mark_rectangle:box,changed_pixels_inside:changed,pixels_changed_outside:outside,protected_rgb_sha256:protectedHash.digest('hex'),
  method:'Image-tool arch and threshold stones selected within a bare-rock patch and composited over original rock. All other RGB pixels retained.',
  png_dimensions:[old.width,old.height],png_format:'RGB PNG',jpeg_dimensions:[512,512],jpeg_bytes:preview.length};
fs.writeFileSync('gathering/preservation-27.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
