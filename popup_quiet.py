"""v49: keep the one-per-open popups out of the way in tests that aren't about them.
QUIET (an init script, runs before every load): the notifications card is never due (its open counter is pinned at 1,
so each load is open 2) and the Settings tip counts as already seen. Their own tests: notif_prompt_test, settings_tip_test."""
QUIET = ("try { localStorage.setItem('chisme-notif', JSON.stringify({ n: 1, shows: 1 }));"
         " if (!localStorage.getItem('chisme-settings-tip')) localStorage.setItem('chisme-settings-tip', 'test:0'); } catch (e) {}")
