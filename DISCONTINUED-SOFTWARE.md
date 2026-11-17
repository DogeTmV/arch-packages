# Discontinued computer/phone software people still want

Research date: 2026-11-17. Scope: programs, services, and phone software that
were shut down or abandoned and for which there is evidence of continued demand
(nostalgia, replacement guides, preservation projects, active questions, or
revival efforts). Physical products, food, and games that are still published
are out of scope.

"Demand" here does **not** mean a product merely used to have users. Each entry
has a source showing people still look for it, miss it, or need a replacement.

This file is the research list. The original reimplementations built from it
live in [`projects/`](projects/) and are packaged in [`packages/`](packages/).
No upstream code, artwork, logos, or proprietary data were copied.

## Built in this repository

| Discontinued original | Original successor built here | What it does |
| --- | --- | --- |
| Google Reader | [`rssledger`](projects/rssledger/) | Local RSS/Atom reader with OPML import/export and read state |
| Yahoo! Pipes | [`pipeway`](projects/pipeway/) | JSON-configured feed/data pipeline with fetch/filter/sort/publish stages |
| AIM, MSN Messenger, Yahoo! Messenger, Hangouts | [`chathoard`](projects/chathoard/) | Unified chat-log archive, search, tags, HTML/Markdown export |
| Winamp, Google Play Music, MixRadio | [`minamp`](projects/minamp/) | Local playlist manager and playback front-end with M3U import/export |
| Picasa, Picture Manager, iPhoto, Aperture | [`photoatlas`](projects/photoatlas/) | Photo index, duplicate finder, tags, static HTML gallery |
| Netscape Navigator bookmarks, del.icio.us | [`bookmarkdeck`](projects/bookmarkdeck/) | Bookmark manager with Netscape HTML import/export |
| Google Notebook | [`notebox`](projects/notebox/) | Local notebook with tags, search, and Markdown/HTML export |
| Google Desktop, Beagle, Yahoo! Answers archives | [`desksearch`](projects/desksearch/) | Local full-text index with snippets and ranking |
| HyperCard | [`cardstack`](projects/cardstack/) | Linked text card stacks with HTML/Markdown export |
| Palm Memo Pad / HotSync workflows | [`memopad`](projects/memopad/) | Memo database with categories, search, and import/export |
| Nokia Snake | [`snakecell`](projects/snakecell/) | Deterministic terminal Snake with a headless demo mode |
| GeoCities, FrontPage, iWeb | [`homestead`](projects/homestead/) | Static personal-site generator with themes |
| Google Image Charts API | [`chartlet`](projects/chartlet/) | CSV-to-SVG bar/line/pie/sparkline charts |
| Microsoft Encarta | [`knowbase`](projects/knowbase/) | Offline article encyclopedia with search and export |
| Google Wave | [`threadweave`](projects/threadweave/) | mbox importer and threaded conversation browser |
| Classic X11/Windows screensavers | [`starsaver`](projects/starsaver/) | Deterministic starfield, digital-rain, and pipes animations |
| Google Now | [`contextcards`](projects/contextcards/) | Local, date-driven context digest from user-owned JSON data |
| Google Trips | [`tripplan`](projects/tripplan/) | Offline itineraries with ICS/Markdown/JSON export |
| Google Cloud Print | [`printbridge`](projects/printbridge/) | Authenticated loopback HTTP-to-`lp` print bridge |

Anything marked **not built** below needs a dead server, proprietary protocol,
licensed content, hardware access, or a full GUI/browser engine to be a real
replacement; shipping a stub would be worse than leaving it documented.

## Web, feed, and social software

