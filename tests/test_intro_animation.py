"""Release contract for the four Magicule Studio intro experiences.

These checks ensure visual changes do not reintroduce a separate 999 logo,
a plain PNG-like flight, or an overlay that can block the player indefinitely.
"""
from pathlib import Path
import re
import unittest

HTML = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
MARKUP = HTML.split("<body>", 1)[1].split("<script>", 1)[0]


class IntroAnimationContractTests(unittest.TestCase):
    def test_250_rainbow_magicules_form_continuous_letter_outlines(self):
        self.assertIn("const MAGICULE_COUNT=250;", HTML)
        self.assertIn("MAGICULE_PER_LETTER=[63,63,62,62]", HTML)
        self.assertIn("Array.from({length:MAGICULE_COUNT}", HTML)
        self.assertIn("c.strokeText(", HTML)
        self.assertIn("getImageData", HTML)
        self.assertIn("new Float64Array(pixels.length)", HTML)  # contour spacing
        self.assertIn("glyphPoints(el,count,letterIndex)", HTML)
        self.assertIn("targets=from", HTML)
        self.assertIn("destinations=headerLetters.flatMap", HTML)
        self.assertIn("const palette=", HTML)
        self.assertNotIn('class="intro-dot"', MARKUP)
        self.assertNotIn('id="introCore"', MARKUP)

    def test_unique_randomness_per_launch_and_living_particle_motion(self):
        self.assertIn("crypto.getRandomValues(entropy)", HTML)
        self.assertIn("seed=(Math.random()*4294967296)>>>0", HTML)
        self.assertIn("window.__wrldIntroLastSeed=launchSeed", HTML)
        self.assertIn("glyphSamplePhases[letterIndex]", HTML)
        self.assertIn("function livingOffset(p,time)", HTML)
        self.assertIn("wiggle:.6+rand()*1.15", HTML)
        self.assertIn("const settling=smooth((u-.70)/.30)", HTML)
        self.assertIn("wiggle.x*settling", HTML)
        self.assertIn("restingPosition(p,config.transfer)", HTML)
        self.assertNotIn("createLinearGradient(x,y,tail.x,tail.y)", HTML)
        self.assertIn("resizeTimer=setTimeout(", HTML)
        self.assertIn("clearTimeout(resizeTimer)", HTML)

    def test_four_distinct_modes_in_settings(self):
        for key, name in [
            ("singularity", "Magicule Singularity"),
            ("flow", "Prismatic Flow"),
            ("awakening", "Magicule Awakening"),
            ("ascension", "Magicule Ascension"),
        ]:
            self.assertIn('data-intro-mode="' + key + '"', MARKUP)
            self.assertIn(name, MARKUP)
            self.assertIn(key + ":{name:", HTML)
        self.assertEqual(len(re.findall(r'data-intro-mode="', MARKUP)), 4)
        self.assertIn("wrld-magicule-mode-v1", HTML)
        self.assertIn("localStorage.setItem('wrld-magicule-mode-v1',mode)", HTML)
        self.assertIn("renderIntroChoices()", HTML)
        self.assertIn("replayWrldIntro(mode)", HTML)
        self.assertIn("aria-pressed", HTML)

    def test_particle_transfer_and_wordmark_flutter(self):
        self.assertIn("function flight(p,time)", HTML)
        self.assertIn("function transfer(p,time)", HTML)
        self.assertIn("Math.sin(Math.PI*progress)", HTML)
        self.assertIn("function renderLettering(time)", HTML)
        self.assertIn("function renderParticles(time)", HTML)
        self.assertIn("headerLetters.flatMap", HTML)
        self.assertIn("document.body.classList.remove('wrld-intro-running')", HTML)

    def test_visible_brand_is_wrld_only(self):
        header = MARKUP.split('<div class="brand">', 1)[1].split('<label class="search"', 1)[0]
        self.assertNotIn("999", header)
        for letter in "WRLD":
            self.assertIn('class="header-letter">' + letter + "</span>", header)
            self.assertIn('class="intro-letter">' + letter + "</span>", MARKUP)
        self.assertIn("<strong>WRLD</strong>", MARKUP)
        self.assertIn('id="logoCometBtn"', header)

    def test_overlay_does_not_block_app_inputs(self):
        # This broke all WRLD buttons in v1.8.30: the invisible overlay
        # captured clicks, and finish() threw when removing resize instead
        # of onResize before removing the overlay.
        self.assertIn("pointer-events:none!important;color:white", HTML)
        self.assertIn(".wrld-intro,.wrld-intro *{pointer-events:none!important}", HTML)
        self.assertIn("removeEventListener('resize',onResize)", HTML)
        self.assertNotIn("removeEventListener('resize',resize)", HTML)
        self.assertIn("setTimeout(finish,5100)", HTML)
        self.assertIn("magiculeOverlaySafetyHide", HTML)
        self.assertIn("recoverWrldIntro(intro)", HTML)
        self.assertNotIn("pointer-events:all;color:white", HTML)

    def test_replay_and_failure_cleanup(self):
        self.assertIn('id="introParticleCanvas"', MARKUP)
        self.assertIn('id="replayIntro"', MARKUP)
        self.assertIn("prefers-reduced-motion: reduce", HTML)
        self.assertIn("fallback=setTimeout(finish,4800)", HTML)
        self.assertIn("cancelAnimationFrame(frame)", HTML)
        self.assertIn("document.body.insertAdjacentHTML('afterbegin',wrldIntroMarkup)", HTML)
        self.assertIn("$('replayIntro').addEventListener('click',()=>replayWrldIntro(introMode))", HTML)
        self.assertEqual(len(re.findall(r"<script>", HTML)), 1)
        self.assertEqual(len(re.findall(r"</script>", HTML)), 1)


if __name__ == "__main__":
    unittest.main()
