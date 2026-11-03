# Audit of cleaned data


## games (137,725 rows)

- **games · titles with HTML entities:** 0
- **games · titles with ™/®/©:** 1,954 — strip for matching only (title_norm)
  - e.g. Prince of Persia: Warrior Within™; Dungeon of the ENDLESS™; Cold Fear™; LEGO® Harry Potter: Years 1-4; LEGO® MARVEL's Avengers DLC - The Masters of Evil Pack; Just Cause™ 3 - Combat Buggy
- **games · titles with control/zero-width chars:** 0
- **games · titles > 100 chars:** 51
  - e.g. Sakuya Izayoi Gives You Advice And Dabs: Nitori Kawashiro Offers You Advice In Exchange Fo; Movavi Video Suite 2023 Steam Edition - An all-in-one video maker: an editor converter scr; Attack on Titan 2: Final Battle Upgrade Pack / A.O.T. 2: Final Battle Upgrade Pack / 進撃の巨人; JoJo's Bizarre Adventure: All-Star Battle R Jolyne Cujoh Costume Green Dolphin Street Stat; Touhou Blooming Chaos 2 - Chara Pack 2:Flandre Scarlet/Komeji Koishi/Aki Minoriko/Tsukumo ; Demon Slayer -Kimetsu no Yaiba- The Hinokami Chronicles: Tanjiro Zenitsu & Inosuke (Entert
- **games · titles that look like placeholders:** 206
  - e.g. 天师; 171; 红月; Be; 1849; 2048
- **games · descriptions containing HTML tags:** 18
  - e.g. <p>The small country of Arulco has been taken over by a merciless dictator - and only you ; This game is a cat personification reasoning game. Players will play as 'Detective Cat' ta; <Futanari's Sex World!> It tells the story of the protagonist, Julie, who is summoned to a; <The Longed-for Revenge of Undecember> is a horror game based on a true incident. Dreams d; <p>The small country of Arulco has been taken over by a merciless dictator - and only you ; <DESTROY> enemies. <COLLECT> orbs. <COMPETE> on leaderboards. <INITIALIZE>
- **games · descriptions containing HTML entities:** 0
- **games · descriptions < 20 chars (non-empty):** 280
  - e.g. apolitical; Lead. Fight. Win.; God Test; He's back!; Montaro is a DOGE.; 和机器人妹子（傻子）谈！！恋！！爱！！
- **games · descriptions shared by 2+ apps:** 1,975 — template text; weak content signal
  - e.g. Find the objects that are hidden on the map.; This game is a classic puzzle game with several levels of difficulty and beautiful arts. E; This is a casual puzzle game, where the position of each game image is random and can be r; This game is a classic memory game with several levels of difficulty and beautiful arts. E; Collect a 3D puzzle, transferring things to the right places to create a beautiful place.; What could be more beautiful than hentai?
- **games · descriptions mostly non-Latin (>30% non-ASCII):** 2,065 — embedding model is English-only
  - e.g. Three Kingdoms 2019 阿达三国志2019 横版; 古剑奇谭二(GuJian2); 東方憑依華 ～ Antinomy of Common Flowers.; Bishojo Mangekyo Kotowari to Meikyu no Shojo; 猎魔者战纪; 风信楼
- **games · release_date missing:** 2,139
- **games · release_date in the future (unreleased):** 0 — can't be played yet
- **games · release_date before 1980:** 0
- **games · kaggle_price_regular > $150:** 20
  - e.g. 3DF Zephyr Lite Steam Edition $199.99; Clickteam Fusion 2.5 Developer Upgrade $299.99; Hidden Post-Apocalyptic 3 Top-Down 3D $199.99; Break Everything - Park $199.99; VEGAS 19 Edit Steam Edition $199.99; Houdini Indie $269.99
- **games · fronkon_price > $150:** 292
  - e.g. 3DF Zephyr Lite Steam Edition $199.2; Break Everything - Living room $199.99; Tanks Battle $199.99; Hidden Harbor 2 Top-Down 3D $199.99; 3D PUZZLE - Castle $199.99; Tanks Logic $199.99
