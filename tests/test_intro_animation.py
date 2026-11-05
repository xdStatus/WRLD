"""Release gate for WRLD's native shared-element startup animation.

These structural assertions prevent accidental regression to a separate logo
pop-in or an overlay that can leave the player hidden on startup.
"""
from pathlib import Path
import re
import unittest

HTML = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")


class IntroAnimationContractTests(unittest.TestCase):
    def test_30_seeded_orbs_and_real_svg_geometry(self):
        self.assertIn("length:30", HTML)
        self.assertIn("headerMark.cloneNode(true)", HTML)
        self.assertIn("getPointAtLength", HTML)
        self.assertIn("getTotalLength", HTML)
        self.assertIn("Math.pow(pull,3.2)", HTML)
        self.assertNotIn('class="intro-dot"', HTML)

    def test_overlay_handoff_to_actual_header(self):
        self.assertIn('id="introParticleCanvas"', HTML)
        self.assertIn('id="introMark"', HTML)
        self.assertIn('id="introWordmark"', HTML)
        self.assertIn("measureDock()", HTML)
        self.assertIn("headerMark.getBoundingClientRect()", HTML)
        self.assertIn("headerWord.getBoundingClientRect()", HTML)
        self.assertIn("fly(mark,dock.mark,phase,17)", HTML)
        self.assertIn("document.body.classList.remove('wrld-intro-running')", HTML)

    def test_accessibility_and_failure_cleanup(self):
        self.assertIn("prefers-reduced-motion: reduce", HTML)
        self.assertIn("fallback=setTimeout(finish,4000)", HTML)
        self.assertIn("startWrldIntro();", HTML)
        self.assertIn("intro?.remove();", HTML)
        self.assertIn("clearTimeout(fallback)", HTML)
        self.assertIn("cancelAnimationFrame(frame)", HTML)

    def test_only_one_inline_main_script(self):
        self.assertEqual(len(re.findall(r"<script>", HTML)), 1)
        self.assertEqual(len(re.findall(r"</script>", HTML)), 1)


if __name__ == "__main__":
    unittest.main()
