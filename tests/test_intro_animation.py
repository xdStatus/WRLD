"""Regression gate for WRLD's single monochrome Magicule Singularity intro."""
from pathlib import Path
import re
import unittest

HTML = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
MARKUP = HTML.split("<body>", 1)[1].split("<script>", 1)[0]
JS = HTML.split("<script>", 1)[1].split("</script>", 1)[0]


class SingularityIntroTests(unittest.TestCase):
    def test_single_launch_style_and_preview(self):
        self.assertIn("Magicule Singularity", MARKUP)
        self.assertIn("350 white magicules", MARKUP)
        self.assertIn('id="replayIntro"', MARKUP)
        self.assertIn("Preview Magicule Singularity", MARKUP)
        self.assertEqual(MARKUP.count('id="replayIntro"'), 1)
        self.assertNotIn('data-intro-mode=', MARKUP)
        self.assertNotIn('Prismatic Flow', MARKUP)
        self.assertNotIn('Magicule Awakening', MARKUP)
        self.assertNotIn('Magicule Ascension', MARKUP)
        self.assertNotIn("MAGICULE_MODES", JS)
        self.assertIn("$('replayIntro').addEventListener('click',replayWrldIntro)", JS)

    def test_350_monochrome_magicules_spawn_offscreen(self):
        self.assertIn("const MAGICULE_COUNT=350;", JS)
        self.assertIn("MAGICULE_PER_LETTER=[88,88,87,87]", JS)
        self.assertIn("i,letter:i<88?0:i<176?1:i<263?2:3", JS)
        self.assertIn("Array.from({length:MAGICULE_COUNT}", JS)
        self.assertIn("const shades=['#fff','#ededed'", JS)
        for snippet in ("{x:-margin", "{x:width+margin", "y:-margin", "y:height+margin"):
            self.assertIn(snippet, JS)
        self.assertIn("edge:Math.floor(random()*4)", JS)
        self.assertNotIn("const palette=", JS)
        self.assertNotIn("#91E8FF", JS)
        self.assertIn("crypto.getRandomValues(entropy)", JS)
        self.assertIn("window.__wrldIntroLastSeed=seed", JS)

    def test_particle_arrival_reveals_actual_font_incrementally(self):
        self.assertIn("g.fillText(el.textContent.trim()", JS)
        self.assertIn("g.getImageData(", JS)
        self.assertIn("new Float32Array(candidates.length)", JS)
        self.assertIn("function stamp(surface,point,radius)", JS)
        self.assertIn("createRadialGradient(", JS)
        self.assertIn("globalCompositeOperation='destination-in'", JS)
        self.assertIn("if(at.progress>.955&&!p.centerCharged)", JS)
        self.assertIn("stamp(center,center.points[p.i],17)", JS)
        self.assertIn("function paintSurface(surface,fade,finishStrength,blur)", JS)
        self.assertIn("const centerReveal=smooth((time-SINGULARITY.reveal)/340)", JS)
        self.assertIn("const centerFinish=smooth((time-(SINGULARITY.reveal+120))/520)", JS)
        self.assertIn("const centerFade=centerReveal*(1-smooth((time-SINGULARITY.transfer)/520))", JS)
        self.assertIn("const revealBloom=", JS)
        self.assertIn("paintSurface(center,centerFade,centerFinish,12*revealBloom)", JS)
        self.assertIn("hoverBoost=time>=SINGULARITY.hover&&time<SINGULARITY.reveal?1.16:1", JS)
        # Before reveal, the mask can be charged but must not be painted.
        self.assertNotIn("paintSurface(center,1", JS)
        self.assertNotIn("lettering.style.opacity=", JS)
        self.assertNotIn("mark.style.opacity=", JS)

    def test_living_energy_and_long_curved_handoff(self):
        self.assertIn("function living(p,time)", JS)
        self.assertIn("wiggle:.47+random()*1.18", JS)
        self.assertIn("function flight(p,time)", JS)
        self.assertIn("function transfer(p,time)", JS)
        self.assertIn("cubic(from.x,c.c1.x,c.c2.x,to.x,q)", JS)
        self.assertIn("travel:1820,hover:3920,reveal:4620,transfer:5920,end:8350", JS)
        # Even with the maximum randomized delay and travel duration,
        # arrivals must finish before the particle-only hold starts.
        max_arrival_ms=170+1370+1820+110
        self.assertLess(max_arrival_ms,3920)
        self.assertEqual(4620-3920,700)
        self.assertIn("p.dockCharged=true;stamp(dock,dock.points[p.i],5.2)", JS)
        self.assertIn("smooth((time-6100)/1450)", JS)
        self.assertIn("render(now)", JS)
        self.assertEqual(JS.count("function animationFrame(now)"),1)

    def test_click_through_recovery_and_reduced_motion(self):
        self.assertIn(".wrld-intro,.wrld-intro *{pointer-events:none!important}", HTML)
        self.assertIn("animation:magiculeOverlaySafetyHide 9s", HTML)
        self.assertIn("const watchdog=setTimeout(finish,8900)", JS)
        self.assertIn("removeEventListener('resize',onResize)", JS)
        self.assertIn("recoverWrldIntro(intro)", JS)
        self.assertIn("prefers-reduced-motion: reduce", HTML)
        self.assertIn("if(reduced)", JS)
        self.assertIn("cancelAnimationFrame(frame)", JS)
        self.assertNotIn("pointer-events:all;color:white", HTML)
        self.assertEqual(len(re.findall(r"<script>", HTML)), 1)
        self.assertEqual(len(re.findall(r"</script>", HTML)), 1)

    def test_wrld_wordmark_remains_in_header(self):
        header = MARKUP.split('<div class="brand">', 1)[1].split('<label class="search"', 1)[0]
        self.assertNotIn("999", header)
        for letter in "WRLD":
            self.assertIn('class="header-letter">' + letter + "</span>", header)
            self.assertIn('class="intro-letter">' + letter + "</span>", MARKUP)


if __name__ == "__main__":
    unittest.main()