- **games · Kaggle vs Fronkon regular price differ > 50%:** 18,898 — prices change over time; IsThereAnyDeal is the live source anyway
  - e.g. Prince of Persia: Warrior Within™; Monaco: What's Yours Is Mine; Escape Dead Island; Dungeon of the ENDLESS™; Hyperdimension Neptunia Re;Birth1; The Sum of All Fears
- **games · positive_ratio outside 0–100:** 0
- **games · owners_lo > owners_hi:** 0
- **games · tag lists with duplicates:** 0
- **games · tag spellings differing only by case/space:** 0
- **games · tags used by < 5 games:** 1 — vocabulary 441
  - e.g. Coding
  - item_type: game 114,537, playtest 8,131, dlc 8,078, unknown 4,631, software 1,769, removed 336, advertising 141, video 44, tool 23, music 19, mod 8, demo 7, hardware 1
- **games · typed 'tool' by the name rule:** 23 — check for false positives like 'Beta Squad' or 'Test Drive'
  - e.g. Lambda Wars Dedicated Server; Loadout Campaign Beta; Songs2See Editor; Terrain Test; Savage Resurrection Dedicated Server; Tower Wars Editor
- **games · duplicate titles (title_norm):** 3,393
  - e.g. 1; ➕1️⃣; +1%; 10 Seconds; 10 seconds; 100$
- **games · adult/sexual content (Fronkon age ≥ 18, notes or tags):** 9,382 — flag; exclude by default
  - Fronkon tags type: ndarray

## interactions_kaggle (41,154,753 rows)

- **kaggle · app_id not in games:** 0
- **kaggle · review_date in the future:** 0
- **kaggle · review_date before game's release:** 2,996,565
- **kaggle · review > 30 days before release (early access/beta keys or bad release date):** 2,845,352
  - e.g. 鬼谷八荒 Tale of Immortal; Mount & Blade II: Bannerlord; Paladins®; Unturned; Rust; DayZ
- **kaggle · not a game (is_game False) incl. unresolved types:** 1,128,787
- **kaggle · user-days with ≥ 50 reviews (bot/bulk-review pattern):** 887
- **kaggle · users with any ≥ 50-review day:** 729
- **kaggle · users with ≥ 1,000 reviews:** 55
  - e.g. 3023; 3392; 3479; 3840; 4152; 6045
- **kaggle · users (≥10 reviews) whose playtime is identical on every game:** 0 — copy-paste/bot
- **kaggle · helpful > 10,000:** 102

## interactions_mcauley (5,094,082 rows)

- **mcauley · app_id not in games:** 0
- **mcauley · 2-week playtime > lifetime playtime:** 0
- **mcauley · lifetime playtime > 50,000 h (≈ 5.7 years nonstop):** 0
- **mcauley · lifetime playtime > 10,000 h:** 5
  - e.g. Garry's Mod; Universe Sandbox; Call of Duty®: Black Ops; Mabinogi
- **mcauley · users with ≥ 3,000 owned items:** 16
  - e.g. 4576; 5027; 6132; 6410; 6700; 7762
- **mcauley · users with games but zero played:** 2,509
- **mcauley · users with total playtime > 8,760 h per year since 2009 (> 24h/day):** 0
  - item_type of owned rows: game 4,301,056, unknown 366,240, removed 280,816, advertising 40,184, tool 36,881, mod 27,072, dlc 17,186, software 13,170, video 10,809, demo 668
  - most-owned items typed 'tool': 232210 Patch testing for Chivalry (15,740); 362300 H1Z1: Just Survive Test Server (4,987); 232150 Killing Floor 2 - SDK (4,183); 238590 Loadout Campaign Beta (1,921); 367690 Spintires Editor (1,440); 234740 Tower Wars Editor (1,355); 397080 Magicka 2: Spell Balance Beta (1,243); 319060 Lambda Wars Dedicated Server (1,095)
  - most-owned items typed 'unknown': 301520 Robocraft (21,528); 243870 Tom Clancy's Ghost Recon Phantoms - NA (14,449); 323370 TERA (10,359); 367540 Starbound - Unstable (9,558); 271290 HAWKEN (8,240); 239220 The Mighty Quest For Epic Loot (6,916); 236830 Red Orchestra 2: Heroes of Stalingrad - Single Player (6,696); 299360 Block N Load (5,103)