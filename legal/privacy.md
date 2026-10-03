# Chisme Privacy Policy


**Effective date:** <mark class="todo">TODO: effective date (the day this is published)</mark>
**Who we are:** Chisme ("Chisme", "we", "us") is a free local news, weather, sports, food, events and games web app at <https://chisme.onrender.com>, run by Chisme (San Antonio, TX). Contact: [bexartalkradio@gmail.com](mailto:bexartalkradio@gmail.com) · <mark class="todo">TODO: mailing address or P.O. box</mark>.

**The short version:**
- No accounts, no ads, no tracking cookies, and we don't sell or share your info for advertising.
- Most of what Chisme remembers (settings, chat history, saved spots, game scores) lives **on your phone**.
- Some things have to reach our server, or the services we use, to work. Your approximate location gets you local weather and news. Your messages to Tía go to Google's AI. A push subscription lets us send alerts. A high-score name is shown on a public board.

## 1. What we collect and why

| What | When | Why | Where it goes / how long |
|---|---|---|---|
| **Approximate location** (latitude/longitude rounded to about 1 km, or a city/ZIP you type; about 100 m only once, to look up your neighborhood's name) | When you allow location or search a place | Forecast, NWS alerts, radar, nearby stories, nearest teams, events, food, Tía's answers | Saved on your device (`localStorage`). Sent with each request to our server, which looks things up with the National Weather Service, OpenStreetMap Nominatim, Photon (komoot) and Zippopotam.us. Our server caches results by area; our host's logs may briefly record request URLs (see §4). |
| **Notification subscription** (a push endpoint from your browser's push service), your area rounded to about **1 km**, your time zone, and which alerts you want | Only if you turn on notifications | To send big local news (at most 2 a day) and NWS warnings/watches for your area | Stored on our database provider (Upstash) until you turn notifications off, or until the push service tells us the subscription is gone. Turning notifications off deletes it. |
| **Messages to Tía Chismosa** (your last messages, up to 12, and the stories/events/scores the app is showing) | When you chat with Tía | To answer you | Sent to our server and to **Google (Gemini API)** to generate the reply. **Chisme doesn't store chats on its server.** <mark class="todo">TODO: owner: confirm the Gemini tier and keep the matching sentence</mark> On Google's free tier, Google's terms say Google may keep and use what's sent to improve its products, and human reviewers may read it. (On the paid tier, Google processes it under its paid-service terms and keeps it briefly for abuse monitoring.) **Don't type private or sensitive information to Tía.** Your chat history and the interests Tía learns are saved **only on your phone**; Settings → Forget me erases them. |
| **High-score name** (a nickname up to 12 characters), score, level, time | If you choose to save a Top 10 score in "The Juan That Got Away" | To show the public Top 10 board | Stored on our database provider. **Shown publicly.** Don't use your real name. We may remove or rename any entry. Ask us to delete yours at bexartalkradio@gmail.com, or tap Report on the board. |
| **Anonymous usage counts**: app opens (installed vs browser), tab views, which public news stories are opened (headline + link), game plays, food video views, the *count* of Tía chats (never the text), donate-button taps, the Add-to-Home-Screen tip outcome, and your city name (city level only) | While you use the app, **unless your browser sends Do Not Track or Global Privacy Control** | To see what's useful and fix what isn't | A random ID made on your phone is turned into a salted one-way hash on the server and only *counted* (we can't list or reverse it). Daily counts are kept about 40 days. No names, no IP addresses, no tracking cookies. |
| **IP address** | Every request (that's how the internet works) | Security and rate limits (for example, Tía messages per hour) | Our rate limits keep only a salted hash of your IP, for up to a day. Our hosting providers (Render, Cloudflare) process IPs and request logs under their own policies. |
| **Tía device ID** (a random ID made on your phone, not linked to your name or account) | When you chat with Tía | Tía's daily limit (20 AI answers per phone per day) | Our server keeps only a salted hash of it with a count, until about an hour after midnight Central time, then it's gone. If it's missing, the limit uses your IP the same way. |

We do **not** ask for or collect your name, email, phone number, contacts, photos, or payment details. Donations happen on Cash App or Buy Me a Coffee, not in Chisme (see §5).

## 2. What stays on your device
Chisme uses your browser's local storage (not tracking cookies) to remember things like: your location and setup choices, theme, text size, default tab, reduce-motion, notification state, your Tía chat history and interests, your food feed preferences and saved spots, news you've already seen, game progress and best scores, your high-score nickname, a random anonymous ID used only for the counts above, and a random Tía device ID used only for her daily message limit. You can clear all of it by clearing this site's data in your browser. Settings → "Forget me" and "Reset my feed" clear the Tía and feed data (except the Tía device ID, which is used only for her daily limit; clearing the site's data removes it too).

**Cookies:** Chisme itself sets no tracking or advertising cookies. (The only Chisme cookies are for the owner's private admin page.)

## 3. Third-party content inside Chisme
When you open or play these, your browser connects **directly** to them, and they get your IP address and may set their own cookies or storage under their own policies:
- **YouTube** videos play in YouTube's privacy-enhanced embedded player (youtube-nocookie.com). **Chisme uses YouTube API Services.** By watching YouTube videos in Chisme you agree to the YouTube Terms of Service (<https://www.youtube.com/t/terms>). Google's Privacy Policy: <https://policies.google.com/privacy>. Because some feed videos autoplay, YouTube may receive basic data when a video loads.
- **TikTok** videos play in TikTok's official embed player (TikTok Privacy Policy: <https://www.tiktok.com/legal/privacy-policy>).
- **News pages** you open may load inside Chisme's reader (only when the site allows it) or in a new tab. Images next to stories load from the publishers' and ESPN's servers.
- **Maps**: map tiles load from OpenStreetMap's tile servers; radar images from RainViewer; "Directions" opens Apple Maps or Google Maps.
- **Donations** open Cash App or Buy Me a Coffee.

## 4. Who we share with
We don't sell your personal information, share it for targeted advertising, or use it to build profiles about you. We share only what's needed to run Chisme with these service providers:
- Render and Cloudflare (hosting and network; they process IPs and request logs)
- Upstash (database for push subscriptions, high scores and anonymous counts)
- Google Gemini API (Tía's answers, and checking whether a news story is big enough for an alert)
- Browser push services (Apple, Google, Mozilla) to deliver notifications
- NWS, OpenStreetMap Nominatim, Photon (komoot) and Zippopotam.us (they receive the area being looked up, from our server, not from you)

We may also disclose information if the law requires it, or to protect people's safety or Chisme's security.

## 5. Donations
Tips go through Cash App ($Slurmkaos) or Buy Me a Coffee (buymeacoffee.com/Chismoso). Those services handle your payment and their privacy policies apply. They may show the recipient's name to you, and may show your name to us. Chisme only counts that a donate button was tapped.

## 6. Children
Chisme is a general-audience app and isn't directed to children under 13. Don't post a high score with your real name, and ask a parent before turning on notifications. <mark class="todo">TODO: owner: decide whether Tía's AI chat is 18+ (legal audit H3)</mark> If you believe a child under 13 has given us personal information (for example, a real name on the high-score board), email bexartalkradio@gmail.com and we'll delete it.

## 7. Tía Chismosa (AI) and safety
Tía is an AI chatbot. She only talks about what's in the app, cites her sources, and can be wrong. Always check the original story. If a message mentions self-harm, Tía doesn't use AI and instead points to the **988 Suicide & Crisis Lifeline** (call or text 988, en español también), Crisis Text Line (text HOME to 741741) and 911. She won't give medical, legal or financial advice.

## 8. Your choices and rights
- **Location:** deny it or change it any time in your browser or Settings → Location (Chisme then uses the city/ZIP you type, or San Antonio).
- **Notifications:** turn them off in Settings; that deletes your subscription and area from our server.
- **Anonymous counts:** turn on your browser's Global Privacy Control or Do Not Track, and Chisme sends nothing.
- **Delete / access:** email bexartalkradio@gmail.com to ask what we have tied to you (usually nothing we can link to you), or to delete a high-score entry. We respond within 30 days. Depending on where you live (for example, Texas, California or other US states), you may have rights to access, correct, delete, or opt out. We honor those requests even where the law doesn't require it. We don't sell personal data or use it for targeted ads.

## 9. Security and retention
Data in transit is encrypted (HTTPS). We keep server-side data only as long as described above: push subscriptions until you unsubscribe, high scores until removed (the board keeps the top 500), and anonymous daily counts about 40 days. No system is perfectly secure.

## 10. Outside the U.S.
Chisme is run from the United States for U.S. users, and weather alerts only cover the U.S. <mark class="todo">TODO: owner: if Tía stays on Gemini's free tier, say Chisme isn't offered in the EEA, Switzerland or the UK</mark>

## 11. Changes
If we change this policy, we'll update the date above and, for big changes, show a note in the app.

## 12. Contact
Chisme (San Antonio, TX) · [bexartalkradio@gmail.com](mailto:bexartalkradio@gmail.com) · <mark class="todo">TODO: mailing address or P.O. box</mark> · San Antonio, Texas.
