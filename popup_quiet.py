"""v49: keep the one-per-open popups out of the way in tests that aren't about them.
QUIET (an init script, runs before every load): the notifications card is never due (its open counter is pinned at 1,
so each load is open 2) and the Settings tip counts as already seen.
v49.12: Chisme opens to a random tab by default; QUIET pins News (unless a test picked a tab) so tests keep a known start.
Its own test: random_tab_test. Their own tests: notif_prompt_test, settings_tip_test.
v49.12: both also pin the Día de Muertos season theme off (chisme-season-pin), unless a test set it, so screenshots and
colour checks see the everyday look whatever the date. Its own test: muertos_test."""
PIN_NEWS = ("try { if (!localStorage.getItem('chisme-default-tab')) localStorage.setItem('chisme-default-tab', 'news');"
            " if (!localStorage.getItem('chisme-terms-ok')) localStorage.setItem('chisme-terms-ok', 'test');"   # v49.12: + the one-time Terms bar
            " if (!localStorage.getItem('chisme-season-pin')) localStorage.setItem('chisme-season-pin', 'off'); } catch (e) {}")
QUIET = ("try { localStorage.setItem('chisme-notif', JSON.stringify({ n: 1, shows: 1 }));"
         " if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0');"
         " if (!localStorage.getItem('chisme-default-tab')) localStorage.setItem('chisme-default-tab', 'news');"
         " if (!localStorage.getItem('chisme-terms-ok')) localStorage.setItem('chisme-terms-ok', 'test');"
         " if (!localStorage.getItem('chisme-season-pin')) localStorage.setItem('chisme-season-pin', 'off'); } catch (e) {}")
