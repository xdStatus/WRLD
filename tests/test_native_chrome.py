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
        self.assertEqual(len(drag_attributes), 3)
        self.assertIn('window-drag-strip pywebview-drag-region', drag_attributes)
        self.assertIn('class="window-drag-strip pywebview-drag-region"', MARKUP)
        self.assertIn('topbar glass pywebview-drag-region', drag_attributes)
        self.assertIn('pywebview-drag-region', drag_attributes)
        self.assertNotIn('class="app pywebview-drag-region"', MARKUP)
        self.assertNotIn('id="windowChrome"', MARKUP)

    def test_frameless_window_controls_hidden(self):
        for element_id in ('winMin', 'winMax', 'winClose', 'windowChrome'):
            self.assertNotIn('id="' + element_id + '"', MARKUP)
        self.assertIn("document.body.classList.add('native-shell')", HTML)
        self.assertIn("if(e.key==='F11')", HTML)
        for action in ('minimize', 'maximize', 'close'):
            self.assertIn("'" + action + "'", NATIVE)

    def test_audio_visualizer_expands_into_right_panel(self):
        self.assertIn('def set_visualizer_expanded(self, expanded):', NATIVE)
        self.assertIn('target = 800 if expanded else 400', NATIVE)
        self.assertIn('win.resize(width, 1080)', NATIVE)
        self.assertIn('time.sleep(0.016)', NATIVE)
        self.assertIn('id="visualizerExpandTab"', MARKUP)
        self.assertIn('id="reactivePanel"', MARKUP)
        self.assertEqual(MARKUP.count('id="visualizerWrap"'), 1)
        self.assertIn('body.wrld-reactive-expanded .wrld-reactive-panel{opacity:1', HTML)
        self.assertIn('left:400px;top:0;bottom:0;width:400px', HTML)
        self.assertIn('body.wrld-reactive-expanded .app{width:400px', HTML)
        self.assertIn('body.wrld-reactive-expanded:not(.wrld-settings-open) #playerDock{', HTML)
        self.assertIn('body.wrld-reactive-expanded:not(.wrld-settings-open) .wrld-reactive-panel{bottom:148px}', HTML)
        self.assertIn('const centerShape=.14+.86*', HTML)
        self.assertIn("ctx.shadowColor='rgba(255,255,255,.70)'", HTML)
        self.assertIn("api.set_visualizer_expanded(expanded)", HTML)
        self.assertIn('body.wrld-settings-open .visualizer-expand-tab', HTML)

    def test_settings_owns_full_workspace(self):
        self.assertIn("document.body.classList.toggle('wrld-settings-open',view==='settings')", HTML)
        self.assertIn('body.wrld-settings-open #playerDock{display:none!important}', HTML)
        self.assertIn('body.wrld-settings-open .side,', HTML)
        self.assertIn('body.wrld-settings-open #settingsPanel{display:flex', HTML)
        self.assertIn("if(state.view==='settings')setView(musicViewBeforeSettings)", HTML)

    def test_about_replay_uses_original_intro(self):
        self.assertIn('id="replayIntro"', MARKUP)
        self.assertIn('Preview Magicule Singularity', MARKUP)
        self.assertIn("const wrldIntroMarkup=$('wrldIntro')?.outerHTML||'';", HTML)
        self.assertIn("document.body.insertAdjacentHTML('afterbegin',wrldIntroMarkup)", HTML)
        self.assertIn("$('replayIntro').addEventListener('click',replayWrldIntro)", HTML)
        self.assertIn("document.body.classList.remove('wrld-intro-running')", HTML)


if __name__ == '__main__':
    unittest.main()
