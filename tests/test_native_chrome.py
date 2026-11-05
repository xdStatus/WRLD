"""Regression checks for WRLD's frameless native chrome and intro replay."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
NATIVE = (ROOT / 'native.py').read_text(encoding='utf-8')
HTML = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
MARKUP = HTML.split('<body>', 1)[1].split('<script>', 1)[0]


class NativeChromeContractTests(unittest.TestCase):
    def test_frameless_header_only_drag(self):
        self.assertIn('frameless=True', NATIVE)
        self.assertIn('easy_drag=False', NATIVE)
        self.assertIn("DRAG_REGION_DIRECT_TARGET_ONLY", NATIVE)
        drag_attributes = re.findall(r'class="([^"]*pywebview-drag-region[^"]*)"', MARKUP)
        self.assertEqual(len(drag_attributes), 2)
        self.assertIn('topbar glass pywebview-drag-region', drag_attributes)
        self.assertIn('pywebview-drag-region', drag_attributes)
        self.assertNotIn('class="app pywebview-drag-region"', MARKUP)
        self.assertNotIn('native-shell .window-chrome{display:none!important}', HTML)

    def test_frameless_window_controls(self):
        for element_id in ('winMin', 'winMax', 'winClose'):
            self.assertIn('id="' + element_id + '"', MARKUP)
        for action in ('minimize', 'maximize', 'close'):
            self.assertIn("'" + action + "'", NATIVE)
        self.assertIn('win.maximize()', NATIVE)
        self.assertIn('win.restore()', NATIVE)

    def test_about_replay_uses_original_intro(self):
        self.assertIn('id="replayIntro"', MARKUP)
        self.assertIn('Preview Magicule Singularity', MARKUP)
        self.assertIn("const wrldIntroMarkup=$('wrldIntro')?.outerHTML||'';", HTML)
        self.assertIn("document.body.insertAdjacentHTML('afterbegin',wrldIntroMarkup)", HTML)
        self.assertIn("$('replayIntro').addEventListener('click',replayWrldIntro)", HTML)
        self.assertIn("document.body.classList.remove('wrld-intro-running')", HTML)


if __name__ == '__main__':
    unittest.main()
