"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const html=fs.readFileSync(path.resolve(__dirname,"../app/src/main/assets/index.html"),"utf8");
const [head,scriptEnd]=html.split("<script>");
assert.ok(scriptEnd,"Android UI needs inline script");
const js=scriptEnd.split("</script>")[0];
assert.equal((html.match(/<script>/g)||[]).length,1);
for(const marker of ['id="wrldIntro"','id="introVeil"','id="introParticleCanvas"',
 'id="introLettering"','class="intro-letter">W','class="intro-letter">R',
 'class="intro-letter">L','class="intro-letter">D',
 'class="header-letter">W','class="header-letter">R','class="header-letter">L',
 'class="header-letter">D','id="headerMagicules"']){
 assert.ok(head.includes(marker),"Missing required intro markup: "+marker);
}
assert.match(head,/\.brand\{[^}]*order:2;margin-left:auto/,"Logo must dock top-right");
assert.match(head,/\.header #updatesButton\{order:1\}/,"Updates button moves left");
assert.match(head,/\.brand-text strong\{visibility:hidden\}/,"Header must have no filled letter display");
assert.match(js,/const MAGICULE_COUNT=350;/);
assert.match(js,/const MAGICULE_PER_LETTER=\[88,88,87,87\]/);
assert.match(js,/travel:1820,hover:3920,transfer:5420,end:8000/);
assert.equal(5420-3920,1500,"Particles should have an extended living hover");
assert.match(js,/mode:'particle-silhouette'/);
assert.match(js,/const headerLetters=Array\.from\(document\.querySelectorAll\('\.brand-text strong \.header-letter'\)\)/);
assert.match(js,/const glyph=create\(\)/,"Font used only to sample particle positions");
assert.match(js,/const image=g\.getImageData/,"Samples actual WRLD shapes");
assert.match(js,/const breathe=smooth/,"Silhouette must breathe");
assert.match(js,/Math\.sin\(time\*\.00175\)\*3\.2\*breathe/);
assert.match(js,/function transfer\(p,time\)/);
assert.match(js,/function startHeaderMagicules\(points,magicules\)/);
assert.match(js,/headerMagiculeTimer=setInterval\(draw,95\)/);
assert.match(js,/startHeaderMagicules\(dock\.points,magicules\)/);
assert.doesNotMatch(js,/paintSurface\(|ctx\.drawImage\(surface\.glyph/,"Never draw filled font");
assert.doesNotMatch(js,/SINGULARITY\.reveal|centerFinish|headerFinish/,"No lettering reveal");
assert.match(js,/edge:Math\.floor\(random\(\)\*4\)/);
assert.match(js,/const watchdog=setTimeout\(\(\)=>finish\('watchdog'\),8700\)/);
assert.match(head,/\.wrld-intro,\.wrld-intro \*\{pointer-events:none!important\}/);
assert.match(js,/document\.addEventListener\('visibilitychange',onVisibility\)/);
assert.match(js,/dpr=Math\.min\(1\.25/);
assert.match(js,/lastPaint>=29/);
assert.match(js,/const reduced=!explicitPreview&&/);
assert.match(js,/try\{startWrldIntro\(true\)\}/);
assert.match(js,/try\{startWrldIntro\(false\)\}/);
assert.match(js,/if\(b\.dataset\.replayIntro\)\{replayWrldIntro\(\);return\}/);
assert.match(js,/data-replay-intro="1"/);
assert.match(js,/function startSky\(\)/);
assert.match(js,/call\("playQueue"/);
assert.match(js,/receiveCloudConfig:function\(data\)/);
assert.match(js,/receivePlayer:function\(data\)/);
const activity=fs.readFileSync(path.resolve(__dirname,"../app/src/main/java/com/wrld/player/MainActivity.kt"),"utf8");
const smoke=fs.readFileSync(path.resolve(__dirname,"smoke-test-preview.sh"),"utf8");
assert.match(activity,/logIntroFrameProbe\("launch"\)/);
assert.match(activity,/logIntroFrameProbe\("replay"\)/);
assert.match(smoke,/launch: "running"/);
assert.match(smoke,/replay: "running"/);
console.log("Android living particle silhouette passed: no solid font, 350 dots, breathing hover, top-right dock and replay.");