1. **Google Reader** — Web RSS reader. Announced March 2013, shut July 1, 2013;
   Google cited declining use and prioritized Google+. Demand: [The Verge's
   10-year retrospective](https://www.theverge.com/23778253/google-reader-death-2013-rss-social)
   and an [Android Authority poll](https://www.androidauthority.com/killed-by-google-apps-i-miss-most-3534674/)
   where Reader tied for first at 24%. **Built: `rssledger`.**

2. **Yahoo! Pipes** — Visual feed/data mashup tool. Shut September 30, 2015.
   Demand: [Hacker News eulogy](https://news.ycombinator.com/item?id=9660682)
   and a [2026 alternatives guide](https://www.import.io/post/5-yahoo-pipes-alternatives-that-are-actually-better-than-pipes)
   noting the need never went away. **Built: `pipeway`.**

3. **Google Wave** — Collaborative communication/document platform. Development
   ended 2010, service shut 2012. Demand: [How-To Geek retrospective](https://www.howtogeek.com/the-forgotten-google-app-that-was-way-ahead-of-its-time/).
   **Built: `threadweave`** (offline threaded conversation browser inspired by
   its conversation model).

4. **Google Notebook** — Web clipping and research notebook. Development ended
   2009, export-only 2011, shut 2012. Demand: [Lifehacker's migration guide](https://lifehacker.com/where-to-go-when-google-notebook-goes-down-5131781).
   **Built: `notebox`.**

5. **Yahoo! Answers** — Q&A archive. Shut June 30, 2021. Demand: [ArchiveTeam
   preservation wiki](https://wiki.archiveteam.org/index.php/Yahoo!_Answers)
   and the [Internet Archive dump](https://archive.org/details/archiveteam_yahooanswers?sort=-publicdate).
   **Partly built: `desksearch`** provides offline full-text search over
   exported text archives; it is not a Q&A upload site.

6. **StumbleUpon** — Random web-discovery toolbar. Shut June 30, 2018. Demand:
   [Mashable](https://mashable.com/article/stumbleupon-died-shut-down) and
   [FastCompany](https://www.fastcompany.com/40577345/rip-stumbleupon-youll-be-missed-for-the-simpler-internet-you-once-represented)
   mourned its simpler-web discovery model. **Not built** — a discovery service
   needs a large shared corpus, not just a local CLI.

7. **Google+** — Social network. Consumer service shut April 2, 2019. Demand:
   [Android Authority eulogy](https://www.androidauthority.com/a-eulogy-of-google-plus-913743/).
   **Not built** — social graph/network effect cannot be recreated locally.

8. **Orkut** — Social network. Shut September 30, 2014. Demand: renewed revival
   interest in [TechCrunch](https://techcrunch.com/2026/10/09/remember-orkut-its-founder-wants-to-bring-it-back/)
   and [India Today](https://www.indiatoday.in/technology/news/story/orkut-coming-back-founder-wants-to-relaunch-the-social-network-with-a-new-purpose-3013249-2026-10-09).
   **Not built** — hosted community service.

## Phone-era and mobile software

9. **Google Play Music** — Cloud music locker. Shut 2020 during migration to
   YouTube Music. Demand: [SlashGear farewell](https://www.slashgear.com/google-play-music-well-miss-you-moving-on-is-just-an-option-31645256/)
   and [FOSSBytes alternatives](https://fossbytes.com/best-google-play-music-alternatives-list/).
   **Partly built: `minamp`** handles local libraries and playlists, not cloud
   lockers or streaming.

10. **Google Now** — Proactive phone cards. Folded into Google/Discover/Assistant
    around 2015. Demand: tied for first at 24% in the [Android Authority poll](https://www.androidauthority.com/killed-by-google-apps-i-miss-most-3534674/).
    **Built: `contextcards`** — a local digest fed by user-owned JSON data, not
    an account-based assistant.

11. **Inbox by Gmail** — Task-oriented email client. Shut 2019. Demand: 21% in
    the [Android Authority poll](https://www.androidauthority.com/killed-by-google-apps-i-miss-most-3534674/)
    missed it most. **Not built** — needs a live mail backend.

12. **Google Trips** — Offline travel itinerary app. Shut August 5, 2019.
    Demand: described as leaving "the largest void" in [Android Authority](https://www.androidauthority.com/killed-by-google-apps-i-miss-most-3534674/)
    and [Thrifty Traveler](https://thriftytraveler.com/guides/google-trips-where-to-find-info/).
    **Built: `tripplan`** — offline itineraries with calendar export; manual
    entry replaces closed reservation APIs.

13. **Android Auto for phone screens** — Car UI for older cars. Discontinued
    2022. Demand: 15% in the [Android Authority poll](https://www.androidauthority.com/killed-by-google-apps-i-miss-most-3534674/).
    **Not built** — needs a phone UI/kiosk integration and navigation intents.

14. **Trusted Contacts** — Consent-based live location sharing. Shut 2020.
    Demand: [Android Authority poll](https://www.androidauthority.com/killed-by-google-apps-i-miss-most-3534674/).
    **Not built** — location sharing needs a trusted remote endpoint.

15. **Google Cloud Print** — Cloud/local printing. Shut December 31, 2020.
    Demand: [PaperCut's migration guide](https://www.papercut.com/blog/print_tips/what-to-do-after-google-cloud-print-end-of-life/)
    documents mass migration. **Built: `printbridge`** — an authenticated
    loopback HTTP endpoint that feeds local `lp`/CUPS queues.

16. **Google Hangouts** — Chat/video. Shut November 1, 2022. Demand: in a
    [1,479-vote poll](https://www.androidauthority.com/google-hangouts-2739112/),
    71% said it was the best. **Partly built: `chathoard`** preserves and
    searches exported logs; it is not a live chat service.

17. **Nokia PC Suite / Ovi Suite** — Phone-to-PC sync and backup. Retired around
    2011/2014. Demand: [users still ask how to download it](https://www.reddit.com/r/Nokia/comments/hbz4we/nokia_pc_suite_anyway_to_download/).
    **Not built** — requires proprietary device protocols and drivers.

18. **Palm Desktop / HotSync** — PDA sync conduits. Faded after Palm's webOS
    transition. Demand: [64-bit sync guide](https://superuser.com/questions/1190871/heres-how-to-synchronize-an-old-palm-os-device-with-a-modern-64-bit-windows-pc),
    [palmDB HotSync help](https://palmdb.net/help/hotsync-setup), [Arch Wiki Palm](https://wiki.archlinux.org/title/Palm).
    **Partly built: `memopad`** covers the memo-data side, not HotSync transport.

19. **BBM (BlackBerry Messenger)** — PIN-based phone messaging. Consumer service
    shut May 31, 2019. Demand: [CrackBerry EOL thread](https://forums.crackberry.com/general-blackberry-news-discussion-rumors-f2/bbm-end-life-1197498/)
    and [The Independent](https://www.independent.co.uk/tech/bbm-not-working-blackberry-messenger-shut-down-date-a8938701.html).
    **Not built** — a messenger without peers has little value.

20. **BlackBerry Blend** — Phone-to-desktop bridge. EOL 2018. Demand:
    [CrackBerry revival discussion](https://crackberry.com/should-blackberry-revive-blend-and-bring-it-android-phones).
    **Not built** — needs a phone-side companion app.

21. **webOS App Catalog** — Mobile app store. Shut with the platform after 2011.
    Demand: third-party [restoration of the catalog and SDK](https://www.osnews.com/story/134943/webos-app-catalog-sdk-and-more-restored-by-3rd-party/)
    and [appcatalog.webosarchive.org](https://appcatalog.webosarchive.org/).
    **Not built** — the community restoration already exists; packaging a
    duplicate would not help.

22. **MixRadio / Nokia Music** — Phone music discovery. Shut December 2016.
    Demand: [Windows Central](https://www.windowscentral.com/line-kills-mixradio)
    and [Windows Phone reactions](https://www.reddit.com/r/windowsphone/comments/4613d8/the_end_of_mixradio_as_line_quietly_kills_off/).
    **Partly built: `minamp`** can sort/queue local libraries and export M3U
    mixes; it has no streaming catalog.

## Messaging, browsers, and desktop utilities

23. **AOL Instant Messenger (AIM)** — Desktop IM. Shut December 15, 2017.
    Demand: [Smithsonian retrospective](https://www.smithsonianmag.com/innovation/in-25-years-since-its-launch-aol-instant-messenger-has-never-been-away-180980086/)
    and [Ars Technica farewell](https://arstechnica.com/gaming/2017/12/aol-instant-messenger-is-no-more-but-the-memories-will-last-forever/).
    **Partly built: `chathoard`** (log archive/export).

24. **MSN Messenger / Windows Live Messenger** — Desktop IM. Phased out
    2013-2014; community "Escargot" later restored parts. Demand: [Microsoft Q&A
    in 2026](https://learn.microsoft.com/en-us/answers/questions/4169333/hi-is-there-any-way-of-accessing-old-msn-messenger)
    and [revival guide](https://techqe.com/can-you-still-access-msn-messenger-the-2026-revival-guide/).
    **Partly built: `chathoard`.**

25. **Yahoo! Messenger** — Desktop IM. Shut July 17, 2014. Demand: [Lifewire
    legacy coverage](https://www.lifewire.com/yahoo-messenger-1949913) and
    [AlternativeTo alternatives](https://alternativeto.net/software/yahoo-messenger/).
    **Partly built: `chathoard`.**

26. **Netscape Navigator** — Browser. Final releases ended 2008. Demand:
    [Hackaday's "Zombie Netscape won't die"](https://hackaday.com/2026/01/27/zombie-netscape-wont-die/).
    **Partly built: `bookmarkdeck`** for the bookmark workflow; a new browser
    engine is out of scope.

27. **Winamp** — Skinned music player. Classic development effectively ended
    after 5.572 in 2013. Demand: [Engadget reports 40M+ active users and a
    2027 revival](https://www.engadget.com/2259236/winamp-coming-back-2027-deezer-partnership-streaming-music/).
    **Built: `minamp`** (playlist/queue/playback front-end, no legacy skins).

28. **Adobe Flash Player** — Browser plugin/runtime. EOL December 31, 2020.
    Demand: [Adobe community questions about old SWFs](https://community.adobe.com/questions-638/how-can-i-access-old-flash-swf-files-after-flash-player-was-discontinued-1631844).
    **Not built** — reimplementing a browser plugin is both unsafe and
    incompatible with modern browsers; isolated archival playback is a
    separate, larger project.

29. **Windows Movie Maker** — Desktop video editor. Discontinued January 2017.
    Demand: [Digital Citizen's 2026 archived-installer guide](https://www.digitalcitizen.life/classic-windows-movie-maker-can-still-run-on-windows-11-through-a-free-archived-installer/).
    **Not built** — ffmpeg already provides the underlying trim/concat
    operations; a full timeline UI is out of scope.

30. **Microsoft Office Picture Manager** — Batch photo manager. Removed after
    Office 2010/2013. Demand: [How-To Geek installation guide](https://www.howtogeek.com/install-microsoft-office-picture-manager-on-windows-11/)
    and [sysadmin replacement threads](https://www.reddit.com/r/sysadmin/comments/75za7i/office_2010_picture_manager_replacement/).
    **Partly built: `photoatlas`** (index/find/gallery, not destructive edits).

31. **Picasa** — Desktop photo organizer. Desktop client retired 2016. Demand:
    [AlternativeTo](https://alternativeto.net/software/picasa/), [ShotKit](https://shotkit.com/best-picasa-alternative/),
    [Reddit photography discussion](https://www.reddit.com/r/photography/comments/5l4py4/picasa_is_dead_is_there_a_good_replacement/).
    **Built: `photoatlas`.**

32. **iPhoto** — Apple photo manager. Discontinued 2015. Demand: the
    [Retroactive project](https://github.com/cormiertyshawn895/Retroactive)
    exists to keep it running on modern macOS. **Partly built: `photoatlas`.**

33. **Aperture** — Pro photo/RAW manager. Discontinued April 2015. Demand:
    [PetaPixel's 2025 report on demand for Aperture-inspired tools](https://petapixel.com/2025/04/28/if-you-miss-aperture-on-mac-musebox-could-be-the-answer/)
    and [Retroactive](https://github.com/cormiertyshawn895/Retroactive).
    **Partly built: `photoatlas`** (metadata/keyword indexing, not RAW editing).

34. **iWeb** — Desktop website builder. Development stopped 2011, MobileMe
    hosting ended 2012. Demand: [Apple Community question](https://discussions.apple.com/thread/252514674)
    and [Macworld on iWeb never being forgotten](https://www.macworld.com/article/3011551/blast-from-the-past-iweb-and-aperture-live-on-for-now-on-apple-com.html).
    **Built: `homestead`.**

35. **Adobe Fireworks** — Raster/vector web graphics tool. Discontinued 2013.
    Demand: [Graphic Design StackExchange successor question](https://graphicdesign.stackexchange.com/questions/51476/which-modern-software-is-a-decent-successor-replacement-for-fireworks)
    and [Adobe Community question](https://community.adobe.com/questions-635/is-fireworks-no-longer-available-686166).
    **Not built** — a layer-based vector/raster editor is a large GUI project.

36. **Microsoft FrontPage** — WYSIWYG web authoring. Discontinued December 2006.
    Demand: [2023 "Still using FrontPage?" guide](https://www.ait.com/still-using-frontpage-great-frontpage-alternatives/)
    and [Microsoft Q&A replacement requests](https://learn.microsoft.com/en-us/answers/questions/3747355/frontpage-replacement).
    **Built: `homestead`** (snippet/page generator, no WYSIWYG canvas).

37. **TrueCrypt** — Disk encryption. Development ended May 2014. Demand:
    [Ask Leo](https://askleo.com/what-happened-to-truecrypt-and-what-do-i-use-instead/),
    [The Guardian](https://www.theguardian.com/technology/2014/may/30/encryption-software-truecrypt-closes-doors),
    [privacy-community threads](https://www.reddit.com/r/privacytoolsIO/comments/ehhkyw/still_using_truecrypt_what_to_use_now/).
    **Not built** — security-sensitive container code should be audited by
    specialists; use the maintained VeraCrypt/LUKS forks instead.

38. **Opera 12 / Presto** — Browser generation. Presto abandoned with Opera 15
    in 2013. Demand: [Opera forum thread](https://forums.opera.com/topic/52/what-happens-to-opera-12-and-presto-engine)
    and [retro interest](https://rip.so/opera-presto.html). **Not built** — a
    browser engine is far beyond a small package.

## Additional discontinued tools found in follow-up research

39. **HyperCard** — Apple hypermedia stack authoring. Last major release 1992,
    discontinued 2004. Demand: ["Mourned HyperCard for 25 years"](https://www.reddit.com/r/VintageApple/comments/u0j2ox/mourned_hypercard_for_25_years_but_was_it/),
    [CNET on TileStack bringing stacks to the web](https://www.cnet.com/tech/services-and-software/tilestack-hypercard-comes-back-from-the-dead-and-onto-the-web/),
    [TidBITS on the HyperCard-shaped gap](https://tidbits.com/2026/08/14/decades-after-hypercard-ai-is-democratizing-development-again/).
    **Built: `cardstack`.**

40. **Google Desktop Search** — Desktop full-text search. Discontinued 2011.
    Demand: [replacement guides](https://www.getfossick.com/blog/google-desktop-search-replacement),
    [Software Recommendations question](https://softwarerecs.stackexchange.com/questions/11513/google-desktop-search-replacement-for-windows).
    **Built: `desksearch`.**

41. **Beagle** — GNOME desktop search. Stalled in 2009. Demand: still referenced
    in Linux desktop-search replacement discussions and forks. **Built:
    `desksearch`** as a portable, index-file-based successor.

42. **Microsoft Encarta** — CD-ROM encyclopedia. Discontinued 2009. Demand:
    [SlashGear retrospective](https://www.slashgear.com/1621872/why-microsoft-discontinued-encarta-what-happened/),
    [Microsoft Q&A "what replaces Encarta?"](https://learn.microsoft.com/en-us/answers/questions/2415027/what-replaces-encarta-since-it-was-discontinued).
    **Built: `knowbase`** with original sample articles, no copied content.

43. **Google Image Charts API** — URL-based chart images. Deprecated 2012,
    retired 2015/2019. Demand: [Stack Overflow replacement questions](https://stackoverflow.com/questions/16003624/google-chart-images-replacement)
    and [migration guides](https://quickchart.io/documentation/migrating-from-google-image-charts/).
    **Built: `chartlet`** (local CSV-to-SVG charts).

44. **Nokia Snake (and friends)** — Bundled phone games. Demand: enduring
    nostalgia for the monochrome Nokia-era games and their simple deterministic
    gameplay. **Built: `snakecell`.**

45. **Del.icio.us** — Social bookmarking. Declined after Yahoo changes and shut
    down in 2017. Demand: long-running requests for local/social bookmark
    replacements. **Built: `bookmarkdeck`** (local, Netscape-format compatible).

46. **Classic X11/Windows screensavers (Pipes, Digital Rain, Starfield)** —
    Ambient desktop animations. Demand: retro-nostalgia demand and ports to
    modern systems. **Built: `starsaver`** as deterministic terminal renders.

## Selection notes

- Favored products with concrete 2020s evidence: polls, active replacement
  questions, preservation projects, or revival announcements.
- Favored workflows that reduce to local data plus a small CLI/TUI, which is
  realistic for original Arch packages built from Python's standard library.
- Avoided shipping non-functional stubs for services that fundamentally need
  other people, dead servers, proprietary protocols, licensed content, or a
  full browser/GUI engine.
- Names, code, file formats, and documentation are original. Trademarks are
  used only to describe the inspiration, never claimed as our own.
