# Chisme

**Chisme** (Spanish slang for gossip, or the neighborhood news) is a local news + weather app for **wherever you are**. It uses your phone's location (e.g. South San, San Antonio) to rank nearby stories and fetch your weather. The home screen stays clean: the place is shown and changed in **Settings** (tap the Chisme logo).
It uses large, bold, high-contrast text, and it's an **installable phone app (PWA)** that opens full-screen and still works offline.

* **Anywhere in the U.S. (v24):** the whole app follows your location, typed or live GPS. `data/metros.json` lists metros with hand-verified local outlets (**San Antonio, Houston, Austin, Dallas–Fort Worth, Miami**); anywhere else Chisme uses Google News searches for your city/county. **News:** only the outlets of the metro you're in (e.g. KHOU, KPRC, Houston Public Media and the Chronicle in Houston; WSVN, WPLG, Miami New Times and the Herald in Miami), plus Google News for the city, county and nearby neighborhoods; the "{Metro} headlines" section only appears in a metro's suburbs. San Antonio's newsrooms are no longer fetched elsewhere. **Weather + radar:** NWS for the point, the map recenters. **Events:** that city's Eventbrite + AllEvents pages; Visit San Antonio only near SA. **¿Cuál dieta?:** outside SA, "{City} food news" comes first (the metro's Eater + paper food desk where curated, plus a Google News food search for the city, credited to each publisher; 5 max), and San Antonio's creators stay below, labeled "Road-trip picks: San Antonio's food creators". **Sports:** your nearest NBA, NFL and MLB teams (every team in your state first on the scoreboards) and the nearest Minor League club within 60 km (Houston → Rockets, Texans, Astros, Sugar Land Space Cowboys; Austin → Spurs, Texans/Cowboys, Astros/Rangers, Round Rock Express; Miami → Heat, Dolphins, Marlins, no MiLB chip); the chips, intro and team card follow (`data/pro_teams.json`, built by `tools/build_pro_teams.py`; MiLB from the MLB Stats API's ballpark coordinates). **Header:** San Antonio's skyline in SA, simple silhouettes for Houston (Williams Tower, Pennzoil Place), Austin (the Capitol dome, Frost Bank Tower), Dallas (Reunion Tower, Fountain Place) and Miami (palms, the Freedom Tower), and the generic skyline anywhere else. Copy says your city, not San Antonio, and times use the place's time zone. Test: `location_city_test.py`.
* **Location bug fixed in v24:** on v22/v23, picking a city in Settings (e.g. "Houston TX") worked for a moment, then snapped back to San Antonio whenever the phone had location permission. The GPS `watchPosition` started at launch kept running, and its next update (iOS sends them often) called `setLocation(…, "gps")` because the saved source was no longer `"gps"`. Now a typed place stops the watch, GPS callbacks never override a typed place, and **Use my location** switches back to live GPS (which then follows you from city to city). Geocoding itself was fine: all of "Houston TX", "Houston, TX", "Houston", "77002", "Austin", "Miami FL" and "33101" resolve on both the live site and locally.
* **Your location:** uses the browser Geolocation API. **Only on first launch**, a card on the home screen explains why Chisme wants your location and offers **Use my location** or a **city/ZIP** box (or **Not now**, which keeps San Antonio). Once a place is set, or you tap Not now, the card never comes back (`localStorage` key `chisme-location-setup`), and there's no location bar on the home screen. The last location is saved on the device (`localStorage` key `chisme-location`), so the app opens straight to it. While the app is open it watches your position (`watchPosition`) and reloads everything when you've moved **more than ~3 km**. It also re-checks every time the app is opened or brought back to the front. To switch places, open **Settings → Location**. It shows the current place ("Using your location: …" / "Showing: …") with **Use my location** and a city/ZIP search. Location errors (denied, no fix) are reported there, never as a pop-up on the home screen.
* **No location? No problem.** If location is denied, unavailable, or the page isn't on HTTPS, Chisme shows **San Antonio, TX** as the default. On first launch the card switches to a **city or ZIP search box**; later, the same search is in Settings. Searches are geocoded through the backend. Pick a result and it's remembered on the device.
* **Weather:** current conditions from the nearest NWS observation station, the next 12 hours, a 7-day forecast and **active NWS alerts for your exact point**. Alerts appear as red banners at the top. Times are shown in the location's own time zone.
* **Outside the U.S.:** the National Weather Service only covers the U.S. and its territories. For other places Chisme says so clearly, and the radar and news keep working.
* **Live rain radar (in Weather):** a **Radar** card right under "Weather now". It's a Leaflet map with a muted grey OpenStreetMap basemap (inverted in dark mode) so the rain colors stand out, RainViewer radar looping through the past ~2 hours of 10-minute frames, a time badge on the map ("8:20 AM CDT · 80 min ago", or "Latest" with a red live dot), zoom buttons, a **Light → Extreme** color legend (RainViewer's "Universal Blue" dBZ scale, the one scheme the free tiles serve), play/pause, back/forward and a slider. The map re-centers by itself when your location changes. Your position is an Apple Maps-style **blue dot** (`#0A84FF`, white ring, soft pulsing halo; the halo holds still with Reduce motion). There's no "You are here" label or red pin anymore.
* **Header (v23):** the app icon's own black "Chisme" speech bubble, with its smooth hand-drawn oval, the curved tail at the bottom-left, the icon's lettering and the confetti inside it. It's centered over a flat black skyline, with Fiesta confetti in the icon's colors around it. The bubble **is the Settings button** (`#settings-btn`, `aria-label="Settings"`), and there's no logo square. In San Antonio / Bexar County (and for the default or an unknown place) the skyline shows the **Tower of the Americas** and the Alamo's curved parapet; elsewhere a generic city skyline is shown. Dark mode uses a teal skyline and a turquoise bubble outline. The header is sized in px, so the Text size setting never reflows it, and below 390 px wide it scales proportionally. The bubble, lettering and inner confetti are vector-traced from `assets/chisme-icon-original.png` by `tools/trace_icon_bubble.py` (→ `tools/icon_bubble.json`; dev-only deps `numpy scipy pillow potracer`). `tools/make_header_art.py` writes the SVG into `index.html` between the `HEADER-ART` markers.
* **Five views, News first:** the app opens on **News** (or the default tab picked in Settings). The black section bar (**📰 News · 🏀 Sports · 🌮 ¿Cuál dieta? · 🌤️ Weather · 🎉 Events**, the same order for swiping and for Settings → Open Chisme to; the five buttons share the width, and on narrow phones the tab text shrinks a little and "¿Cuál dieta?" wraps onto two lines, so all five fit at 320 px even with the largest text size) is `position: fixed` at the top of the screen on every device (including iPhone standalone PWAs: it pads for `safe-area-inset-top`, and the page gets matching top padding, measured live, so nothing hides under it) while the rest of the header scrolls away. **Swipe sideways** anywhere on the page to move News ↔ Sports ↔ Weather ↔ Events ↔ ¿Cuál dieta?: the page follows your finger and snaps. Vertical scrolling is still handled by the browser (`touch-action: pan-y`). Swipes that start on the radar map, the hourly strip, the 7-day forecast strip, the Events chips / food strip, a sports score strip or standings table, or a slider are ignored, so the map still pans normally. Each view remembers its scroll position.
* **Dig deeper on every story:** each story ends with **Read full story · {outlet} ↗** (the article's own link from the feed), **Also reported by** (up to 3 stories on the same topic from *other* outlets, found by matching headlines among the feeds Chisme already fetched), and **🔎 More coverage ↗** (a Google News search for the headline's key words). Chisme never builds or guesses article URLs.
* **Events near you:** upcoming events with the listing's photo (or a clearly labeled "No photo from the listing" placeholder), date/time, venue + address, a small map tile and a **Map & directions** link, **cost** (FREE / price, *only* when the listing says so; otherwise **Check price ↗** linking to the listing), and the **NWS outlook** for that day at the venue's area. Beyond the NWS 7-day window it says "Forecast not available yet." Seasonal exhibits and tours that already started are under **Still going on**.
* **Postales between stories:** after every 4th news story (only between stories) there's a photo of a Texas landmark or local mural. The 13 photos rotate, and the next starting photo is saved on the phone, so each refresh shows different ones. Each card has a large bold caption (subject · city), the artist for murals, and the attribution line (photographer, license link, source link). The photos are optimized WebP files (max 1200 px, ~2 MB total) in `static/art/`, precached by the service worker so they work offline. Swipes and scrolls that start on a photo still work as usual.
* **Event categories:** filter chips at the top of Events: **All · 🎸 Concerts · 🎉 Festivals · 🎓 Free classes** (with counts, choice saved on the phone; the chip row scrolls sideways without switching views). Events are tagged automatically from the title and the source's own categories (Eventbrite's category/format, AllEvents' embedded categories, Visit SA's categories). "Free classes" = classes, talks, lectures and workshops that the listing says are free.
* **🌮 ¿Cuál dieta? (food tab):** its own nav tab, third, between Sports and Weather (was the Food chip in Events; food & drink events still show under Events → All). A witty intro (“Diet? Not today. …”), then **Latest · 🔖 Saved spots (n)** chips, a sideways strip of **local San Antonio creators' latest videos** (thumbnail, creator, date), and at the bottom **From the food desks**: at most 5 compact text rows from SA Current, Express-News and MySA (taken in turn from each desk, newest first). Everything is from public feeds or the hand-picked TikTok list; reviews are the creators' own and titles are shown as published. Cached for offline like the rest. `/#cual-dieta`, `/#dieta`, `/#antojos` and the old `/#food` all open it, and Settings → **Open Chisme to** has a **🌮 ¿Cuál dieta?** option.
* **In-app player and reader:** tapping a food video (card, thumbnail, title or ▶ Watch) opens a bottom sheet that plays it inside Chisme with YouTube's privacy-enhanced embed (`youtube-nocookie.com/embed/ID?playsinline=1&rel=0&modestbranding=1&autoplay=1`; Shorts get a tall 9:16 frame), with the restaurant name/address when known, 🔖 Save, **Directions** and **Close** (or swipe the sheet down). Closing stops the video. TikToks play in **TikTok's official embed player** (`tiktok.com/player/v1/ID`). Offline, the sheet says the video will play when you're back online. Food-desk stories open in a reader sheet: SA Current allows framing, so the article shows inside a sandboxed iframe; Express-News and MySA links go through Google News, which refuses framing, so the sheet shows the headline plus a clearly labeled **Open article ↗** (opens the browser). The server checks `X-Frame-Options` / CSP `frame-ancestors` once per site every 12 h. Spurs YouTube clips on Sports play in the same sheet (without Save). No link to a video opens a new tab.
* **For You (v25):** the top of ¿Cuál dieta? is a **🌮 Tu feed de antojos** card (v40: renamed **🌮 Bigger the Pansa, Better the Chansa**) ("it learns what you crave") with a big **▶ Start watching** button. It opens a full-screen, TikTok/Reels-style **vertical feed**: one video per screen, CSS scroll-snap (`y mandatory`, one snap stop per video), swipe up/down (or ↑/↓, j/k). The video on screen plays in the official player (YouTube's privacy-enhanced embed or TikTok's embed player) **muted and inline, automatically**, when that's allowed; with Reduce motion, Save-Data or offline it shows the thumbnail and **▶ Tap to play**. Only one player exists at a time (the one you left is removed, which stops it); its thumbnail stays up with a spinner until the player reports that it's playing. A transparent layer over the video takes the touches, so a swipe on the video scrolls the feed and a tap pauses/plays (commands go to the player by `postMessage`); **🔇 Muted / 🔊 Sound on** at the top. Overlaid on each video: the **Why you're seeing this** chip, the title, creator · platform · date, 📍 restaurant + address, and a side rail with **🔖 Save**, **📍 Directions** (Apple Maps), **🙅 Not for me** (with Undo) and **⤢ Details** (the full player sheet). **‹ Back**, Esc, or the phone's back gesture/button closes it (a history entry is pushed while it's open) and returns to the tab.
* **The ranking runs on the phone** (`static/foryou.js`, localStorage key `chisme-foryou`, no server calls, no account). Each video's features: **creator**, **dish/cuisine** keywords from the title (tacos, birria, BBQ, mariscos, desserts, breakfast, burgers, pizza, Italian, Mexican, Caribbean, Asian, steak, soup, coffee, snacks, drinks, wings, food events), **neighborhood** (names like Stone Oak or Southtown, or a ZIP → area table for San Antonio) and **price hints** (cheap eats vs. a splurge). Signals: open/watch **+1**, watch time up to **+1.5 more** at 30 s, **save +3**, unsave −2, **skip-fast** (< 2 s) −0.6, **Not interested −4** and hidden. Weights fade with a **14-day half-life**; score = interest + freshness (10-day half-life) − repeats − already saved. **Variety comes first** (many creators, many different places): videos about the **same restaurant are deduped** (one stays; "Losoya’s Taqueria", "LOSOYAS TAQUERIA" and a title that names it all match), never the same creator or restaurant twice in a row, no restaurant twice in the top 15, and **at most 2 videos per creator in the top 10**. A creator is a person, not a channel (the server sends `crew`: Texas Eats and Elder Eats are both David Elder). On a **new phone the feed round-robins across creators**, so the first 9 videos are 9 different people; once it has learned, the first 5 are 5 different creators. The lead creator **rotates** every visit and every time you close the feed (the one who led last time never leads again), and the banner shows a **3-video cover** ("Up next: …") from the same ranked list, so the cover and the first videos always match. If a tiny feed can't meet every rule, they relax in order instead of dropping videos. **Every 5th card (~20%) is exploration**: something from the third of the feed this phone knows least, labeled "Something different: …". The order is stable for the day. The chip explains each pick ("Because you saved 2 taco spots", "Because you watch Eatmigos", "Near spots you saved in Stone Oak", "Fresh this week"); tap it for how it works. The banner shows what it has learned ("Tuned to you: taco, …"). **Settings → For You feed → Reset my feed** clears it. Tests: `foryou_rank_test.py` (Node), `foryou_ui_test.py` (WebKit iPhone 13 + a real touch swipe in Chromium).
* **Creators we follow:** a card per creator (`data/food_creators.json`) under the video strip, with YouTube / TikTok / Instagram profile links (they open in Chisme's reader, with a small link to the original) and what Chisme pulls in automatically. Instagram-only creators (S.A. Foodie) get an "Instagram only" link card: Instagram has no keyless feed or embed.
* **Curated TikToks:** TikTok has no public RSS and no keyless listing API, so Chisme shows only TikTok videos listed in `data/food_tiktok.json` (`creators` with verified handles, `videos` with `https://www.tiktok.com/@handle/video/ID` links). The server looks each link up with TikTok's official oEmbed (`https://www.tiktok.com/oembed?url=…`: caption, thumbnail, author; cached 12 h), keeps only videos whose author is a listed creator, and dates them from the video ID. Edits are picked up on the next food refresh (no restart). These hand-picked videos skip the 60-day cutoff. Nothing is scraped.
* **Fresher news, no jumping (v26):** while Chisme is open and on screen it checks for new stories every **4 minutes**, and right away when you come back to it (focus / visible again, if the last check is over a minute old). The server's per-feed cache is 4 minutes. If new stories arrive while you're reading, the list doesn't move: a **New chisme ↑** pill appears under the tabs (News tab only); tap it to show them and jump to the top. A check with nothing new only updates the time. Pull to refresh / Settings → Refresh now show new stories right away.
* **Alerts (Web Push, v26):** opt-in only. **Settings → Alerts → Turn on alerts 🔔** (and a one-time inline "Want a heads-up…?" card on your second visit, never a popup; "Not now" hides it for good). The permission prompt only ever comes from that tap, as iOS requires. Two switches: **Breaking & new local news** and **NWS weather warnings & watches for your location**. A new story arrives as **"New chisme, grab the tea! ☕"** with the headline as the text; tapping it opens Chisme with the story in the in-app reader. Weather arrives as **"⚠️ Tornado Warning"** (the alert type) with the NWS headline; tapping opens Weather → alerts. At most **one news alert per 45 minutes**, only stories from the last 3 hours; **quiet hours 10 PM – 7 AM** in the phone's time zone (news and watches wait, warnings still come through); each alert once; the first check after you subscribe only records what's already out there. "Send a test" sends a sample. Works on Android/desktop browsers and on **iPhone/iPad in the Home Screen app (iOS 16.4+)**; in Safari on iPhone, Settings explains how to add it to the Home Screen. Server side: `push.py` (pywebpush + VAPID), see **Alerts setup** under Deploy.
* **Everything opens inside Chisme (v27):** every outside link (Read full story, Also reported by, More coverage, event
  pages, organizer sites, Gamecast/Gameday, ESPN/Reddit lists, creator profiles on YouTube/TikTok/Instagram, photo and
  radar credits) opens the **in-app reader sheet**. The server checks the page's own `X-Frame-Options` and
  `Content-Security-Policy: frame-ancestors` (`GET /api/reader`, cached 6 h per link and 12 h per site; private
  addresses, odd ports and non-web links are refused) and, where the site allows it, shows the page in a sandboxed
  iframe that can't navigate Chisme. Otherwise the sheet is a card: headline, source, date, the feed's summary (or the
  site's own short description, at most 300 characters), the image, and a map for events. The article text is never
  copied, attribution stays on every card, and a small secondary **Open original ↗** link sits at the very bottom.
  Map links (event maps, "Map & directions", food **Directions**) open an in-app OpenStreetMap **map sheet** with a
  pin and a small **Open in Maps ↗** (Apple Maps directions). The only primary button that leaves the app is **Donate on
  Cash App**. Long-press or ⌘/Ctrl-click still gives you the real link.
* **Tía Chismosa (v28):** a chat mascot, a tía chismosa (floating avatar, bottom right). She greets you by the time of day, gives you a daily chisme del día top 3 ranked on the phone from your interests, and chats about the app's current stories, weather, events, sports and food, grounded only in those feeds with citations that open in the in-app reader. Uses Gemini's free tier if `GEMINI_API_KEY` is set, and scripted lines otherwise. See **Tía Chismosa** below.
* **News order (v29):** if you check often and nothing is new, News looks different each visit, and it's all worked out on the phone. `static/newsorder.js` keeps `chisme-news-seen` in localStorage: which stories this phone has shown, seen on screen and opened, and when. On a new visit (opened after 10+ minutes away, or a manual refresh) stories you haven't opened or have seen less move up, the lead rotates among the top 3, the rest get a light seeded shuffle that keeps roughly the server's recency/importance order, and outlets are mixed so none clumps. New stories (the "New chisme" pill still works), breaking/urgent headlines and NWS warnings stay pinned on top. The order is stable within a visit. Settings → Reset my feed and Forget me clear it. Headlines and summaries are never changed.
* **Donate on every tab (v32):** the Cash App card ($Slurmkaos, "The tea ain’t free!…") is the last thing on every tab: News, Sports, Weather, ¿Cuál dieta?, Juegos and Events, plus the one already in Settings. Once per launch there's also one inline card, not a pop-up, in the middle of the tab Chisme opened on (after about the 5th story/event/item; between the radar and the forecast on Weather). It reads "Enjoying the chisme? ☕ Donate for more (and better) chisme!" with the Cash App button and a ✕. Switching tabs never adds another, and ✕ hides it for the rest of the session (sessionStorage `chisme-donate-mid-x`).
* **Tab order (v31):** News · Sports · Weather · ¿Cuál dieta? · 🎲 Juegos · Events, the same in the tab bar, swipe, ←/→ on the tabs, and Settings → default tab.
* **🎲 Juegos (v30):** a sixth tab (between ¿Cuál dieta? and Events since v31, also a Settings default-tab choice; `#juegos`, `#loteria`, `#ice` deep links) with a list of games that run entirely on the phone. They work offline (precached by the service worker), have no links and make no requests, and honor reduce motion. Add a game by pushing `{ id, name, emoji, blurb, mount(el, ctx) }` onto `ChismeJuegos.GAMES` (`static/juegos.js`).
  * **Lotería Chismosa** (`static/juegos.js`): an original chisme-style lotería with 40 cards of our own (in English since v39: The Coffee, The Best Friend, The Rollers, The Phone, The Neighbor, The Gossip, The Flip-Flop, The Sweet Bread … The Gossip Queen). The art is emoji plus two small SVGs in Fiesta colors; none of the traditional card names (Spanish or English) or art are used. You get a random 4×4 board. Tía Chismosa (her avatar) calls a card every few seconds with a short line, out loud in English via speechSynthesis when the phone has a voice, saying only the word "Lotería" with a Spanish voice (🔇 Voice mutes her). Tap a card to put a marker on it. There's ⏸ Pause, 🐢 Slow/🚶 Normal/🐇 Fast and 🔀 New board. **¡Lotería!** checks for a row, column, diagonal or the 4 corners (only cards she actually called count), then shows confetti and a brag. Wins, streak and best streak are kept in `chisme-juegos`.
  * **Ice Ice Bebé** (`static/icebebe.js`): an original 8-bit side-scrolling runner on a canvas, with no image files. A cheerful Tejano in a sombrero runs home across 5 San Antonio stops: Home Dehole (a parody big-box store: a beige building with a plain orange banner, no logo), The Taco Shop, The Corner Store, The Plaza, then Mom's House, where the family party celebrates. Tap, the Jump button, Space or ↑ jumps; tap again in the air to double-jump. He hops traffic cones and gets past generic, faceless agents in plain vests (no logos, badges or weapons) and their unmarked SUVs. The agents are slapstick: they trip on cones and get dizzy. Nobody gets hurt: if he's caught, a random big pixel "¡Ay no!", "¡Fuera!" or "¡Vámonos, amigo!" shows (those three catch lines stay in Spanish; everything else is English since v39) and he goes back to the last 🚩 checkpoint. ☕ Coffee gives a speed boost and 🩴 Flip-flop is a shield (the agent just gets confused). There are square-wave chiptune beeps (🔇 mute), a score, and a best score in `chisme-juegos-ice`. Reduce motion turns off parallax, shake and confetti, and runs a bit gentler.
* **Share Chisme (v28):** a small 📤 **Share Chisme** pill in the footer. On phones it opens the system share sheet (Web Share API) with the title "Chisme", "Pull up a chair, grab the tea ☕ Local chisme, weather, food & events:" and https://chisme.onrender.com/. Where that isn't available it copies the link and shows a "Link copied!" toast. It never opens another page.
* **Donate:** a small card at the very bottom of News and of ¿Cuál dieta?, and a **Support Chisme** row in Settings: "The tea ain’t free! Help a chismoso out — donate now!", a Cash App-green **💸 Donate on Cash App** button (black text, 10.7:1 contrast; works in dark mode) and **$Slurmkaos** under it. It links to `https://cash.app/$Slurmkaos` in a new tab: the one link that deliberately leaves the app. Never between stories, no popups.
* **Saved spots (Food):** every food review and video card has a 🔖 **Save** toggle. Saved items live on the phone in `localStorage` (`chisme-food-saved`: title, link, thumbnail URL, source, date and restaurant name/address when known), so they survive feed refreshes and show up offline. The **Latest · 🔖 Saved spots (n)** chips at the top of the Food section switch to the saved list, where you can reopen the video, **Remove** it (with Undo), and **Add/Edit place**. When a restaurant name or address is known, a **Directions** button opens Apple Maps (`maps.apple.com/?daddr=…`). The server guesses the place from creator video titles (a street address like "4445 Walzem Road San Antonio, TX 78218", or "… at Alzer's Roastery" / "… - Picnikins"). Guesses are labelled "(from the title)" and can be edited. Offline, thumbnails come from the browser cache when it still has them; otherwise the usual "offline" placeholder shows. Test: `food_saved_test.py`.
* **Personality:** a time-of-day greeting at the top of News: "¡Buenos días, chismosos!" (5 AM–noon), "¡Buenas tardes, chismosos!" (noon–6 PM), "¡Buenas noches, chismosos!" (6 PM–5 AM), in the place's time zone, with "Pull up a chair, grab the tea, here’s the latest chisme." under it and, until your first swipe, a short hint ("Swipe 👈 for more · pull to refresh · tap the bubble for settings.", ≤ 2 lines even at 320 px). It's plural for everyone: the old chismoso/chismosa switch (home card and Settings) is gone in v24, and its saved `chisme-greeting-word` key is ignored and cleared. Test: `greeting_test.py`. Also weather blurbs ("Rain's in the chisme today — bring the paraguas"), and playful loading, empty and error states. When NWS alerts are active, the weather blurb turns serious. **News headlines and summaries are shown exactly as the publisher wrote them**, with no jokes or rewording next to them.
* **Local news, ranked by distance:** **Near You** lists stories that name your neighborhood or nearby neighborhoods first, then your city, then your county. Each story has tags like `South San` or `Downtown` / `Austin`. The rest of your city's news goes under **More {city} news**. When you're outside San Antonio, a collapsible **San Antonio headlines** section keeps the SA newsrooms handy.
* **Auto-refresh:** weather + radar every 10 min, sports every 5 min, news every 15 min, events every 30 min, and when you return to the app if the data is stale.
* **Installable and offline:** manifest, icon set and service worker. The **last location's** news, weather and events are saved on the phone and shown with an "offline, saved copy" banner when there's no signal.
* **Sports:** chips for **🏀 NBA · Spurs** (the default; outside SA it's your nearest NBA team, e.g. **NBA · Rockets**), **🏈 NFL**, **⚾ MLB** and **⚾ Missions** (your local Minor League club, hidden if there's none nearby). The choice is saved on the device. Each league has a witty one-line intro; the reporting itself is straight. **Spurs:** a season summary card (record, conference rank, how the season ended, next game), a latest-scores strip, the upcoming schedule (preseason tagged), **Western Conference standings** with the Spurs highlighted, Spurs news, **Trending in Spurs Nation** (the Spurs' YouTube channel and Pounding The Rock, plus a link to r/NBASpurs) and "Around the NBA". **NFL / MLB:** a sideways score strip (Texas teams first, with Gamecast/Gameday links) and league news. **Missions** (Double-A, Texas League): season summary, recent games, Texas League South standings and news. Scores refresh every 5 minutes. **Photos:** news items show only the thumbnail ESPN publishes with its own story, linking to that story. Team photos are freely licensed Wikimedia Commons photos (arena, stadium, game scenes; credited on the card). No team logos or press photos. Works offline from the saved copy. Deep links: `/#sports`, `/#spurs`, `/#nfl`, `/#mlb`, `/#missions`.
* **Settings (tap the Chisme bubble in the header):** a bottom sheet with **Appearance**: System / Light / Dark. Dark mode is near-black with white text and the turquoise accents, and passes the contrast check. It also has **Text size** (A−/A+, moved here from the home screen), **Location** (use my location, or enter a city or ZIP), **chismoso / chismosa**, **Open on** (default tab), **Reduce motion** (no swipe or scroll animations, radar doesn't autoplay, and the location halo holds still; also on automatically when the phone asks for reduced motion), and **Refresh now** with the last-updated time. Everything is saved in `localStorage` (`chisme-theme`, `chisme-font`, `chisme-reduce-motion`, `chisme-default-tab`, `chisme-location`). Theme, text size and motion are applied before the first paint, so there's no flash.
- **v33 — mid-list donate card on every 5th open:** a launch counter in localStorage (`chisme-opens`) shows the inline card only on opens 5, 10, 15 …, each time with a different line from 24 Chisme-voice lines in `static/donatelines.js`, never one of the last 5 shown (`chisme-donate-recent`). Cash App button and ✕ (session dismiss) kept; the bottom-of-tab donate cards are unchanged. Tests: `donate_every_tab_test.py` (Node picker + WebKit), `donate_alerts_test.py`.
- **v34 — the jokey mid-list donate card stays away from serious stories:** before placing it, the stories right before and after the chosen spot are checked (`ChismeDonate.serious`: dies, death, killed, crash, shooting, stabbing, murder, missing, abuse, fire, victim, fatal, arrested, charged and similar, plus urgent/breaking titles and NWS warnings). If either looks serious it moves to the nearest slot with two light neighbors (`ChismeDonate.slot`, a tie goes to the later slot), else to the end of the tab just above the bottom donate card. It re-checks whenever the list re-renders. Tests: `donate_every_tab_test.py`.
- **v35 — new Tía Chismosa art:** rebuilt from `tia-chismosa-v2.jpg` (1280×720) with `tools/make_mascot_assets.py --face 665,215,370 --header 0,20,1280` (the tool now takes a `--header X,Y,W` box, saved in `static/mascot/mascot.json`). Round avatar = a face crop (floating button, chat bubbles, Lotería's caller); the chat header is framed to show her glowing phone and her, with the name label moved bottom-right so the phone shows. Her image URLs carry `?art=2` (index.html, app.js, juegos.js, sw.js) so phones drop the old art; bump it on the next swap.
- **v36 — no yellow in News:** Near You story cards lost their cream/amber background (light `#fff0e0`, dark `#2b1e0e`); they're a plain card with a subtle turquoise edge now, in both themes. No yellow new/unread/lead/mark highlights anywhere in News. Test: `news_no_yellow_test.py` (scans every News element's background, gradients, glows and headline colors in light + dark).
- **v37 — no yellow anywhere, light or dark:** yellow/gold/cream highlights and backgrounds replaced with the Fiesta palette on neutral backgrounds. Pink keyboard focus ring (`--focus`); offline banner = neutral card with an orange edge; Sports standings "us" row = turquoise tint (`--near`); For You kicker/why-chips = light turquoise; Tía's safety bubble = pink edge; Lotería's winning row = turquoise + pink ring and the ¡Lotería! button turns turquoise on a win (orange card tints a bit stronger so they read orange, not cream); Ice Ice Bebé: turquoise level titles/HUD/sign lettering, pink caught text and "!?", orange boost bar, white road stripes, silver confetti/papel picado, turquoise lit windows, pink/orange skies instead of cream, warmer straw sombrero and Home Dehole beige, and whole-pixel parallax so no edges blend into khaki. Radar: RainViewer only serves "Universal Blue" (moderate rain = yellow), so tiles are recolored on a canvas (yellow → orange, amber → deep orange) and the legend matches. Test: `news_no_yellow_test.py` (now app-wide: every tab, Settings, Tía's chat UI, pills/toasts/banner, focus ring, radar legend + tiles, Lotería win, Ice Ice Bebé DOM + canvas pixels, light + dark). Tía's art unchanged.
- **v40 — Tía speaks English first:** Tex-Mex Spanglish, never full Spanish. The Gemini prompt's rule 7 now says: always reply in English with 1-3 Spanish words or short phrases (mija, ay, fíjate, qué chisme, órale, ándale, comadre), never whole Spanish sentences; even when the user writes in Spanish, at least three quarters stays English; serious news stays plain English with no flourishes. A closing reminder repeats it. If the model still answers in Spanish (`lang_mix()` counts Spanish vs English function words), she asks it once to say it again in English, else uses the English smart answer. Smart (no-AI) answers and greetings are English with sprinkles, and understand Spanish questions ("¿cómo van los Spurs?", "¿qué tiempo hace?", "¿hay eventos este fin de semana?"). Lotería's voice stays English. Tests: `mascot_test.py` (screenshot `tia-spanglish.png`).
- **v40 — full-screen games, 🎲 Juegitos, and the food feed's new name:** the Juegos tab is now **🎲 Juegitos** (tab bar, heading, Settings → default tab, aria labels; the view id and `#juegos` links stay, `#juegitos` works too). **Lotería Chismosa** and **Ice Ice Bebé** play **full screen in portrait** (`ChismeJuegos.fullscreen()` in `static/juegos.js`): a fixed overlay (100dvh + safe-area insets) with the tab bar, footer and Tía's button hidden, a title badge at the top center (Lotería: a pink 🎴 "Lotería Chismosa" pill; Ice: a pixel-art "ICE ICE BEBÉ" badge in Fiesta colors) and a **✕** at the top right (or Escape) that stops the calling / pauses the run and goes back to the Juegitos list. It works on iPhone Safari and the home-screen app with the overlay alone; the Fullscreen API is only tried on touch phones that have it. Leaving the tab also drops full screen. Lotería's board, the called card and the controls fill the tall screen (the board sizes itself to the space left). Ice Ice Bebé now has a tall portrait canvas (156 px wide, 220–340 tall to match the screen) with richer 8-bit art per level: sky gradients, sun / moon and stars, drifting clouds, grackles, a far skyline with a generic observation tower and dome, mid-rise blocks with a water tower, palms and a plain-words billboard, storefronts with striped awnings and signs (TACOS, BAKERY, LAUNDRY…), little houses on Mom's street, sidewalk props (lamp posts, hydrants, benches, news boxes), a street with a passing lowrider and a talavera-tile wall. More animation frames (4-step run with arm swing and bounce, jump/fall poses, a cheer, 4-step agent walk, kicking when tripped, stars when dizzy, spinning conchas, waving flags, coffee steam), dust and sparkle particles, and a two-row HUD (level, score, progress with checkpoints, ☕/🩴 power-up slots, best). The faceless slapstick agents, the three Spanish catch lines, the power-ups and Home Dehole (beige, orange sign, white letters) are unchanged. Reduce motion: no parallax, shake, particles or confetti. **¿Cuál dieta?'s feed is renamed "Bigger the Pansa, Better the Chansa"** (was "For You" / "Tu feed de antojos"): the banner title, the feed's top bar and aria label, the why-chip note, and Settings. It wraps evenly on phones; at 360 px or narrower the name gets its own row under ‹ Back / 🔇 Muted. Screens: `screenshots/icebebe-fullscreen.png`, `icebebe-level2.png`, `loteria-fullscreen.png` (390×844), `food-panza.png`.
- **v39 — English games, city-only greetings, no "holographic":** Tía's chat subtitle is now "your comadre · an AI" and her greeting "Tía Chismosa here, your comadre." (the word "holographic" is gone everywhere, including her AI prompt). Greetings and chatty lines (Tía's weather line and chat context, the Events/concerts intros, the loading quips) name only the city via `greetCity()` (e.g. "San Antonio", never "Port San Antonio (Kelly), San Antonio"; "Houston", not "Montrose, Houston"); Settings, NWS-alert and push lines keep the full place label. All of 🎲 Juegos is English (cards, call lines, buttons, rules, win/lose lines, Ice Ice Bebé's levels, signs, hints and pop-ups) except "Lotería" (game name and the ¡Lotería! shout) and Ice Ice Bebé's title and its catch lines "¡Ay no!", "¡Fuera!", "¡Vámonos, amigo!". Tía's voice is English (en-US), switching to a Spanish voice only for "Lotería" (`ChismeJuegos.voicePartsOf`). **Smarter Tía:** no status strip in her header; the server gives her every current feed (all news sections, ESPN scores/schedule/standings, weather, events, food) and `smart()` answers "Spurs score", "did the Spurs win", weather, "events this weekend" and story lookups without AI (fuzzy matching, in-app links, chips show game status / when · venue · price); with `GEMINI_API_KEY` (`AQ.` auth keys work, sent as `x-goog-api-key`) the model gets the full context + retrieval and keeps the citations. New Tía art (the same tía with a sly smirk, phone on the left): all mascot assets rebuilt from `tia-chismosa-v3.jpg` (1280×720) with `tools/make_mascot_assets.py --face 650,235,380 --header 0,60,1280` (the header shows her phone and her), cache-bust `?art=3`. Tests: `juegos_test.py`, `mascot_test.py`.
- **v38 — ☕ Buy Me a Coffee:** a second donate button, **☕ Buy Me a Coffee** → https://buymeacoffee.com/Chismoso, next to 💸 Cash App in every donate card (the 6 tab bottoms, the mid-list card and Settings), in a wrapping `.donate-btns` row with room for a future Venmo button. Fiesta orange with black text (never BMC yellow), orange-edged in dark mode. Like Cash App it opens outside Chisme: the in-app reader skips `.donate-btn` links and any link to `DIRECT_HOSTS` (cash.app, buymeacoffee.com; add venmo.com with the Venmo button). Tests: `donate_every_tab_test.py`, `inapp_reader_test.py`, `donate_alerts_test.py`, `news_no_yellow_test.py`.

No API keys are needed. All data is live, with nothing made up.

> **Geolocation needs a secure page.** Browsers only allow `navigator.geolocation` on **HTTPS** or **`http://localhost`**. If you open Chisme from another device on your Wi-Fi (e.g. `http://192.168.1.20:8211`), the browser blocks location. Chisme notices this, explains it, and offers the city/ZIP search instead. Deploy behind HTTPS (Render, Fly and Caddy do this automatically) to get live location on a phone.

## Run locally

```bash
cd chisme
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn app:app --host 0.0.0.0 --port 8211
# open http://localhost:8211
```

Or run `./run.sh [port]`. It creates the venv if needed, (re)starts the server in the background, and writes `server.pid` and `server.log`.

| env var | default | purpose |
| --- | --- | --- |
| `PORT` | 8211 | port for `python app.py` / `run.sh` (hosts like Render/Fly set it for you) |
| `APP_USER_AGENT` | `Chisme/1.0 (...)` | User-Agent sent to api.weather.gov, Nominatim and the feeds. **NWS and Nominatim both ask for contact info**, e.g. `Chisme/1.0 (you@example.com)` |
| `NOMINATIM_URL` | `https://nominatim.openstreetmap.org` | geocoder base URL. Point it at your own Nominatim (or a hosted one) for heavier use |

## Install Chisme on your phone

Installing (and live location) need **HTTPS**, so deploy it first (see [Deploy](#deploy)). Render and Fly both give you an `https://…` address automatically. (`http://localhost` counts as secure for testing on a computer, but a phone on your Wi-Fi hitting `http://192.168.x.x:8211` won't be allowed to install.)

**iPhone / iPad (Safari):**
1. Open your Chisme address (e.g. `https://chisme.onrender.com`) in **Safari**.
2. Tap the **Share** button (square with an arrow ↑) at the bottom of the screen.
3. Scroll down and tap **Add to Home Screen**, then **Add**.
4. Open Chisme from the turquoise icon. It runs full-screen like an app.

The app shows a short reminder card on iPhone with these steps. Tap ✕ to hide it.

**Android (Chrome):**
1. Open your Chisme address in **Chrome**.
2. Tap the orange **Install** button in the "Get the Chisme app" card (on bigger screens it's in the header). You can also use Chrome's menu ⋮ → **Install app** / **Add to Home screen**.
3. Confirm. Chisme shows up in your app drawer and on your home screen.

**Desktop Chrome/Edge:** click **📲 Install** in the header, or the install icon in the address bar.

**Offline:** once you've opened Chisme with a connection, the service worker keeps the app itself plus the latest news, sports, weather and events **for the last location you viewed**. With no signal you'll see that saved copy and a yellow "You're offline" banner. The radar needs a live connection.

**Sleeping server (Render free plan):** the app opens from the phone's saved copy right away. A small pill under the section buttons says **"Updating…"**. If the server is still waking up (up to ~50 s), after 8 s it changes to "Waking up the server — this can take up to a minute". When the fresh data arrives it says **"✓ Updated 8:45 AM"**. If an update fails, the stories stay on screen and it retries automatically (5 s, 15 s, 30 s, 1 min, 2 min, then every 5 min), again when you come back to the app or reconnect, or right away with **Retry now**. **Pull down** at the top of any section to refresh by hand.

## How it works

`app.py` is a small FastAPI server. It exists because RSS feeds block browser CORS, because browsers can't set the `User-Agent` header that NWS and Nominatim require, and so geocoding can be cached and rate-limited in one place. Every data endpoint takes `lat` and `lon`. Caches are keyed by a **rounded grid cell** (0.01°, about 1 km), so nearby users and small GPS jitter share cached results.

| endpoint | what | server cache |
| --- | --- | --- |
| `GET /` | the single-page app (`static/index.html`, `app.js`, `style.css`; Leaflet is bundled in `static/vendor`) | – |
| `GET /manifest.webmanifest` | PWA manifest (name, turquoise theme `#00C9CD`, icons, screenshots, shortcuts) | – |
| `GET /sw.js` | service worker, served from the root so it covers the whole site | – |
| `GET /api/place?lat&lon` | reverse geocode (Nominatim `/reverse`, zoom 16; falls back to Photon, then NWS — see below). Returns `label` ("South San, San Antonio"), neighborhood, city, county, state, country, ZIP and a list of **nearby neighborhoods** with distances | 7 days per cell |
| `GET /api/geocode?q=` | city/ZIP search for the manual fallback. A 5-digit ZIP is looked up as a U.S. postal code; anything else is a free-text search. Up to 5 results | 30 days |
| `GET /api/weather?lat&lon` | NWS `/points/{lat},{lon}` (per cell, 24 h) → forecast + hourly (per NWS grid), latest observation (nearest station, with fallback), `/alerts/active?point=…` (per cell). Outside NWS coverage it returns `supported:false` and a message | 5 min, alerts 3 min |
| `GET /api/news?lat&lon` | builds the feed list for the place (below), fetches it in parallel, cleans it up, drops near-duplicate headlines, and ranks it | 10 min per feed |
| `GET /api/radar` | RainViewer `weather-maps.json` (list of frames) | 2 min |
| `GET /api/sports` | NFL, NBA (Spurs-heavy), MLB and San Antonio Missions: scores, schedule, standings and news in one payload (~70 KB). Every source is fetched in parallel, a failing one is listed as unavailable, and the rest still show | 3 min (stale copy up to 6 h served while it rebuilds); scoreboards 2 min (MLB 90 s), news 15 min, schedules 10 min, standings 30 min |
| `GET /api/events?lat&lon` | upcoming events within 45 km / 45 days: merged, de-duplicated across sources, with price (when stated), venue, coordinates and the NWS outlook per event day. Details (Visit SA venue/photo/admission, Eventbrite prices) are fetched politely in the background, and the response's `pending` count tells the page to re-check | lists 30 min, details 24 h, outlook 30 min |
| `GET /healthz` | health check | – |

If an upstream request fails, the server keeps serving the last good copy. News, events and food are also **stale-while-revalidate**: an expired copy (news up to 6 h old, events/food 1 h) is returned immediately while a fresh one is built in the background, so a request never waits on slow feeds when there's anything to show. Static files are sent with `Cache-Control: no-cache` (JS/CSS/JSON revalidate via ETag, images cache for a day) and API responses with `no-store`; every response carries `X-Chisme: 1` so the service worker never saves a hosting "waking up" page. A feed that fails is skipped and listed as unavailable under "News sources" at the bottom of the page.

**Geocoding (Nominatim / OpenStreetMap):** requests follow the [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/). They send an identifying `User-Agent`, are serialized to **at most 1 request per second**, and every result is cached. **Fallbacks:** Nominatim blocks busy shared IPs (Render's free-plan egress got `429 Too Many Requests`, which made `/api/news` fail with HTTP 502). Now a 403/429/503 from Nominatim pauses it for 15 minutes and reverse lookups go to [Photon](https://photon.komoot.io) (komoot's OSM geocoder), then to the NWS `/points` "relative location" (U.S.), and finally to a plain coordinate label, so news never fails because of geocoding. Searches fall back to Photon, and ZIPs to [Zippopotam.us](https://api.zippopotam.us). Places found through a fallback are cached for 15 minutes instead of 7 days. Place data © OpenStreetMap contributors (ODbL). The neighborhood list comes from the reverse-geocode result plus a few extra reverse lookups around the point. San Antonio's neighborhoods aren't mapped as areas in OSM, so `data/sa_neighborhoods.json` adds a small gazetteer of **40 SA neighborhoods/landmarks** (Harlandale, Palm Heights, Nogalitos, Port San Antonio, Southtown, Alamo Heights, …). Any within 5 km count as "nearby". It was built with `tools/build_sa_gazetteer.py`.

**News ranking ("Near You"):**
1. **Neighborhood tier:** the headline or summary names your neighborhood or a nearby one (closest first), or your ZIP. Common names like "Downtown" or "Midtown" only count if the city is also named. Within the SA newsrooms' feeds, the city is implied when you're in San Antonio.
2. **City tier:** names your city (e.g. "Austin", but not "Austin College").
3. **County tier:** names your county.

Near You shows up to 18 neighborhood stories, filled with city/county stories up to 30, newest first within each tier. **South Side boost:** only when you're on San Antonio's South Side, the classic South Side word list (South Side, South San, Harlandale, Palm Heights, Nogalitos, Zarzamora, SW Military, Kelly Field, Port San Antonio, Southcross, Pleasanton Rd, Palo Alto College, South Park Mall, …) also counts as neighborhood tier, and two extra South Side searches are added.

**Service worker (`static/sw.js`):**
* **Pre-caches the app shell** (page, CSS, JS, Leaflet, icons, art photos) with `cache: "reload"`, so a new version never precaches a stale HTTP-cached file. Only responses marked `X-Chisme: 1` are saved.
* **Pages open from the cached shell instantly** (no waiting on a sleeping server). Shell files come from the current version's cache, so HTML, JS and CSS always match. Other static files use stale-while-revalidate.
* `/api/*` is **network-first with no short timeout**. A sleeping Render instance can take ~50 s, and the old 10 s cutoff threw the late answer away and showed "You're offline". The page reads the saved copy itself and shows it at once, and the network answer replaces it when it arrives. The SW falls back to the saved copy (for that exact location, or else the **last location's**, marked `X-Chisme-Offline`) only when the network actually fails. Geocode searches aren't cached.
* **Updates:** registered with `updateViaCache: "none"`, and checked again whenever the app comes back to the foreground (at most once a minute). When a new worker takes over it tells the open page its version (`postMessage`). A page from another build **reloads itself once**. If you're typing or have Settings open, it shows "✨ Chisme was updated · Reload" instead and reloads the next time you reopen the app. `WindowClient.navigate()` isn't used, because WebKit can leave that navigation hanging.
* **HTML and JS always match (build number):** the build is defined once, in `VERSION` in `sw.js` (`chisme-v22` → build 22). The server writes it into `index.html`, which loads `/static/app.js?v=22` and `/static/style.css?v=22`, and the worker precaches exactly those URLs and matches the query. So an **older service worker's cached `app.js` can never run with a newer page**. `app.js` also carries its own build (`window.CHISME_APP_BUILD`, which must match `VERSION`; `upgrade_test.py` checks this). A guard at the end of `index.html` reloads once if the two differ or the app crashed while starting. If that doesn't help, it shows "Chisme didn't start properly · Reload Chisme", which clears old caches, instead of blank views.
* **What went wrong with v15 → v21 (fixed in v22):** the v15 worker fetched the page from the network but served `/static/app.js` and `style.css` from its old cache. After the v21 deploy, iPhones got the new HTML (with a Sports tab) running the **old v15 app.js**. The old script didn't know "sports", so the tab did nothing. Its view list was News/Weather/Events, so **Weather** slid to the new (empty) second pane and looked blank. The old CSS gave the new logo `<button>` a white rounded background (the "white circle"). An iPhone home-screen app often resumes instead of reloading, so the broken page could stick around.
* Cross-origin requests (map/radar tiles, news thumbnails, NWS icons) always go to the network.
* When you change front-end files, bump `VERSION` in `sw.js` so phones pick up the update.

**Page loading:** each section (news, weather, events, food) first shows the saved copy for your location ("Saved copy from 8:40 AM"), then refreshes without clearing the screen. Requests time out after 75 s (long enough for a Render wake-up plus a cold news build). Failures retry with backoff. **Geolocation never blocks anything:** data loads for the saved (or default San Antonio) location first. Chisme keeps its own 12 s timer on `getCurrentPosition`, because iOS home-screen apps can leave it hanging, and it doesn't re-ask more than once every 5 minutes.

### App icon

Icons are built from the chosen artwork, `assets/chisme-icon-original.png`: a turquoise rounded square with a black "Chisme" speech bubble and pink/orange confetti. `tools/make_icons.py` fills the white outside the rounded corners with the icon's own turquoise (sampled from the artwork: `#00C9CD`), so there's no white rim. It then exports these to `static/icons/`:

| file | use |
| --- | --- |
| `icon-192.png`, `icon-512.png` | manifest icons (`purpose: any`) |
| `maskable-192.png`, `maskable-512.png` | Android adaptive icons: artwork padded with turquoise so the bubble is inside the 80% safe zone |
| `apple-touch-icon.png` (180×180) | iPhone home screen |
| `favicon.ico` (16/32/48), `favicon-32.png` | browser tab |
| `header-icon.png` | the old header logo (unused since the v23 header, which draws the traced icon bubble as SVG) |

Re-run with `./venv/bin/pip install pillow numpy scipy && ./venv/bin/python tools/make_icons.py`.

Theme: turquoise header (`#00C9CD`), black type, hot pink `#EF426F` and orange `#FF8200` accents (papel picado strip, map marker, install button).

### News sources (verified 2026-09-29)

In San Antonio (other metros' outlets are in `data/metros.json`; no San Antonio outlets are fetched elsewhere):

| Source | Feed |
| --- | --- |
| KSAT 12 | `https://www.ksat.com/arc/outboundfeeds/rss/category/news/local/?outputType=xml` |
| KENS 5 | `https://www.kens5.com/feeds/syndication/rss/news/local` (times out with a Chrome-style User-Agent; works with the app's UA) |
| San Antonio Report | `https://sanantonioreport.org/feed/` |
| Texas Public Radio | `https://www.tpr.org/news.rss` |
| News 4 San Antonio (WOAI) | `https://news4sanantonio.com/news/local.rss` |
| San Antonio Current | `https://sacurrent.com/sanantonio/Rss.xml` |
| Express-News | No public RSS. Pulled through a Google News RSS search, `site:expressnews.com/news when:3d` |

**Dynamic local searches** (Google News RSS `https://news.google.com/rss/search?q=…`), built for the detected place so Chisme works in any city:

| search | query | when |
| --- | --- | --- |
| city | `"{city}" {state} when:3d` | outside San Antonio (the SA feeds already cover SA) |
| county | `"{county}" {state} when:7d` | always |
| neighborhoods | `"{neighborhood}" "{city}" when:30d` for the 2 closest specific neighborhoods | always |
| downtown/midtown… | `"Downtown {city}" when:14d` | when the nearest name is generic |
| South Side | 2 searches for South Side SA terms, last 14 days | only on SA's South Side |

For the "strict" searches (county, neighborhood, South Side), a result is kept only if its **headline** names the place. Obituaries, social-media posts and roster pages are filtered out. Feeds are listed in `SA_FEEDS` / `feeds_for()` in `app.py`.

### Sports sources (verified 2026-09-29, all public and keyless)

| Source | Endpoint | Used for |
| --- | --- | --- |
| **ESPN public site API** (unofficial but widely used) | `https://site.api.espn.com/apis/site/v2/sports/{football/nfl, basketball/nba, baseball/mlb}/scoreboard` and `/news`; team news `/news?team=` (Cowboys 6, Texans 34, Rangers 13, Astros 18, Spurs 24); `/teams/24` and `/teams/24/schedule?seasontype=1,2,3` | NFL/NBA/MLB scores, league + Texas-team news with ESPN's own thumbnails, Spurs record, schedule and latest scores (falls back to the previous season in the offseason) |
| **ESPN standings** | `https://site.api.espn.com/apis/v2/sports/basketball/nba/standings` (falls back to `?season=2026` when the new season hasn't started; labeled "final") | Western Conference standings |
| **MLB Stats API** | `https://statsapi.mlb.com/api/v1/schedule?sportId=1` (today ±3 days); `schedule?sportId=12&teamId=510` (Missions); `standings?leagueId=109` (Texas League) | MLB scores, Missions games, Texas League South standings |
| **San Antonio Spurs on YouTube** | `https://www.youtube.com/feeds/videos.xml?channel_id=UCEZHE-0CoHqeL1LGFa2EmQw` | Trending: latest team videos (text links only) |
| **Pounding The Rock** (SB Nation Spurs blog) | `https://www.poundingtherock.com/rss/index.xml` | Trending: fan coverage (text links only) |
| **Google News RSS** | `"San Antonio Spurs" OR Wembanyama when:3d`, `"San Antonio Missions" (baseball OR "Wolff Stadium" OR "Texas League" OR Padres OR Double-A) when:60d` (National Historical Park / UNESCO results filtered out) | Spurs news from local outlets; Missions news |
| **Reddit r/NBASpurs** | `https://www.reddit.com/r/NBASpurs/top/.rss?t=week` | **Blocked**: Reddit answers 403/429 to server requests. Chisme lists it as unavailable and links to the subreddit instead |

### Event sources (verified 2026-09-29, all free and keyless)

| Source | How | Gives | Limits |
| --- | --- | --- | --- |
| **Visit San Antonio** | RSS `https://www.visitsanantonio.com/event/rss/`, plus each event page's schema.org JSON-LD and its `admission` note | ~30 current/featured SA events: photo, dates, venue + coordinates, admission text, organizer site | Only within ~60 km of SA. Dates only (no start times). The RSS is capped at 30 items. robots.txt asks for a 2 s crawl delay, so detail pages are fetched one at a time in the background (~1 min for a cold cache) |
| **Eventbrite** | public city page `https://www.eventbrite.com/d/{state}--{city}/events/` (pages 1–2): the event JSON embedded in the page. Prices come from each event page's JSON-LD `offers` | local start time, venue + coordinates, photo, price range / Free | Works for any U.S. city (Bexar County suburbs use San Antonio's page). `/api/v3/destination/events/` is disallowed by robots.txt and isn't used. Up to 40 event pages are looked up per area (1/s, cached a day). Heavy on business/networking events |
| **AllEvents** | public city page `https://allevents.in/{city}/all`, schema.org JSON-LD | big concerts/festivals: photo, date, venue + coordinates | Dates only. No prices, so they show "Check price". Ticket-resale listings ("… Tickets") are skipped |

### Food review sources (verified 2026-09-29, public feeds + a curated TikTok list, no keys)

| Source | Feed | Notes |
| --- | --- | --- |
| **Cherise SA Texas Food Guide** (YouTube, ~29K subs, "local guide to restaurants, food trucks… across the San Antonio food scene") | `https://www.youtube.com/feeds/videos.xml?channel_id=UCr5gIcFnRxKTaDNrcfA8ZaA` | posts several SA restaurant videos a week |
| **Hannah \| SATX Creator** (YouTube, "San Antonio, TX") | `…channel_id=UCuluE-lMh--_7hyziZAvDvQ` | mixed lifestyle channel, so only videos whose titles are about food are shown |
| **Texas Eats** (YouTube food & travel show) | `…channel_id=UCsC3RShvhYxR9bTUfogm6pg` | statewide show, so only videos that name San Antonio are shown |
| **San Antonio Current · Food & Drink** | `https://www.sacurrent.com/category/food-drink/feed/` | restaurant news/reviews with photos |
| **Express-News · Food** | Google News RSS `site:expressnews.com/food when:30d` | links go through Google News to the article; no photos in the feed (labeled placeholder) |
| **MySA · Food** | Google News RSS `site:mysanantonio.com/food when:30d` | same; headlines naming another Texas city (and not SA) are skipped |
| **Eatmigos** (Chris Flores, San Antonio; YouTube ~20K, Instagram ~122K) | `…channel_id=UCcRC7jl_YYqciUbzLh__WnA` + 2 TikToks | titles are just the spot's name, so no keyword filter |
| **Full Nelson Eats** (San Antonio filmmaker; the channel links instagram.com/fullnelsoneats) | `…channel_id=UCnPISg_Kx3fn62H1w1Enl1Q` | food videos only (the channel also has ads and vlogs) |
| **Porter's Food Reviews** (Jarnell Porter, San Antonio spots) | `…channel_id=UCQVETXoLaNtOMj8Bom9pUdg` | |
| **Siempre San Antonio** (Gabby Gonzalez) | `…channel_id=UCdxqYEScHFdNhUOqKBRkTXg` | same handle as her TikTok/Instagram and San Antonio content (the channel doesn't link back); food videos only |
| **Cherise** / **Elder Eats** (David Elder, host of KSAT's Texas Eats) / **San Antonio Munchies** (Alex Serna) on TikTok | curated in `data/food_tiktok.json`: 3 / 2 / 3 videos | each link found in public search results and checked with TikTok's oEmbed (author must match) |
| **S.A. Foodie** (Amanda Spencer, Instagram ~599K) | none: Instagram only | link card only; no TikTok at @s.a.foodie, and nothing ties @safoodie / @safoodietx to her |
| **Bootleg Food Review** (Jason Longoria, San Antonio; TikTok ~513K, Instagram ~126K) | curated list in `data/food_tiktok.json` → TikTok oEmbed + official embed player | TikTok [@bootlegfoodreview](https://www.tiktok.com/@bootlegfoodreview) (bio: San Antonio, TX 78223 P.O. box, links linktr.ee/BootlegFoodReview); Instagram [@bootlegfoodreview](https://www.instagram.com/bootlegfoodreview/) (linked from that Linktree). No YouTube channel of his is linked anywhere: `youtube.com/@bootlegfoodreview` exists but has 0 uploads and no tie to him, so there's no YouTube feed. Instagram has no keyless embed/listing API, so it's noted only. |

Checked and left out: **Edible San Antonio** (feed works but the newest post is from July 2025), **Amanda Spencer** and **SanAntonioMiniCritics** (SA food channels, but no uploads since 2024), **Full Nelson**, **The X Chef Review** and **Rick Eatz** (mostly non-food or non-SA lately), **CultureMap SA** (no public RSS). Items older than 60 days are dropped; up to 8 per source.

Not used: **Ticketmaster Discovery** needs an API key. **SA Current's** calendar is a CitySpark widget (no public feed). **SA Report** has no public events feed. **San Antonio Public Library** events load from BiblioCommons' private gateway (403). **Do210** blocks non-browser clients. The City's `sa.gov` has no public calendar feed. **Meetup** listings were mostly online/low-signal.

Events outside the U.S. aren't available. The Events view says so.

### Photo credits (`static/art/art.json`)

All from Wikimedia Commons. CC BY / CC BY-SA photos are shown unmodified except resizing and recompression. Murals and mosaics are the artists' works; the photo licenses cover the photographs.

| # | Subject | Artist | Photo | License | Source |
| --- | --- | --- | --- | --- | --- |
| 01 | The Alamo (San Antonio) | — | Andre m | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) | [Commons](https://commons.wikimedia.org/wiki/File:The_chapel_of_the_Alamo_Mission_in_San_Antonio.jpg) |
| 02 | River Walk & Tower of the Americas (San Antonio) | — | Larry D. Moore | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0) | [Commons](https://commons.wikimedia.org/wiki/File:River_walk_with_tower.jpg) |
| 03 | Mission San José (San Antonio) | — | P. Hughes | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | [Commons](https://commons.wikimedia.org/wiki/File:Mission_San_Jose,_San_Antonio,_Texas_with_clouds.jpg) |
| 04 | Mission Concepción (San Antonio) | — | Michaelluckey | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0) | [Commons](https://commons.wikimedia.org/wiki/File:Mission_Concepci%C3%B3n_in_San_Antonio,_Texas.jpg) |
| 05 | Mission Espada (San Antonio) | — | Michaelluckey | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0) | [Commons](https://commons.wikimedia.org/wiki/File:Mission_Espada_in_San_Antonio,_Texas.jpg) |
| 06 | San Fernando Cathedral (San Antonio) | — | Daniel Schwen | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | [Commons](https://commons.wikimedia.org/wiki/File:San_Fernando_Cathedral.jpg) |
| 07 | Tower of the Americas at night (San Antonio) | — | jcutrer | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | [Commons](https://commons.wikimedia.org/wiki/File:Tower_of_Americas_at_Night.jpg) |
| 08 | “Yanaguana” mural at Hemisfair (San Antonio) | Mural by Alex Rubio | Adrianna Chavez | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) | [Commons](https://commons.wikimedia.org/wiki/File:Yanaguana_mural_-_Hemisfair_(2025-12-12).jpg) |
| 09 | La Chiquita Bakery mural (San Antonio) | Mural artist not named in the source | Carol M. Highsmith | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:Mural_on_side_of_La_Chiquita_Bakery_depicting_Mexican-American_family_life_in_San_Antonio,_Texas_LCCN2014631985.tif) |
| 10 | Virgin of Guadalupe mosaic, Guadalupe Cultural Arts Center (San Antonio) | Mosaic by Jesse Treviño (2004) | Carol M. Highsmith | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:Mosaic_in_half-relief,_depicting_the_Virgin_Mary_at_the_Guadalupe_Cultural_Arts_Center_in_San_Antonio,_Texas_LCCN2014631982.tif) |
| 11 | “The Spirit of Healing” (San Antonio) | Mural by Jesse Treviño | Todd Dwyer | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) | [Commons](https://commons.wikimedia.org/wiki/File:Santa_Rosa_Children%27s_Hospital_-_panoramio.jpg) |
| 12 | Día de los Muertos ofrenda, Mission Marquee Plaza (San Antonio) | — | National Park Service (NPS Photo) | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:Ofrenda_or_Day_of_the_Dead_Altar_at_Mission_Marquee_Plaza._(586908b4-40dd-4be5-bc53-ababb89291f1).JPG) |
| 13 | Texas State Capitol (Austin) | — | LoneStarMike | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0) | [Commons](https://commons.wikimedia.org/wiki/File:TexasStateCapitol-2010-01.JPG) |

### Sports photo credits (`static/sports/`)

All from Wikimedia Commons. They were resized to 800 px WebP and are otherwise unmodified. No logos or press photos. A candidate with the team logo on the court was left out.

| File | Subject | Photo | License | Source |
| --- | --- | --- | --- | --- |
| `spurs-arena.webp` | Spurs vs. Mavericks, 2014 NBA Playoffs (arena now Frost Bank Center) | Katie Haugland | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0) | [Commons](https://commons.wikimedia.org/wiki/File:2014_NBA_Playoffs_Dallas_Mavericks_vs._San_Antonio_Spurs.jpg) |
| `spurs-bluehour.webp` | Blue hour before a Spurs game, 2012 | Mark Bonica | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0) | [Commons](https://commons.wikimedia.org/wiki/File:Blue_hour_at_the_AT%26T_center_(6734460031).jpg) |
| `missions-wolff.webp` | Nelson W. Wolff Municipal Stadium at dusk, 2006 | b r e n t (Flickr) | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0) | [Commons](https://commons.wikimedia.org/wiki/File:Wolff_Stadium_2006.jpg) |
| `missions-game.webp` | Missions outfielders chase a popup, 2019 | Minda Haas Kuhlmann | [CC BY 2.0](https://creativecommons.org/licenses/by/2.0) | [Commons](https://commons.wikimedia.org/wiki/File:San_Antonio_Missions_(48116648172).jpg) |
| `missions-2026.webp` | Between-innings tricycle ride, Wolff Stadium, Aug. 2026 | Airman Shayla Pham, U.S. Air National Guard | Public domain | [Commons](https://commons.wikimedia.org/wiki/File:149th_Fighter_Wing_at_San_Antonio_Missions_Game_(260808-Z-XB550-1212).jpg) |

Radar: [RainViewer](https://www.rainviewer.com/) tiles; basemap © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (standard tiles, greyed with a CSS filter). CARTO's light basemap was tried, but it now requires an API key.

## Checks

```bash
./venv/bin/pip install playwright            # uses system Chrome at /usr/bin/google-chrome
./venv/bin/python shoot.py                   # desktop 1280x900 + phone 390x844 screenshots + radar/news/forecast checks
./venv/bin/python location_test.py           # geolocation: South Side SA, Austin, moving, permission denied + manual search, Paris
./venv/bin/python pwa_check.py               # manifest + Chrome installability errors, SW control, offline reload, install/iOS UI
./venv/bin/python update_test.py             # phone: News first, sticky bar, swipe News→Sports, Weather→Sports, Events→Juegos, map pan, story links, events, offline
./venv/bin/python nav_forecast_test.py       # phone: fixed nav after scrolling far down each view; 7-day strip scrolls sideways w/o switching views; tap a day
./venv/bin/python events_food_test.py        # phone: category chips filter correctly, chip/food strips don't switch views, food reviews + links, offline
./venv/bin/python coldstart_test.py          # phone: proxy holds requests 50 s (sleeping Render) → saved news instantly, "Updating…" → "Waking up…" → "Updated"; 502s retried with backoff; pull-to-refresh; hanging geolocation
./venv/bin/python features_test.py           # phone: 5-tab nav, radar in Weather + blue dot, Spurs/NFL/MLB/Missions, Settings (theme, text size, location, default tab, reduce motion, refresh), dark-mode contrast (axe)
./venv/bin/python webkit_test.py            # WebKit iPhone 13: first-run location card → Settings-only, Sports/Weather tabs, denied/hanging geolocation, 320 px, default tab, logo button, no errors
./venv/bin/python upgrade_test.py           # WebKit iPhone 13: install v15 / v17 / v19 / v21 / v22 first, deploy the current build, reopen → tabs work, old caches gone; next deploy reloads an open page once
./venv/bin/python greeting_test.py         # WebKit iPhone 13: ¡Buenos días / Buenas tardes / Buenas noches, chismosos! at 9 AM / 3 PM / 9 PM / 2 AM CT, the exact line under it, no toggle (card or Settings), saved choice cleared, hint ≤ 2 lines at 390/320 px
./venv/bin/python location_city_test.py     # WebKit iPhone 13, GPS allowed in SA: type Houston TX / Houston, TX / Houston / 77002 / 33101 / Miami FL / Austin; the place sticks through GPS updates; skyline, News outlets, NWS, Events, food, Sports and time zone follow; Use my location returns
./venv/bin/python foryou_rank_test.py       # Node: the on-device For You ranker (features, open/watch time/save/skip/not-interested signals, 14-day decay, 20% exploration, variety rules: round-robin creators, top-10 cap, restaurant dedupe, lead rotation, why-chip text, storage caps, reset, no network)
./venv/bin/python foryou_ui_test.py         # WebKit iPhone 13 + Chromium touch: "Bigger the Pansa, Better the Chansa" (was For You) banner, full-screen scroll-snap feed, one muted autoplay player, Save/Directions/Not for me/Undo, signals in localStorage, why chip, Back + history back, reduced motion tap-to-play, Reset my feed, creator cards, cover = first 3 videos, 9 creators in the first 9, lead rotation
./venv/bin/python push_test.py              # Web Push end to end against a local mock push service: VAPID signature, aes128gcm decrypt, first look, 45-min limit, warnings/watches, quiet hours, stale stories, test push, 410 cleanup, unsubscribe, Upstash REST store, no secrets in git
./venv/bin/python donate_alerts_test.py     # WebKit + Chromium: donate card (News/¿Cuál dieta?/Settings, light + dark, opens cash.app), New chisme ↑ pill (no jump, tap, refresh, focus check), alerts UI (soft prompt once, Turn on, test push decrypted, toggles, SW notification, tap opens the story in-app, Turn off)
./venv/bin/python food_player_test.py        # WebKit iPhone 13 + Chromium: ¿Cuál dieta? tab (nav, swipe and Settings order News · Sports · Weather · ¿Cuál dieta? · Juegos · Events, Sports ⇄ Weather ⇄ ¿Cuál dieta? ⇄ Juegos swipes, 6 tabs fit at 390/320 px with big text), no Food chip in Events, desk ≤ 5 at the bottom, in-app YouTube/TikTok player, reader sheet (framed vs Google News), Save from the sheet, swipe Events↔food tab, swipe-down close, offline
./venv/bin/python food_saved_test.py         # WebKit iPhone 13: food Save toggles, Saved spots (n), reload persistence, Directions (Apple Maps), remove/undo, add place; + Chromium offline
./venv/bin/python header_shots.py            # WebKit iPhone 13: header screenshots (light/dark/crop + 320 px, desktop, big text, Austin in /tmp/wk); bubble opens Settings, tail clear of the tower
./venv/bin/python art_test.py                # phone: a photo after every 4 stories, all 13 rotate, captions/credits match art.json, swipe on photos, offline
./venv/bin/python newsorder_test.py          # News order: reshuffle on repeat visits (Node unit + WebKit iPhone, before/after screenshots)
./venv/bin/python juegos_test.py             # 🎲 Juegitos: Lotería Chismosa + Ice Ice Bebé, full screen in portrait (Node logic, WebKit iPhone play-through, reduce motion, Chromium offline; screenshots)
./venv/bin/python donate_every_tab_test.py    # WebKit iPhone 13: donate card last on all 6 tabs, the once-per-launch mid-list card (News/Events/Weather, re-render, tab switches, ✕ for the session); screenshots
npx lighthouse@11 http://localhost:8211/ --only-categories=pwa,accessibility,best-practices   # v11 still has the PWA category
```

Last run (2026-09-29, about 6:50 PM CT, `donate-alerts` preview branch, build 26: donate card, 4-min news + New chisme ↑ pill, Web Push alerts):
* All pass: `push_test`, `donate_alerts_test`, `foryou_rank_test`, `foryou_ui_test`, `greeting_test`, `features_test`, `nav_forecast_test`, `webkit_test`, `food_saved_test`, `events_food_test`, `update_test`, `art_test`, `location_test`, `location_city_test`, `coldstart_test`, `food_player_test`, `pwa_check`, `upgrade_test` (v15…v24 and **v25** → v26). Lighthouse on `/` and `/#cual-dieta`: accessibility 100, best practices 100, PWA 100. Live check: v24 → v25 on chisme.onrender.com clean in WebKit and Chromium.

Last run (2026-09-29, about 5:45 PM CT, v25 release on main: For You vertical feed + on-device ranking with creator/restaurant variety + Creators we follow, build 25):
* All pass: `foryou_rank_test` (52 checks), `foryou_ui_test` (WebKit feed + Chromium real touch swipe), `food_player_test`, `location_city_test`, `greeting_test`, `features_test`, `nav_forecast_test`, `webkit_test`, `food_saved_test`, `events_food_test`, `update_test`, `art_test`, `location_test`, `coldstart_test`, `pwa_check`, `upgrade_test` (v15…v23 and **v24** → v25). Lighthouse on `/#cual-dieta`: accessibility 100, best practices 100, PWA 100.
* `food_player_test.py`: the tab-swipe checks now start on the ¿Cuál dieta? section heading, because the For You banner pushes the intro below the fold. `foryou_ui_test.py` ignores console noise from inside the embedded TikTok/YouTube players (their own CSP headers, cookie banner, cross-origin frame access); Chisme's own errors still fail it.

Previous run (2026-09-29, about 4:20 PM CT, v24 release on main: tab order News · Sports · ¿Cuál dieta? · Weather · Events + plural greeting, build 24):
* All pass: `greeting_test`, `location_city_test` (7 queries stick through GPS updates; Houston, Miami and Austin checks), `food_player_test`, `webkit_test`, `upgrade_test` (v15/v17/v19/v21/v22/**v23** → v24, plus the next deploy v24 → v25), `features_test`, `food_saved_test`, `events_food_test`, `update_test`, `art_test`, `coldstart_test`, `location_test`, `nav_forecast_test`, `pwa_check`. Lighthouse on `/` and `/#cual-dieta`: accessibility 100, best practices 100, PWA 100.

Previous run (2026-09-29, about 2:05 PM CT, icon-bubble header + Saved spots + no Me button, build 23):
* All pass: `webkit_test`, `upgrade_test` (from **v15, v17, v19, v21 and v22**, plus the next deploy v23 → v24 reloading an open page), `features_test`, `food_saved_test`, `events_food_test`, `art_test`, `coldstart_test`, `location_test`, `nav_forecast_test`, `update_test`, `pwa_check`. Lighthouse 11.7 on `/`: PWA 100, Accessibility 100, Best Practices 100.
* `food_saved_test.py` now lets the background loads finish before its reload (WebKit logged the cut-off `/api/sports` fetch as a console error: a test race, not an app bug).
* `upgrade_test.py` fixes: the old page is closed (`about:blank`) before the deploy, and events are flushed before clearing, because `serve()` blocks the event loop. The v19/v21 "new worker installed" check now actually polls `caches.keys()` for the current version (an async `wait_for_function` predicate is always truthy). "Failed to load resource" console lines, e.g. an API request cut off by the test's own reopen, are reported as notes; they aren't counted as JS errors.

Earlier run (2026-09-29, about 11:05 AM CT, iPhone fixes, build 22):
* `upgrade_test.py` (WebKit, iPhone 13). **From v15 and v17**, the first open after the deploy already runs build 22, and Sports (5,700+ characters) and Weather render. **From v19 and v21**, the first open shows that version's own cached (consistent) app plus the update toast, and the next open is build 22. In every case the old caches are removed, HTML build = app.js build = `sw.js` VERSION, there's no "didn't start" banner and no JS errors. **Next deploy** (22 → 23 with the app open): the page reloads itself once onto build 23 and Sports works.
* `webkit_test.py` (WebKit, iPhone 13):
  * The first launch shows the location card (and no pill). A ZIP picked on it sets the place and hides the card; there's no location UI after 2 reloads, and Settings shows "Showing: South San, San Antonio". "Not now" also hides the card for good.
  * Location granted: no card, and Sports and Weather render. The logo button has a transparent background, no border, no padding and `appearance: none`, and still opens Settings.
  * Geolocation denied or hanging: Weather shows San Antonio's weather.
  * 320 px: no sideways overflow, all 4 tabs fit, Sports/Weather render. The default tab setting opens on Weather / Sports.
  * No console or page errors.
* The live site (v21) on a fresh WebKit install worked. The bug only shows up when upgrading from v15–v18.
* Also fixed: an occasional Chrome console error ("Ignored attempt to cancel a touchmove…"). Leaflet tried to cancel a touch that landed on the radar map while the page was still scrolling; those moves are now kept away from the map. Map panning still works.
* All other checks re-run and pass. Lighthouse 11.7 on `/` and `/#sports`: PWA 100, Accessibility 100, Best Practices 100.

Earlier run (2026-09-29, about 10:00 AM CT, radar in Weather + Sports + Settings/dark mode):
* `features_test.py` (390×844): tabs are exactly News · Sports · Weather · ¿Cuál dieta? · Juegos · Events (v31), with no Radar tab and no A−/A+ on the home screen. The radar is inside Weather, with the basemap + radar tiles loaded, the legend and the time badge, a blue dot `rgb(10,132,255)` with a 3 px white ring and the `me-pulse` halo, and no tooltip or red marker. Sports: the Spurs summary, scores, schedule, West standings with the Spurs highlighted, news and credited photos. NFL, MLB (Wild Card games) and Missions (standings, final games) all render. News images come only from ESPN; swiping on the score strip stays on Sports. Settings: opens from the logo, A+ changes the size, no chismoso/chismosa choice and a plural greeting, ZIP 78704 → Austin and back to 78211, Refresh now, Reduce motion, Dark. After a reload the app stays dark and opens on Sports. axe color-contrast: **0 violations** in dark mode on all four views + Settings, and on Sports in light mode; a full axe run on the open Settings sheet finds 0 violations in light and dark. Settings buttons fit without overlap from 16 px to 30 px text. No console errors.
* Re-ran `coldstart_test.py`, `update_test.py`, `nav_forecast_test.py`, `events_food_test.py`, `art_test.py`, `location_test.py`, `pwa_check.py` and `shoot.py`: all pass, no console errors. Lighthouse 11.7 on `/` and `/#sports`: PWA 100, Accessibility 100, Best Practices 100.

Earlier run (2026-09-29, about 9:05 AM CT, "buffering / not updating" fix):
* `coldstart_test.py` (50 s simulated wake-up): saved news on screen **0.1 s** after opening, stamp "Saved copy from …", pill "Updating…", then "Waking up the server…" after 8 s. No offline banner. **"Updated 9:02 AM"** after 51 s, with fresh news + weather. Two 502s from `/api/news` were retried after 5 s and 15 s, and the stories stayed on screen with a "Retry now" button. Pull-to-refresh shows its indicator and refreshes. A geolocation call that never answers gives up after 12 s, and news loads without it. No console errors.
* With Nominatim mocked to always answer 429: `/api/news` 200 in 2.3 s (30 + 80 stories, "South San, San Antonio" via Photon), `/api/place` for Austin → "Downtown, Austin", `/api/geocode` for "Houston, TX" and 78211 work.
* All other checks re-run and pass. Lighthouse 11.7: PWA 100, Accessibility 100, Best Practices 100.

Earlier run (2026-09-29, about 8:45 AM CT, art between stories):
* `art_test.py`: on the News view (30 + 80 stories), 26 photo cards, each after exactly 4 stories and never at the end of a list, cycling through all 13. Alt text, caption, artist, author, license and links match `art.json` for all 13, and all load. A vertical drag on a photo scrolls (~360 px); a sideways swipe on a photo goes to Weather and back. The next load starts on a different photo. Offline (clean profile): 14 art files precached, all 26 cards load, 0 failed requests, 0 console errors. No console errors online.
* Re-ran `nav_forecast_test.py`, `events_food_test.py`, `update_test.py` and `pwa_check.py`: all pass. Lighthouse 11.7 on `/`: PWA 100, Accessibility 100, Best Practices 100.

Earlier run (2026-09-29, about 8:00 AM CT, fixed nav + forecast strip + categories/food):
* `nav_forecast_test.py`: nav stays `position: fixed` at top 0 with all four buttons hit-testable after scrolling ~24,000 px (News), ~30,000 px (Weather) and ~20,000 px (Events). The forecast strip is 7 cards with `scroll-snap-type: x mandatory`; a sideways drag scrolls it 377 px and stays on Weather. Tapping a day expands its details, tapping again collapses. A swipe outside the strip still switches views. No console errors.
* `events_food_test.py`: All 80 · Concerts 22 · Festivals 7 · Free classes 2 (shown lists match the API tags exactly). Swiping the chip row and the creators strip scrolls them and stays on Events. Food: 19 creator videos + 24 food-desk stories, links only to youtube.com / sacurrent.com / news.google.com and all taken from the API. Chip choice persists across reloads. Offline (clean profile): 0 failed requests, 0 console errors, food + events render from the saved copy with labeled photo placeholders.

Earlier run (2026-09-29, about 6:00 AM CT, after the views/events update):
* `update_test.py` (390×844): opens on News. The section bar is at the top after scrolling 2,300 px. A swipe on a story switches News → Weather, and swiping back restores the News scroll position. Vertical drags scroll (~520 px) without switching. A sideways drag on the radar pans the map without switching. A small wiggle snaps back. 110 stories, each with read + search links, 23 with "Also reported by". Every link was checked against the feed data. 60 events with 59 real photos + 1 labeled placeholder, 57 mini-maps, 9 free / 21 priced / 30 "Check price", 37 with an NWS outlook and 23 "not available yet". Offline reload shows news, forecast and all 60 events. No console errors.
* Lighthouse 11.7: **PWA 100, Accessibility 100, Best Practices 100** (also Accessibility 100 on `/#events`).

Earlier run (2026-09-29, about 5:02 AM CT):
* Chrome `Page.getInstallabilityErrors`: **none**.
* Lighthouse 11: **PWA 100, Accessibility 100, Best Practices 100** (report in `screenshots/lighthouse.report.html`).
* Offline reload kept all news and the forecast.
* `location_test.py`: South Side SA → "South San, San Antonio"; Austin → "Downtown, Austin" (also via watchPosition when moving); denied → default San Antonio + search ("Houston, TX", ZIP 78211 → South San); Paris → clear non-US weather message. No page errors.

## Deploy

The app is one Python process with an in-memory cache (alerts keep their subscriber list in Upstash Redis, see Alerts setup). Both options below give you HTTPS, which the phone install needs.

**Render:**
1. Push this folder to a GitHub repo.
2. In Render, choose **New → Blueprint** and pick the repo. It reads `render.yaml`: service `chisme`, build `pip install -r requirements.txt`, start `uvicorn app:app --host 0.0.0.0 --port $PORT`, health check `/healthz`.
3. Set `APP_USER_AGENT` to include your email (e.g. `Chisme/1.0 (you@example.com)`). Nominatim throttles anonymous-looking traffic from shared hosting IPs; Chisme falls back to Photon when that happens, but a real contact helps.
4. Open `https://chisme.onrender.com` (or whatever URL Render shows) on your phone and install it as described above.

Free instances sleep when idle, and the first request after a nap takes **~50 s** while Render wakes the service. The installed app shows the saved copy immediately with "Waking up the server…", and then "Updated h:mm" when fresh data arrives.

**Fly.io:** uses the included `Dockerfile` and `fly.toml` (app `chisme`, region `dfw`):
```bash
fly launch --copy-config --no-deploy   # pick a unique app name if "chisme" is taken
fly secrets set APP_USER_AGENT="Chisme/1.0 (you@example.com)"
fly deploy
# → https://<app>.fly.dev
```

**Any Docker host** (Railway, Cloud Run, a VPS behind Caddy for automatic HTTPS):
```bash
docker build -t chisme . && docker run -p 8080:8080 -e APP_USER_AGENT="Chisme/1.0 (you@example.com)" chisme
```

**Vercel:** can run FastAPI as a Python serverless function, but each cold function starts with an empty cache, so Render or Fly is a better fit.

### Tía Chismosa (the chat mascot, v28)

A floating avatar (bottom right) opens a chat sheet with **Tía Chismosa**, a sassy, warm AI tía with
rollers, a cafecito and a glowing phone.
* **She greets you by the time of day** and, once a day, gives you a **chisme del día**: the top 3 stories, events,
  sports or food items for you. It's ranked **on the phone** from what you tap (news, sports, events) plus your For You
  food profile. Each item is a button that opens in the in-app reader.
* **She chats about what's in the app right now:** stories, weather, events, sports and food. Every message sends
  the conversation plus the app's current feed items to `POST /api/mascot/chat`. The server numbers the items (S1…Sn)
  and tells the model to use **only** those and cite them; citations to anything that wasn't sent are dropped, and each
  citation opens in the in-app reader. She never invents or rewrites news. Serious news stays plain and respectful;
  the banter is for light stuff.
* **Safety:** a pre-filter answers self-harm with the 988 Lifeline, refuses violence, weapons, drugs and hacking, and
  declines medical, legal and money advice without calling the model. The model's own safety filters stay on. Replies
  are capped at `MASCOT_MAX_TOKENS` (350) and 1,200 characters.
* **Limits:** 30 messages per phone per hour (`MASCOT_PER_HOUR`), plus a server-wide daily budget (`MASCOT_DAILY_CAP`,
  450). Past either one, or whenever the AI is down or out of free quota, she answers with **smart answers** (no AI)
  built from the same feeds.
* **Privacy:** chat history (the last 40 messages) and her interest profile stay in the phone's localStorage. The
  server keeps nothing. **Settings → Tía Chismosa → Forget me** (tap twice) erases the chats, her interests and the
  For You profile.
* **No key, no problem (v39):** without `GEMINI_API_KEY` she still answers specific questions from the app's own feeds
  (`smart()` in `mascot.py`): "Spurs score" / "did the Spurs win" → the live or latest score + the next game + the
  record; "standings"; "weather" (tonight / tomorrow / this weekend) → NWS now, forecast and alerts; "events this
  weekend" (tonight, tomorrow, a weekday, free, concerts…) → the events in that window; food; and any other words →
  the best-matching stories from every section, with in-app links (fuzzy keyword + entity matching). The chat
  header no longer shows a "Scripted mode" / "AI" strip.
* **She knows the whole app (v39):** each message, the server adds its own current feeds for the phone's spot (the
  same caches the tabs use, so usually instant): every news story from every source and section incl. Near You,
  ESPN games (live, final, upcoming), the Spurs' record and standings, sports stories, NWS weather + alerts, events
  and food, merged with what the phone shows (up to 320 numbered sources). With a key, the model gets all of it plus
  the top matches for the question and the smart answer's facts, and must cite [S#]; the news stays straight.
* **Providers are swappable:** `MASCOT_PROVIDER=gemini|openai|anthropic` with `GEMINI_API_KEY`, `OPENAI_API_KEY` or
  `ANTHROPIC_API_KEY`, and optionally `MASCOT_MODEL`. The default is `gemini-3.5-flash-lite`, whose free tier allows
  about 500 requests a day; the plain Flash models allow only about 20 a day.
* **Her art:** `static/mascot/` (a round 64/128/192 px WebP avatar and a 480/960 px header) is built from one
  picture: `./venv/bin/python tools/make_mascot_assets.py path/to/art.png --face CX,CY,SIZE`. The face box is in
  source pixels and is saved in `static/mascot/mascot.json`. To swap her look, run it with a new picture.

**Turn on her AI (free, about 5 minutes):**
1. Go to **aistudio.google.com** and sign in with a Google account.
2. Click **Get API key → Create API key**. Let it create a new project if it offers to. Copy the key. New keys are
   "auth keys" that start with `AQ.` (older `AIza…` keys work too): Chisme never checks the prefix and sends the key
   in the `x-goog-api-key` header to Gemini's native `generateContent` endpoint, the way Google's docs say.
   Don't turn on billing: the free tier is enough.
3. In the Render dashboard, open the `chisme` service → **Environment** → **Add Environment Variable**, set
   `GEMINI_API_KEY` to the key, then **Save changes**. Render redeploys.
4. Check https://chisme.onrender.com/api/mascot/config: it says `"ai": true, "provider": "gemini"` once the key is live.
Keep the key private: never commit it or paste it into chats. If it leaks, delete it in AI Studio and make a new one.

### Alerts setup (free: Upstash Redis + a GitHub Actions timer)

Render's free plan sleeps after 15 idle minutes and has no disk, so Chisme can't keep subscriptions in memory or run
its own timer. What it does instead:
* **Subscriptions are stored in Upstash Redis** (free tier, no card) through its REST API. Without Upstash they go to a
  file in `/tmp`, which Render wipes every time the service sleeps; the app re-registers when it's opened, but phones
  that aren't opened would stop getting alerts. So set up Upstash.
* **A GitHub Actions workflow runs every 10 minutes** (the file is `tools/push-tick.yml`; it has to be copied to
  `.github/workflows/push-tick.yml`, see step 5) and calls `POST /api/push/tick` with a secret. That wakes
  the server, which checks each subscriber's area (news + NWS alerts), sends what's new, and goes back to sleep later.

Steps (one time):
1. **Make the keys.** On your computer, in this folder: `./venv/bin/python tools/make_vapid_keys.py`. It prints four lines
   (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`, `PUSH_TICK_SECRET`). Keep them private; don't commit them.
2. **Make the free database.** Sign up at upstash.com → **Create Database** (Redis, free, a US region) → open it →
   **REST API** → copy **UPSTASH_REDIS_REST_URL** and **UPSTASH_REDIS_REST_TOKEN**.
3. **Tell Render.** Render dashboard → the `chisme` service → **Environment** → add six variables: `VAPID_PUBLIC_KEY`,
   `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (change it to `mailto:` + your email), `PUSH_TICK_SECRET`,
   `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` → **Save changes** (Render redeploys).
4. **Tell GitHub.** The repo on github.com → **Settings → Secrets and variables → Actions → New repository secret**:
   name `PUSH_TICK_SECRET`, value = the same secret as on Render. (Optional: a repository *variable* `CHISME_URL` if the
   app isn't at `https://chisme.onrender.com`.)
5. **Add the timer.** GitHub only lets a login with the `workflow` permission add workflow files, so this one is
   added by hand: on github.com open the repo → **Add file → Create new file** → name it
   `.github/workflows/push-tick.yml` → paste everything from `tools/push-tick.yml` → **Commit changes**. Then the
   **Actions** tab → allow workflows if asked → **push-tick** → **Run workflow**. The log should end with something like
   `{"ok":true,"subs":0,…}`.
6. **Turn it on on your phone.** iPhone: open the site in Safari → Share → **Add to Home Screen** → open Chisme from
   the Home Screen → Settings → **Alerts → Turn on alerts 🔔** → Allow → **Send a test**. Android/desktop: the same from
   the browser.

Alerts limits: GitHub runs scheduled jobs every 10 minutes at best and often 5–15 minutes late (sometimes it skips a
run when GitHub is busy), so alerts can lag by that much. GitHub turns off scheduled workflows in a repo with no
activity for 60 days (re-enable it in the Actions tab). Each tick keeps the free server awake, so with alerts on it's
awake almost all the time: that's about 730 of Render's 750 free instance hours a month, fine for one free service
(and the app opens faster), but if you run other free services on the same Render account, change the cron in
`.github/workflows/push-tick.yml` to `*/20` or `*/30`. Upstash's free tier easily covers family and friends (each tick reads the list
once and writes only changed subscribers). iPhone alerts need iOS 16.4+ and the Home Screen app.

## Limitations

* **Geolocation needs HTTPS or localhost.** On plain `http://` from another device, the browser refuses, and Chisme falls back to the city/ZIP search. iOS Safari asks again in some situations, and the in-app "Use my location" button re-requests it. If you've blocked location for the site, it has to be re-allowed in browser/phone settings.
* **On Render's free plan, Nominatim may refuse requests** (shared IP → 429). Places then come from Photon or NWS, which can be less precise (e.g. the city instead of the neighborhood) until Nominatim answers again.
* **Nominatim is rate-limited (1 request/second) and shared.** The first visit to a new ~1 km area makes a few lookups (place + nearby neighborhoods), so the first load there can take **~5–8 s**. After that it's cached. For a busy public deployment, use your own or a commercial geocoder (`NOMINATIM_URL`).
* **Neighborhood names are approximate.** OSM has few neighborhood boundaries in Texas cities, so "Near:" uses the nearest named place from Nominatim, which can be a subdivision name or the ZIP's area. San Antonio uses the built-in gazetteer's *points*, not boundaries. The Overpass API (for full neighborhood polygons) wasn't reachable from the build box, so it isn't used.
* **"Near You" is keyword-based.** It can miss stories that don't name a place, and it can match a different place with the same name. Common names are guarded by requiring the city too, but some false positives remain (e.g. a story about a "Downtown Austin" altercation involving San Marcos officials).
* **Google News RSS** results (Express-News and all dynamic searches) link through `news.google.com` redirects, often have no thumbnails, and Google could rate-limit or change the format. Some articles are paywalled.
* **NWS is U.S.-only.** Outside the U.S. (and in some offshore spots) there's no forecast, observation or alerts, only a clear message. Radar coverage outside the U.S. depends on RainViewer.
* **Radar basemap:** it's OpenStreetMap's standard tiles greyed out with a CSS filter. Free "light/dark" basemaps (CARTO) now need an API key.
* **Radar resolution:** RainViewer's free tiles stop at **zoom 7** (higher zooms return a "Zoom Level Not Supported" image). Leaflet stretches the zoom-7 image (`maxNativeZoom: 7`), so the radar gets blocky at neighborhood scale. The radar isn't available offline.
* **OpenStreetMap tiles:** `tile.openstreetmap.org` is fine for personal use but has a [usage policy](https://operations.osmfoundation.org/policies/tiles/). For a public, high-traffic deployment, use a tile provider.
* **Events:** prices appear only when a listing states them. Many say "Check price", and prices can change, so confirm on the event page. Visit SA and AllEvents give dates without start times. Two sources sometimes disagree on a date; both listings are shown as published. Sources are HTML pages and a feed, so a site redesign can break one. It then shows as "unavailable" under Event sources and the others keep working. Event photos and map tiles need a connection (offline shows "Photo loads when you're online"). **Categories** are keyword-based, so a few events land in an odd bucket (e.g. an Eventbrite "Food & Drink" speed-dating night shows under Food). **Food reviews** depend on creators' public YouTube feeds (latest 15 videos each) and Google News for Express-News/MySA; a feed that fails is shown as "unavailable" under Event sources and the rest keep working.
* **"Also reported by"** matches headlines by shared key words (≥3 words, ≥50% overlap, within 5 days), so it can occasionally link a closely related story rather than the exact same one.
* **Sports sources:** ESPN's `site.api.espn.com` is public but unofficial and undocumented, so it could change without notice (a failing ESPN feed shows as unavailable, and MLB/Missions keep working from the MLB Stats API). **Reddit blocks server requests** (403/429), so r/NBASpurs posts aren't shown, only a link. Spurs YouTube, Pounding The Rock and Google News items are shown **as text links without images** on purpose (their thumbnails can be press or team photos). In the offseason, "latest scores" and standings come from the finished season and are labeled that way.
* **Offline** shows only the **last location's** saved data. Moving to a new place while offline keeps showing the old place until you're back online.
* **Current conditions** come from the nearest airport station and are usually 30–60 minutes old.
* **iOS:** there's no automatic install prompt (Apple doesn't allow one), only the Share → Add to Home Screen hint. iOS may clear saved offline data for a home-screen app that hasn't been opened in a few weeks.
* The Android install button only appears when Chrome decides the app is installable (HTTPS, not already installed). A real phone install still has to be done by hand after deploying.
