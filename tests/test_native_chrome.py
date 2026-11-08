"""Regression checks for WRLD's frameless native chrome and intro replay."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
NATIVE = (ROOT / 'native.py').read_text(encoding='utf-8')
HTML = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
MARKUP = HTML.split('<body>', 1)[1].split('<script>', 1)[0]


class NativeChromeContractTests(unittest.TestCase):
    def test_frameless_window_stays_left_and_cannot_be_dragged(self):
        self.assertIn('frameless=True', NATIVE)
        self.assertIn('easy_drag=False', NATIVE)
        self.assertIn("window.move(0, 0)", NATIVE)
        self.assertIn("win.move(0, 0)", NATIVE)
        self.assertNotIn('pywebview-drag-region', MARKUP)
        self.assertIn('class="window-drag-strip" aria-hidden="true"', MARKUP)
        self.assertIn('pointer-events:none!important', HTML)
        self.assertNotIn('title="Drag window"', MARKUP)
        self.assertNotIn('class="app pywebview-drag-region"', MARKUP)

    def test_always_on_top_button_and_native_toggle(self):
        self.assertIn('id="alwaysOnTopBtn"', MARKUP)
        self.assertIn('class="header-actions"', MARKUP)
        self.assertIn('aria-pressed="false"', MARKUP)
        self.assertIn("api.set_always_on_top(enabled)", HTML)
        self.assertIn("btn.setAttribute('aria-pressed',String(active))", HTML)
        self.assertIn('.header-settings.always-on-top-toggle[aria-pressed="true"]', HTML)
        self.assertIn('def set_always_on_top(self, enabled):', NATIVE)
        self.assertIn('user32.SetWindowPos(', NATIVE)
        self.assertIn('ctypes.c_void_p(-1 if enabled else -2)', NATIVE)
        self.assertIn('0, 0, 0, 0, 0x0013', NATIVE)

    def test_native_window_has_square_flush_edges(self):
        self.assertIn('easy_drag=False, shadow=False', NATIVE)
        self.assertIn('DWMWCP_DONOTROUND', NATIVE)
        self.assertIn('DwmSetWindowAttribute(', NATIVE)
        self.assertIn('hwnd, 33, ctypes.byref(dwm_corner_preference)', NATIVE)
        self.assertIn('window.move(0, 0)', NATIVE)

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
        self.assertIn('body.wrld-reactive-expanded .wrld-reactive-panel{', HTML)
        self.assertIn('left:400px;top:0;bottom:0;width:400px', HTML)
        self.assertIn('body.wrld-reactive-expanded .app{width:400px', HTML)
        self.assertIn('body.wrld-player-wide:not(.wrld-settings-open) #playerDock{', HTML)
        self.assertIn('body.wrld-reactive-expanded:not(.wrld-settings-open) .wrld-reactive-panel{bottom:245px}', HTML)
        self.assertIn('body:not(.wrld-settings-open) .app{', HTML)
        self.assertIn('margin-left:0!important;margin-right:0!important;', HTML)
        self.assertIn('height:clamp(430px,calc(100vh - 490px),620px)', HTML)
        self.assertIn('position:fixed;z-index:6;left:12px;right:12px;bottom:5px;', HTML)
        self.assertIn('height:215px;min-height:215px;padding:23px 13px', HTML)
        self.assertIn('height:215px;min-height:215px;padding:23px 22px', HTML)
        self.assertIn('#starfield{left:0;right:auto;width:800px!important', HTML)
        self.assertIn('const sceneWidth=800;', HTML)
        self.assertIn('if(stars.length&&width===sceneWidth&&height===sceneHeight&&dpr===nextDpr)return;', HTML)
        self.assertIn('const centerShape=.14+.86*', HTML)
        self.assertIn("ctx.shadowColor='rgba(255,255,255,.70)'", HTML)
        self.assertIn('steps = 12', NATIVE)
        self.assertIn('wrld-reactive-revealed', HTML)
        self.assertIn('clip-path:inset(50% 0 50% 0);', HTML)
        self.assertIn('clip-path .75s cubic-bezier(.22,1,.36,1)', HTML)
        self.assertIn('visibility:visible;clip-path:inset(0 0 0 0);pointer-events:auto;', HTML)
        self.assertIn('const nextWidth=Math.max(1,canvas.clientWidth);', HTML)
        self.assertIn('const nextHeight=Math.max(1,canvas.clientHeight);', HTML)
        self.assertIn('transition-delay:0s;', HTML)
        self.assertIn('reactiveRevealTimer=setTimeout(()=>{', HTML)
        self.assertIn('},200);', HTML)
        self.assertIn("document.body.classList.remove('wrld-reactive-revealed')", HTML)
        self.assertIn('await new Promise(resolve=>setTimeout(resolve,750));', HTML)
        self.assertIn('clip-path:none;transition:none;', HTML)
        self.assertIn('clearTimeout(reactiveRevealTimer);', HTML)
        self.assertIn('api.set_visualizer_expanded(true)', HTML)
        self.assertIn('api.set_visualizer_expanded(false)', HTML)
        self.assertIn('function setPlayerWide(wide){', HTML)
        self.assertIn("document.body.classList.toggle('wrld-player-wide',wide)", HTML)
        self.assertIn('const before=groups.map(el=>el.getBoundingClientRect());', HTML)
        self.assertIn("duration:460,easing:'cubic-bezier(.22,1,.36,1)'", HTML)
        self.assertIn('setPlayerWide(true);', HTML)
        self.assertIn('setPlayerWide(false);', HTML)
        self.assertIn('body.wrld-settings-open .visualizer-expand-tab', HTML)

    def test_audio_reactive_expander_remains_visible(self):
        self.assertIn('color:rgba(255,255,255,.92);cursor:pointer;', HTML)
        self.assertIn('display:block;width:5px;height:40px;border-radius:999px;', HTML)
        self.assertIn('visibility:visible;clip-path:inset(0 0 0 0);pointer-events:auto;', HTML)
        self.assertIn("document.body.classList.add('wrld-reactive-revealed');", HTML)

    def test_monochrome_expander_and_library_actions(self):
        self.assertIn('.visualizer-expand-tab span{', HTML)
        self.assertIn('display:block;width:5px;height:40px;border-radius:999px;', HTML)
        self.assertIn('background:transparent;box-shadow:none;', HTML)
        self.assertNotIn('<svg viewBox="0 0 16 16"><path d="m6 3.5 4.5 4.5L6 12.5"/></svg>', MARKUP)
        self.assertIn('id="visualizerExpandTab"', MARKUP)
        self.assertIn('id="shuffleAllBtn"', MARKUP)
        self.assertNotIn('id="newPlaylistBtn"', MARKUP)
        self.assertNotIn("$('newPlaylistBtn')", HTML)
        self.assertIn('background:rgba(160,160,160,.18)', HTML)
        self.assertIn('background:rgba(180,180,180,.26)', HTML)
        self.assertIn('id=\'createPlaylistCard\'', HTML)

    def test_monochrome_audio_reactive_and_tab_switches(self):
        self.assertIn('rgba(27,27,27,.55),rgba(5,5,5,.84)', HTML)
        self.assertIn('.wrld-outgoing-row.song{background:#121212;display:grid}', HTML)
        self.assertIn('.wrld-outgoing-row.playlist-card{background:#121212}', HTML)
        self.assertIn('background:radial-gradient(circle,#191919,#080808 80%)', HTML)
        self.assertNotIn('rgba(28,36,57,.5)', HTML)
        self.assertNotIn('.wrld-outgoing-row.song{background:#11131a', HTML)

    def test_now_playing_title_stays_with_heading(self):
        self.assertIn('class="now-playing-section"', MARKUP)
        self.assertIn('class="now-track-details"', MARKUP)
        self.assertIn('class="now-title" id="nowTitle"', MARKUP)
        self.assertIn('.now-playing-section{display:flex;flex-direction:column;flex:0 0 auto;', HTML)
        self.assertIn('body:not(.wrld-settings-open) .side{flex-shrink:0}', HTML)

    def test_player_space_reserved_in_both_modes(self):
        self.assertIn("body:not(.wrld-settings-open){\n  --wrld-player-reserve:228px;", HTML)
        self.assertIn('--wrld-player-reserve:264px;', HTML)
        self.assertIn('padding-bottom:var(--wrld-player-reserve)!important;', HTML)
        self.assertIn('margin-top:0;margin-bottom:0;', HTML)
        self.assertIn('body.wrld-reactive-expanded:not(.wrld-settings-open) .side{', HTML)
        self.assertIn('margin-bottom:12px;', HTML)
        self.assertIn('height:auto!important;min-height:0;flex:1 1 auto;', HTML)
        self.assertIn('bottom:var(--wrld-player-reserve)!important;', HTML)
        self.assertIn('body:not(.wrld-settings-open) .main{', HTML)

    def test_white_progress_bars_and_clear_player_dock(self):
        self.assertIn('background:radial-gradient(circle at 50% 45%,rgba(27,27,27,.22),rgba(5,5,5,.46) 80%)!important;', HTML)
        self.assertIn('background:linear-gradient(90deg,#ededed,#fff 72%,#fff);', HTML)
        self.assertIn('background:linear-gradient(90deg,#fff var(--progress,0%),rgba(255,255,255,.20) 0);', HTML)
        self.assertIn('#playerDock .volume-shell input::-moz-range-progress{background:#fff}', HTML)
        self.assertNotIn('#b6c4ff', HTML)
        self.assertNotIn('#c9d4ff', HTML)

    def test_up_next_queue_slides_above_fixed_player(self):
        self.assertIn('body:not(.wrld-settings-open) #queueDrawer.queue-drawer{', HTML)
        self.assertIn('position:fixed;left:12px;right:auto;bottom:225px;top:auto;', HTML)
        self.assertIn('body.wrld-reactive-expanded:not(.wrld-settings-open) #queueDrawer.queue-drawer{', HTML)
        self.assertIn('left:402px;right:6px;bottom:calc(var(--wrld-player-reserve,264px) + 14px);', HTML)
        self.assertIn('width:auto;max-height:calc(100vh - var(--wrld-player-reserve,264px) - 26px);', HTML)
        self.assertIn('max-height:min(38vh,410px);', HTML)
        self.assertIn('body.wrld-queue-open:not(.wrld-settings-open) #queueDrawer.queue-drawer{', HTML)
        self.assertIn("document.body.appendChild($('queueDrawer'));", HTML)
        self.assertIn("document.body.classList.toggle('wrld-queue-open',queueOpen);", HTML)
        self.assertIn('max-height:min(38vh,390px);overflow-y:auto;', HTML)
        self.assertIn("if(queueOpen)renderQueue();", HTML)
        self.assertIn("drawer.inert=!queueOpen;", HTML)

    def test_integrated_player_dock(self):
        self.assertIn('body:not(.wrld-settings-open) #playerDock.player.glass{', HTML)
        self.assertIn('border:0!important;border-top:1px solid rgba(255,255,255,.16)!important;', HTML)
        self.assertIn('border-radius:14px 14px 0 0!important;', HTML)
        self.assertIn('left:0;right:0;bottom:0;', HTML)

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
