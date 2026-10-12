<!-- NOT LEGAL ADVICE. This is a plain-English draft. Have a licensed Texas attorney review before launch. -->

# Chisme Privacy Policy

**Effective date:** October 12, 2026

This Privacy Policy explains what information Chisme collects, how we use it, who we share it with, and the choices you have. Chisme is a San Antonio news and entertainment app at chisme.onrender.com and, later, chisme.co (the "Service"), operated by Arnulfo Ledezma of San Antonio, Texas ("Chisme," "we," "us").

**The short version:**

- We collect what we need to run your account and show your posts.
- **We remove GPS/EXIF location data from photos you upload.**
- **We don't sell your personal information.** We don't share it for targeted advertising either.
- You can delete your account and content from inside the app.
- Much of what Chisme remembers without an account (settings, Tía chat history, saved spots, game scores) lives **on your phone**.
- **Your messages to Tía Chismosa go to Google's AI.** Don't type private information to her.
- Chisme sets no tracking or advertising cookies.
- Questions? Email **Arnulfoled@outlook.com**.

---

## 1. Who this covers

Browsing Chisme without an account (news, weather, videos, and games) is open to a general audience **13 and older**, and Chisme isn't directed to children under 13. **Accounts, social features, and Tía Chismosa chat are only for people 18 and older.** We don't knowingly collect personal information from children under 13, and we don't knowingly let anyone under 18 create an account or chat with Tía. If we learn we have collected information we shouldn't have (for example, an account belonging to someone under 18, or a real name a child under 13 put on the high-score board), we'll delete it. If you think a minor is using Chisme's accounts, social features, or Tía chat, email us.

If you're under 18: don't post a high score with your real name, and ask a parent before turning on notifications or tipping.

## 2. What we collect

### Information you give us

- **Account info:** your email address, and your password, which is stored scrambled (hashed) so we can't read it.
- **Profile info:** username, display name, profile photo, bio, and anything else you choose to add.
- **Content you post:** photos, videos (up to 60 seconds), memes, comments, reposts, likes, and reactions.
- **Social connections:** your Homies (mutual friend connections), friend requests, and the users you block.
- **Reports and messages to us:** reports you file about content or users, and anything you send us by email.

### Information collected automatically

- **Device and log info:** IP address, browser and device type, operating system, pages or screens you visit, and dates and times of activity. Our hosting and storage providers create these logs as part of running the Service.
- **Sign-in session data:** tokens stored in your browser (in cookies or local storage) to keep you logged in.
- **Approximate location:** we may estimate your general area (like city or region) from your IP address for security and to show local San Antonio content. We do **not** collect your precise GPS location. (If you choose to share your device location for weather and local content, see the next section for how we round it.)

### Location for weather and local content

- **What:** your approximate location, meaning latitude/longitude rounded to about 1 km, or a city or ZIP code you type. Only once, a location rounded to about 100 m is used to look up your neighborhood's name.
- **When:** only when you allow location in your browser or search for a place.
- **Why:** to show your forecast, National Weather Service (NWS) alerts, radar, nearby stories, nearest teams, events, food, and Tía's answers.
- **Where it goes:** it's saved on your device (local storage) and sent with each request to our server, which looks things up with the National Weather Service, OpenStreetMap Nominatim, Photon (komoot), and Zippopotam.us. Our server caches results by area, and our host's logs may briefly record request URLs.

### Notifications

