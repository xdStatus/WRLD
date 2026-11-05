"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(path.resolve(__dirname, "../app/src/main/assets/index.html"), "utf8");
const [head,scriptEnd] = html.split("<script>");
assert.ok(scriptEnd, "Android UI needs one inline script");
const js = scriptEnd.split("</script>")[0];
assert.equal((html.match(/<script>/g) || []).length, 1);
const requiredMarkup = [
  'id="wrldIntro"', 'id="introVeil"', 'id="introParticleCanvas"',
  'id="introLettering"', 'class="intro-letter">W', 'class="intro-letter">R',
  'class="intro-letter">L', 'class="intro-letter">D',
  'class="header-letter">W', 'class="header-letter">R',
  'class="header-letter">L', 'class="header-letter">D',
];
for (const marker of requiredMarkup) {
  assert.ok(head.includes(marker), "Missing Singularity markup: " + marker);
}
const header = head.split('<div class="brand">')[1].split("</div>")[0];
assert.doesNotMatch(header, /Animated 999|class="digit"/);
assert.match(header, /class="brand-magicule"/);

// This caught the original regression: Android's header is <strong>,
// whereas the Windows port incorrectly searched for ".brand h1".
const androidHeader = head.split('<span class="brand-text">')[1].split('<small>Android Edition')[0];
assert.equal((androidHeader.match(/class="header-letter"/g)||[]).length,4,
  "Android header must contain all four transfer targets");
const headerTarget = js.match(/const headerLetters=Array\.from\(document\.querySelectorAll\('([^']+)'\)\)/);
assert.ok(headerTarget,"Magicule intro must query the Android header");
assert.equal(headerTarget[1],".brand-text strong .header-letter",
  "Intro must animate the Android header, not the Windows <h1> selector");
assert.match(js,/window\.__wrldIntroFrameCount\+\+/,"Animation must expose rendered frame count");
assert.match(js,/frames:window\.__wrldIntroFrameCount\|\|0/,"Runtime probe must include frame count");
assert.match(js,/__wrldIntroError/,"Animation failures should be diagnosable");

// Desktop-equivalent choreography and mobile-only performance/safety limits.
assert.match(js, /const MAGICULE_COUNT=350;/);
assert.match(js, /const MAGICULE_PER_LETTER=\[88,88,87,87\]/);
assert.match(js, /travel:1820,hover:3920,reveal:4620,transfer:5920,end:8350/);
assert.equal(4620-3920, 700, "Particles hover for 700ms before text reveal");
assert.match(js, /Array\.from\(\{length:MAGICULE_COUNT\}/);
assert.match(js, /edge:Math\.floor\(random\(\)\*4\)/);
assert.match(js, /if\(p\.edge===0\)return \{x:-margin/);
assert.match(js, /if\(p\.edge===1\)return \{x:width\+margin/);
assert.match(js, /y:-margin/);
assert.match(js, /y:height\+margin/);
assert.match(js, /function living\(p,time\)/);
assert.match(js, /function stamp\(surface,point,radius\)/);
assert.match(js, /globalCompositeOperation='destination-in'/);
assert.match(js, /const centerReveal=smooth\(\(time-SINGULARITY\.reveal\)\/340\)/);
assert.match(js, /paintSurface\(center,centerFade,centerFinish,12\*revealBloom\)/);
assert.match(js, /function transfer\(p,time\)/);
assert.match(js, /p\.dockCharged=true;stamp\(dock,dock\.points\[p\.i\],5\.2\)/);
assert.match(js, /crypto\.getRandomValues\(entropy\)/);
assert.match(js, /const watchdog=setTimeout\(finish,8900\)/);
assert.match(head, /\.wrld-intro,\.wrld-intro \*\{pointer-events:none!important\}/);
assert.match(head, /magiculeOverlaySafetyHide 9s/);
assert.match(js, /document\.addEventListener\('visibilitychange',onVisibility\)/);
assert.match(js, /document\.removeEventListener\('visibilitychange',onVisibility\)/);
assert.match(js, /dpr=Math\.min\(1\.25/);
assert.match(js, /scale=Math\.min\(1\.5/);
assert.match(js, /lastPaint>=29/);
assert.match(js, /prefers-reduced-motion: reduce/);

// Replays are delegated: Settings is rebuilt when changing tabs.
assert.match(js, /function replayWrldIntro\(\)/);
assert.match(js, /document\.body\.insertAdjacentHTML\('afterbegin',wrldIntroMarkup\)/);
assert.match(js, /if\(b\.dataset\.replayIntro\)\{replayWrldIntro\(\);return\}/);
assert.match(js, /data-replay-intro="1"/);
assert.match(js, /Preview Magicule Singularity/);
assert.doesNotMatch(js, /el\('replayIntro'\)\.addEventListener/);

// Emulator probes assert the animation is visible and actually rendering
// both at launch and after using the Settings replay button.
const activity = fs.readFileSync(path.resolve(__dirname,
  "../app/src/main/java/com/wrld/player/MainActivity.kt"),"utf8");
const smoke = fs.readFileSync(path.resolve(__dirname,"smoke-test-preview.sh"),"utf8");
assert.match(activity,/logIntroFrameProbe\("launch"\)/);
assert.match(activity,/logIntroFrameProbe\("replay"\)/);
assert.match(smoke,/launch: "running"/);
assert.match(smoke,/replay: "running"/);

// The native music library, cloud and player survive the visual-only port.
assert.match(js, /function startSky\(\)/);
assert.match(js, /call\("playQueue"/);
assert.match(js, /receiveCloudConfig:function\(data\)/);
assert.match(js, /receivePlayer:function\(data\)/);
console.log("Android Singularity tests passed: 350 magicules, 700ms hover, mobile replay, performance, fallback and song controls.");
