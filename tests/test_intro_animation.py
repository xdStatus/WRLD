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
        self.assertIn("300 white magicules", MARKUP)
        self.assertIn('id="replayIntro"', MARKUP)
        self.assertIn("Preview Magicule Singularity", MARKUP)
        self.assertEqual(MARKUP.count('id="replayIntro"'), 1)
        self.assertNotIn('data-intro-mode=', MARKUP)
        self.assertNotIn('Prismatic Flow', MARKUP)
        self.assertNotIn('Magicule Awakening', MARKUP)
        self.assertNotIn('Magicule Ascension', MARKUP)
        self.assertNotIn("MAGICULE_MODES", JS)
        self.assertIn("$('replayIntro').addEventListener('click',replayWrldIntro)", JS)

    def test_300_monochrome_magicules_spawn_offscreen(self):
        self.assertIn("const MAGICULE_COUNT=300;", JS)
        self.assertIn("MAGICULE_PER_LETTER=[75,75,75,75]", JS)
        self.assertIn("i,letter:Math.floor(i/75)", JS)
        self.assertIn("Array.from({length:MAGICULE_COUNT}", JS)
        self.assertIn("const shades=['#fff','#ededed'", JS)
        for snippet in ("{x:-margin", "{x:width+margin", "y:-margin", "y:height+margin"):
            self.assertIn(snippet, JS)
        self.assertIn("crypto.getRandomValues(entropy)", JS)

    def test_particle_only_center_and_top_left_letter_reveal(self):
        self.assertIn("g.fillText(el.textContent.trim()", JS)
        self.assertIn("g.getImageData(", JS)
        self.assertIn("new Float32Array(candidates.length)", JS)
        self.assertIn("const offsetX=width/2-", JS)
        self.assertIn("const offsetY=height/2-", JS)
        self.assertIn("document.querySelector('.brand h1')?.classList.add('intro-final-reveal')", JS)
        self.assertIn("@keyframes wrldHeaderBloom", HTML)
        self.assertNotIn("paintSurface(center,centerFade", JS)
        self.assertNotIn("paintSurface(dock,headerFade", JS)

    def test_living_energy_growth_and_continuous_handoff(self):
        self.assertIn("function living(p,time)", JS)
        self.assertIn("function flight(p,time)", JS)
        self.assertIn("function transfer(p,time)", JS)
        self.assertIn("const from=flight(p,SINGULARITY.transfer)", JS)
        self.assertIn("const grownSize=p.size*(1+.10*smooth(arrivalProgress(p,time)))", JS)
        self.assertIn("const gatherFreedom=(1-smooth((u-.25)/.75))", JS)
        self.assertIn("const settle=.18+.82*gatherFreedom", JS)
        self.assertIn("drift.x*(3.8*settle)*arrival", JS)
        self.assertNotIn("const breathe=smooth", JS)
        self.assertNotIn("const ripple=Math.sin", JS)
        self.assertNotIn("const aliveX=dx*breath", JS)
        self.assertIn("travel:1820,hover:3920,transfer:5420,reveal:7080,end:8000", JS)
        self.assertEqual(5420-3920,1500)
        self.assertIn("render(now)", JS)
        self.assertEqual(JS.count("function animationFrame(now)"), 1)

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
