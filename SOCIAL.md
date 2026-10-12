# Chisme social, part 1

What's in it: accounts, profiles, Homies, Chismes with photos and short videos, the four feeds, reactions, comments,
shares, ChismeTV reposts, and the safety tools. No LIVE (on hold until Chisme makes money), no messages yet (part 2),
no check-ins or map yet (part 3).

Files: `social.py` (rules + shapes), `social_api.py` (routes), `social_store.py` (Supabase / SQLite, R2 / Supabase
Storage / local), `social_auth.py` (Supabase Auth), `static/social.{js,css}` (inside the main app, `index.html`; `social.html` is only the moderation page),
`supabase/migrations/20261004150000_social_p1.sql` (tables + RLS). Test: `social_test.py` (no network, no browser).

## Pages
* It all lives inside the main app's **Chisme** tab, with the app's own header, background, cards, chips and bottom
  tabs (social.css is scoped under `.sx` and only adds what the app doesn't have). User Chismes are mixed into
  **All** (tagged 🌶️ San Anto, like the News / Sports / Events tags), and a second chip row opens the 🤝 Homies ·
  🌶️ San Anto · 🔥 Trending · 😂 Memes feeds in place of the mix. The "What's the chisme? ➕ CHISME" bar opens the
  composer. Profiles, Homies, Alerts and Settings open from the feed (names, @mentions) and from the ☰ menu in the
  top bar. Routes are `#s/...` (e.g. `/#s/u/lupe`, `/#s/feed/memes`), so they never clash with the app's own
  `#news`, `#juegos`. The old `/social` link redirects to `/#s/feed/sananto`.
* Feeds 🤝 Homies · 🌶️ San Anto · 🔥 Trending · 😂 Memes; ➕ CHISME (Take Photo, Upload Photo,
  Record Video, Upload Video, Repost a ChismeTV clip, Post a Meme, Text Chisme); profiles; Homies (requests, Homie or
  Nah); Alerts; Settings (privacy, blocked people, sign out, delete account).
* `/c/<id>`: the share page for an Everyone Chisme (Open Graph tags).
* `/dmca`: the copyright takedown form. Each Chisme's ⋯ menu also has ©️ Report copyright.
* `/stats/social`: the moderation queue (owner only, the /stats sign-in).

## How it works
* **Accounts:** Supabase Auth stores and checks passwords and sends the 6-digit email codes. Chisme keeps its own random
  session ids (hashed). Sign-up asks for the birthday and refuses anyone under 18 (and remembers that on the phone).
  No SMS. Sign in with Apple / Google only when `SOCIAL_APPLE=1` / `SOCIAL_GOOGLE=1` (and the providers are set up in
  Supabase).
* **Bot check:** Cloudflare Turnstile when `TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET_KEY` are set; until then a signed
  math question plus a hidden honeypot field. The copy: "Prove you ain't a bot, cuh 🤖".
* **Rate limits** (Upstash when set, else memory): sign-ups per IP / phone, sign-ins per IP / email, codes, Chismes
  (new accounts: 3 an hour, 8 a day, no links for 72 h), comments, Homie requests, uploads, reports, reactions.
* **Profiles:** avatar, cover banner, display name, @username, bio, part of town (optional), theme accent from the
  Fiesta palette (turquoise, pink, orange, purple, silver, black: no yellow), one pinned Chisme.
* **Photos:** shrunk on the phone (2048 px JPEG, redrawn so EXIF/GPS never leave it), then re-encoded on the server
  to WebP from the pixels only (no EXIF, GPS, XMP or comments). 4 per Chisme, 8 MB max.
* **Videos:** 60 s max. The phone re-records big or over-720p videos at 720p when it can; the server always re-encodes
  to H.264/AAC at 720p max with all metadata, chapters and data tracks dropped, and makes a poster frame. 40 MB max
  upload.
* **Sign-ups are testers only for now:** `SIGNUPS_PUBLIC` is off (0) by default until chisme.co has a verified email
  sending domain (around Oct 29), so the 6-digit codes reliably arrive. While it's off, only the emails in
  `SOCIAL_SIGNUP_TESTERS` (comma list; Gmail dots / +tags don't matter) can make an account; everyone else sees
  "Accounts are opening soon. Keep browsing the chisme! 👀". Testers use `/#s/signup/invite`. Browsing and signing in
  to existing accounts stay open. Set `SIGNUPS_PUBLIC=1` to open them.
* **Sign-up checks (Plato, legal):** a birthdate (18+, checked in the browser AND on the server, Chicago time). The
  birthdate itself is never stored: `social_private` keeps only `adult = true` and `age_checked_at` (safer: nothing
  to leak). An UNTICKED "I agree to the Terms and Privacy Policy" box (links /terms, /privacy) that they tick
  themselves; the server refuses without it. Saved: `tos_at` + `tos_version`, `privacy_at` + `privacy_version`, and
  one row each in `social_consents` (terms, privacy, community_rules, age_18) with the time. RLS: forced, anon
  revoked, a person reads only their own rows; rows go with the account. Schema: the NEW migration
  `supabase/migrations/20261012190000_social_signup_consent.sql`, applied AFTER `20261004150000_social_p1.sql`.
* **Legal pages:** `/terms`, `/privacy`, `/community-rules` are Plato's final text (`legal/terms.md`, `privacy.md`,
  `rules-and-copyright.md`, copied word for word from /workspace/chisme_legal), built in the app's look by
  `./venv/bin/python tools/make_legal_pages.py`. The consent versions (`TERMS_VERSION` / `PRIVACY_VERSION` /
  `RULES_VERSION` in social.py) are each page's "Effective date" (2026-10-12); a test fails if they drift, so bump
  them with new text. The contact (name, address, phone, email, DMCA number) lives in ONE file, `legal_contact.py`:
  `SHOW_STREET_ADDRESS = False` hides the street line on every page and on /dmca, then rebuild the pages.
* **Uploads are owner + testers only for now:** `UPLOADS_PUBLIC` is off (0) by default, because Cloudflare's CSAM
  Scanning Tool needs a domain that runs through Cloudflare and chisme.onrender.com doesn't. Until a scanner is live,
  only the @usernames in `SOCIAL_UPLOAD_TESTERS` (comma list; Goonie's first) can upload photos, videos, avatars or
  covers. Everyone else sees "Photo and video uploads are coming soon 📸 Text Chismes work right now." Text Chismes,
  ChismeTV reposts, reactions and comments stay open. Set `UPLOADS_PUBLIC=1` once the scanner is on.
* **Storage:** Cloudflare R2 when all five `R2_*` keys are set, else Supabase Storage (`chisme-media` bucket), else a
  local folder (dev). Force one with `SOCIAL_MEDIA_STORE=r2|supabase|local`.
* **CSAM scan hook:** every photo, and three frames + the poster of every video, go to `CSAM_SCAN_URL` (Bearer
  `CSAM_SCAN_TOKEN`) before anything is stored. It answers `{"match": true|false}`. A match: the file goes to the
  private quarantine bucket, a hold row is written, the account is closed, and the queue shows "file the NCMEC report".
  A scanner error: the upload is refused ("try again in a few minutes"). Not set: uploads go through (turn on
  Cloudflare's free CSAM Scanning Tool on the R2 custom domain as well).
* **Reports:** reasons incl. Copyright. 3 open reports (or one "Someone under 18") auto-hide a Chisme or comment and
  flag a profile until the owner decides in `/stats/social`: Keep it up / Take it down / Ban account (bans also block
  that email from signing up again). DMCA notices hide the listed Chismes right away, then Remove / Reject.
* **Block:** both ways, ends the Homie connection, stops requests, never tells them.
* **Delete account:** Settings → type DELETE: profile, Chismes, photos, videos, comments, reactions, Homies and the
  Supabase Auth user are deleted at once.
* **RLS:** on and forced on every table; the public key can read nothing; nobody but the server can write.

### The admin account, badges and new-user review
- **Admin:** the account whose email matches `SOCIAL_OWNER_EMAIL` is the one full admin (`role=admin`). It always wears the GOLD badge, set on sign-up, verify and sign-in. Only one admin is allowed (a unique index in the migration).
- **Badges:** GOLD or BLUE, shown next to names everywhere (cards, profiles, comments, Homies, menus, the admin lists). The admin gives or removes them with **🏅 Badge** on a profile, or under Moderation → Badges (in ☰ → Admin or on /stats/social). The server only accepts `POST /api/social/admin/badge` from the admin and answers 404 to anyone else. In Supabase, the trigger `social_badges_admin_only` refuses any change to badge, role or review that doesn't come from the service role. Gold is a metallic orange-gold built on #FF6A0B with a silver shine (no yellow). Blue uses the app's turquoise.
- **New metiches:** with `NEW_USER_REVIEW=1` (the default) a new account's Chismes are held (`status=held`). Only the author and the admin can see them, and the author gets the note "Waiting for a quick check before everyone sees it." They go live when the admin approves the person or the post, or gives them a badge. A blue badge also skips review from then on. Set `NEW_USER_REVIEW=0` to turn it off.
- **Admin alerts:** new sign-ups (on first verify), reports and held Chismes show up in the admin's 🔔 Alerts.
- Migration: `supabase/migrations/20261012200000_social_admin_badges.sql` (not applied). Apply it after `20261012190000_social_signup_consent.sql`.

### ☰ → Admin (admin only)
The admin's ☰ menu has an Admin section. Each page reuses the existing tools, and `_signed_in` in app.py also accepts the admin's Chisme session, so the /stats/* endpoints check it on the server:
- **📊 Analytics:** `/stats/api/summary` (visitors, opens, top stories) plus `GET /api/social/admin/stats` (new users, Chismes, reactions and comments, top Chismes this week, newest people).
- **📣 Sponsor posts:** the existing owner-posts composer (`/stats/posts`, with the Sponsored checkbox and pins), framed in the app.
- **🔔 Notifications:** a push to everyone through the existing `/stats/push/send` (it asks you to confirm first).
- **🛡️ Moderation:** reports, DMCA, New metiches (approve, post or remove, badge) and the Badges list.

### Theme
Every social screen takes its colors from the app's theme variables (`--card`, `--ink`, `--line`, `--near`, `--turq`, and the app's pink and orange). In Día de los Muertos (`html[data-season="muertos"]`) it also uses `--mq-plum` and `--marigold`, so when the season switches off (or with `THEME_OVERRIDE=off`) the social screens switch back with the rest of the app. The tests check that social.css has no hard-coded light backgrounds.

## Goonie sets these up himself
1. **Cloudflare R2** (needs a payment method on the free tier): bucket `chisme-media` with a public custom domain, plus
   a private bucket for quarantine. Then on Render: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
   `R2_BUCKET`, `R2_PUBLIC_BASE_URL`, `R2_QUARANTINE_BUCKET`. Turn on the CSAM Scanning Tool for that domain.
2. **Turnstile:** add the site in Cloudflare → Turnstile, then `TURNSTILE_SITE_KEY` + `TURNSTILE_SECRET_KEY`.
3. **DMCA agent:** done. Registered with the U.S. Copyright Office as **DMCA-1082743**; copyright complaints go to
   **Arnulfoled@outlook.com**. That's the built-in default on `/dmca` (`DMCA_AGENT_DEFAULT` in `social_api.py`);
   set `DMCA_AGENT_INFO` only to override the text (the email still becomes a link). Keep the Copyright Office
   listing current (renew it every 3 years).
   `/dmca` also shows the agent's full contact exactly as the registration lists it, built in as the defaults:
   Arnulfo Ledezma (Chisme), 912 FM 2537 Lot #5, San Antonio, TX 78221, (210) 837-2281, Arnulfoled@outlook.com.
   `DMCA_AGENT_NAME`, `DMCA_AGENT_ADDRESS` (new lines allowed) and `DMCA_AGENT_PHONE` override them; if the
   registration changes, update it at the Copyright Office and here together.
4. **Supabase:** review and apply the migration (not applied to production by this branch); set the Auth email
   template to send the 6-digit code (`{{ .Token }}`) through a custom SMTP sender; `SUPABASE_URL`,
   `SUPABASE_SERVICE_KEY`, `SUPABASE_PUBLISHABLE_KEY`; a `SOCIAL_SECRET`.
5. **Sign-ups:** `SOCIAL_SIGNUP_TESTERS=<your email>,<testers' emails>` now; `SIGNUPS_PUBLIC=1` once chisme.co
   sends the codes from a verified domain. Have a Texas attorney look over Plato's pages before launch (their own note).
6. **Uploads:** `SOCIAL_UPLOAD_TESTERS=<your @username>,<testers>` now; `UPLOADS_PUBLIC=1` only after chisme.co runs
   through Cloudflare with the CSAM Scanning Tool on (or `CSAM_SCAN_URL` points at a live scanner).
7. Optional: `CSAM_SCAN_URL` / `CSAM_SCAN_TOKEN` (PhotoDNA, Thorn Safer…), `SOCIAL_APPLE=1` / `SOCIAL_GOOGLE=1`.
   `SOCIAL_UPLOADS=0` pauses all uploads.