- **What:** a push subscription (a push endpoint from your browser's push service), your area rounded to about 1 km, your time zone, and which alerts you want.
- **When:** only if you turn on notifications.
- **Why:** to send big local news (at most 2 a day) and NWS warnings and watches for your area.
- **Where it goes:** it's stored with our database provider (Upstash) until you turn notifications off, or until the push service tells us the subscription is gone. Turning notifications off deletes it.

### Tía Chismosa chats

When you chat with Tía, your messages go to our server and to Google. See Section 3 for the details.

### High scores

- **What:** a nickname (up to 12 characters), score, level, and time.
- **When:** only if you choose to save a Top 10 score in "The Juan That Got Away."
- **Why:** to show the public Top 10 board.
- **Where it goes:** it's stored with our database provider (Upstash) and **shown publicly.** Don't use your real name. We may remove or rename any entry. Ask us to delete yours at **Arnulfoled@outlook.com**, or tap Report on the board.

### Anonymous usage counts

- **What:** app opens (installed vs. browser), tab views, which public news stories are opened (headline and link), game plays, food video views, the *count* of Tía chats (never the text), donate-button taps, the Add-to-Home-Screen tip outcome, your city name (city level only), and how a visit arrived (the kind of site or app that sent you, like Facebook or Google, a link's campaign tag, the page you landed on, and the sending site's name, never the full address).
- **When:** while you use the app, **unless your browser sends Do Not Track or Global Privacy Control.**
- **Why:** to see what's useful and fix what isn't, and to know which posts help people find Chisme.
- **How:** a random ID made on your phone is turned into a salted one-way hash on our server and only *counted* (we can't list or reverse it). Daily counts are kept about 40 days. These counts don't include names, IP addresses, or tracking cookies.

### IP address and rate limits

Every request includes your IP address (that's how the internet works). We use it for security and rate limits (for example, Tía messages per hour). Our rate limits keep only a salted hash of your IP, for up to a day. Our hosting providers (Render and Cloudflare) process IP addresses and request logs under their own policies.

### Photo location data: stripped

Photos taken on phones often contain hidden "EXIF" metadata, which can include the exact GPS spot where a photo was taken. **When you upload a photo, we strip GPS and other EXIF location metadata before the photo is stored or shown to anyone.** Keep in mind that we can't remove location info that's visible in the photo or video itself (like a street sign or house number), so think before you post.

### Embedded content (YouTube and TikTok)

ChismeTV clips and other reposts may play through YouTube or TikTok embeds. When you view or play an embed, those companies may collect information about you (such as your IP address and viewing activity) and set their own cookies, under their own privacy policies. We don't control that.

## 3. Tía Chismosa (AI chat)

Tía Chismosa is Chisme's AI chat character. **You must be 18 or older to chat with her.**

- **What's sent:** your last messages (up to 12) and the stories, events, and scores the app is showing.
- **Where it goes:** to our server and to **Google (Gemini API)** to generate the reply. **Chisme doesn't store chats on its server.**
- **Google's free tier:** Chisme uses Google's free tier. Google's terms say Google may keep and use what's sent to improve its products, and **human reviewers may read it.** **Don't type private or sensitive information to Tía.**
- **On your phone only:** your chat history and the interests Tía learns are saved **only on your phone.** Settings > Forget me erases them.
- **Daily limit:** Tía gives up to 20 AI answers per phone per day. To track this, the app makes a random Tía device ID on your phone (not linked to your name or account). Our server keeps only a salted hash of it with a count, until about an hour after midnight Central time, and then it's gone. If the ID is missing, the limit uses your IP address the same way.
- **Safety:** Tía is an AI and can be wrong; always check the original story. She only talks about what's in the app and cites her sources. If a message mentions self-harm, Tía doesn't use AI and instead points to the **988 Suicide & Crisis Lifeline** (call or text 988, en español también), Crisis Text Line (text HOME to 741741), and 911. She won't give medical, legal, or financial advice.

## 4. What stays on your device

Chisme uses your browser's local storage to remember things like: your location and setup choices, theme, text size, default tab, reduce-motion, notification state, your Tía chat history and interests, your food feed preferences and saved spots, news you've already seen, game progress and best scores, your high-score nickname, a random anonymous ID used only for the anonymous counts, a random Tía device ID used only for her daily message limit, and your sign-in session if you have an account. You can clear all of it by clearing this site's data in your browser. Settings > Forget me and Reset my feed clear the Tía and feed data (except the Tía device ID, which is used only for her daily limit; clearing the site's data removes it too).

**Cookies:** Chisme itself sets no tracking or advertising cookies. The only cookies Chisme uses are for keeping you signed in and for the owner's private admin page.

## 5. Third-party content inside Chisme

When you open or play these, your browser connects **directly** to them, and they get your IP address and may set their own cookies or storage under their own policies:

- **YouTube:** videos play in YouTube's privacy-enhanced embedded player (youtube-nocookie.com). **Chisme uses YouTube API Services.** By watching YouTube videos in Chisme you agree to the YouTube Terms of Service (<https://www.youtube.com/t/terms>). Google's Privacy Policy: <https://policies.google.com/privacy>. Because some feed videos autoplay, YouTube may receive basic data when a video loads.
- **TikTok:** videos play in TikTok's official embed player (TikTok Privacy Policy: <https://www.tiktok.com/legal/privacy-policy>).
- **News pages:** stories you open may load inside Chisme's reader (only when the site allows it) or in a new tab. Images next to stories load from the publishers' and ESPN's servers.
- **Maps:** map tiles load from OpenStreetMap's tile servers, radar images come from RainViewer, and "Directions" opens Apple Maps or Google Maps.
- **Donations:** the tip buttons open Cash App or Buy Me a Coffee.

## 6. How we use your information

We use your information to:

- Create and secure your account and sign you in
- Show your profile and posts, and run features like likes, reactions, comments, reposts, and Homies
- Process uploads (for example, compressing video, limiting video to 720p, and stripping photo location data)
- Keep Chisme safe: review reports, enforce our [Terms](terms.md) and [Community Rules](rules-and-copyright.md), stop spam and abuse, and investigate security problems
- Show your local forecast, weather alerts, radar, and nearby news, sports, events, and food
- Answer your messages to Tía Chismosa
- Send notifications you asked for
- Show the public high-score board
- Count anonymous usage so we know what's useful
- Handle copyright notices and counter-notices
- Talk to you about your account, important changes, and responses to your messages
- Fix bugs and improve the Service
- Follow the law and respond to valid legal requests

## 7. What other users can see

Your username, display name, profile photo, bio, and the posts, comments, reactions, and reposts you share may be visible to other Chisme users and, depending on your settings and the feature, to people who aren't logged in. Your Homies list may be visible to others. High-score nicknames on the Top 10 board are public to everyone. People you block won't be able to interact with you on Chisme, but anything already public may have been seen, screenshotted, or shared before you blocked them.

## 8. Who we share information with

**We do not sell your personal information, and we do not share it for targeted advertising.**

We share information only in these situations:

- **Service providers** who help us run Chisme, and only to do that work for us:
  - **Supabase:** sign-in (email, password, and 6-digit email codes), user accounts, and our database
  - **Cloudflare (R2):** storing and delivering your photos and videos
  - **Render:** hosting the Chisme app and servers
  - **Email delivery:** to send sign-in codes and account emails
  - **Cloudflare (network):** along with Render, processes IP addresses and request logs
  - **Upstash:** database for push subscriptions, high scores, and anonymous counts
  - **Google Gemini API:** Tía's answers, and checking whether a news story is big enough for an alert
  - **Browser push services (Apple, Google, Mozilla):** delivering notifications
  - **NWS, OpenStreetMap Nominatim, Photon (komoot), and Zippopotam.us:** they receive the area being looked up, from our server, not from you
- **Sponsors and advertisers:** we show "Sponsored" posts, but we don't give sponsors your personal information. We may share combined, anonymous stats (like "this post got 2,000 views").
- **Legal and safety:** when we believe in good faith it's required by law, a court order, or a valid legal request; to protect someone's safety; or to investigate fraud or abuse. We report child sexual abuse material to the National Center for Missing & Exploited Children (NCMEC) as federal law requires.
- **Copyright notices:** if you send or receive a DMCA notice or counter-notice, we may forward it, including your contact info, to the other side as the law allows.
- **Business changes:** if Chisme is sold, merged, or reorganized, your information may transfer to the new owner, who will have to honor this policy.
- **With your permission:** any other time you tell us it's okay.

## 9. Tips and donations

Tips go through Cash App ($Slurmkaos) or Buy Me a Coffee (buymeacoffee.com/Chismoso). Those services handle your payment and their privacy policies apply. They may show the recipient's name to you, and may show your name to us. Chisme only counts that a donate button was tapped. We don't collect your payment details.

## 10. How long we keep information

- **While your account is open:** we keep your account info and content so the Service works.
- **When you delete a post:** it's removed from the Service; copies may remain in backups for a short time.
- **When you delete your account:** we delete your profile, posts, uploaded photos and videos, comments, reactions, and Homies connections. Deletion from live systems usually happens within about 30 days, and backup copies are cleared within about 90 days.
- **Notifications:** your push subscription and area are kept until you turn notifications off or the push service tells us the subscription is gone.
- **High scores:** kept until removed. The board keeps the top 500.
- **Anonymous daily counts:** kept about 40 days.
- **Rate-limit records:** the salted hash of your IP is kept up to a day, and the Tía device ID hash until about an hour after midnight Central time.
- **Tía chats:** not stored on our server. Google may keep what's sent under its free-tier terms (see the Tía Chismosa section).
- **What we may keep longer:** limited records we need for safety, fraud prevention, legal obligations, or disputes, such as records of bans, reports, copyright notices, and content we're legally required to keep (for example, material reported to NCMEC). We keep these only as long as needed.

## 11. Your choices and rights

- **Location:** deny it or change it any time in your browser or Settings > Location. Chisme then uses the city or ZIP you type, or San Antonio.
- **Notifications:** turn them off in Settings; that deletes your subscription and area from our server.
- **Anonymous counts:** turn on your browser's Global Privacy Control or Do Not Track, and Chisme sends none.
- **Tía chat history:** Settings > Forget me erases it from your phone.
- **High scores:** email **Arnulfoled@outlook.com** or tap Report on the board to delete your entry.
- **Access and update:** view and edit your profile info in the app.
- **Delete content:** delete your posts and comments at any time.
- **Delete your account:** use the in-app account deletion option. No email or phone call needed.
- **Get a copy or ask questions:** email **Arnulfoled@outlook.com** to ask for a copy of your personal information, ask us to correct or delete it, or ask about how we use it. We'll respond within 45 days. We may need to verify that you own the account first.
- **Appeal:** if we deny a privacy request, you can reply to appeal, and we'll explain our decision. Texas residents who are still unhappy after an appeal may contact the Texas Attorney General.
- **No discrimination:** we won't treat you differently for using your privacy rights.

## 12. Security

We use reasonable safeguards like encrypted connections (HTTPS), access controls, and the security features of our providers. No system is 100% secure, though, so we can't guarantee your information will never be accessed without permission. If a data breach affects you, we'll notify you as required by law.

## 13. Where your data is stored

Chisme is based in Texas, and our providers may store and process information in the United States and other countries where they operate. By using Chisme, you understand your information may be processed outside your home state or country.

## 14. Outside the U.S.

Chisme is run from the United States for U.S. users, and weather alerts only cover the U.S. **Chisme isn't offered in the European Economic Area, Switzerland, or the United Kingdom.**

## 15. Changes to this policy

We may update this Privacy Policy. If we make important changes, we'll tell you in the app or by email before they take effect. The "Effective date" at the top shows when it was last updated.

## 16. Contact us

Arnulfo Ledezma, Chisme
912 FM 2537 Lot #5, San Antonio, TX 78221
Email: **Arnulfoled@outlook.com**
