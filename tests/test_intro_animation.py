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
    def test_sixty_rainbow_magicules_form_letter_shapes(self):
        self.assertIn("length:60", HTML)
        self.assertIn("Math.floor(i/15)", HTML)  # 15 per letter
        self.assertIn("getImageData", HTML)
        self.assertIn("glyphPoints(el,count)", HTML)
        self.assertIn("targets=from", HTML)
        self.assertIn("destinations=headerLetters.flatMap", HTML)
        self.assertIn("const palette=", HTML)
        self.assertNotIn('class="intro-dot"', MARKUP)
        self.assertNotIn('id="introCore"', MARKUP)

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
