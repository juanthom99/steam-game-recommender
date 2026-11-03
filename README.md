# Steam Game Recommender

A player signs in through Steam and gets two rows of game recommendations: **For you** (close to what they already
enjoy) and **Try something new** (games players with the same taste enjoyed, outside the player's usual tags).
"Enjoyed" comes from playtime: how long a player played a game compared with that game's other players.

## D2: Data preparation and EDA

- Data note: [`d2/final/D2_Data_Note.pdf`](d2/final/D2_Data_Note.pdf)
- Dashboard (Streamlit on Modal, reading Supabase): https://juanthom99--steamrec-d2-dashboard-run.us-east.modal.run
- Data dictionary: [`clean/data_dictionary.md`](clean/data_dictionary.md); cleaning rules: [`clean/cleaning_report.md`](clean/cleaning_report.md)
- Evaluation protocol (frozen before testing): [`eval/PROTOCOL.md`](eval/PROTOCOL.md)

## Data

Not stored in this repository. Download into `C:/Users/<you>/data_raw/` (paths are set at the top of each script):

| Source | Use |
|---|---|
| McAuley Australian Steam data ([UCSD](https://cseweb.ucsd.edu/~jmcauley/datasets.html#steam_data)) | Full 2017 libraries: main training and test data |
| [Game Recommendations on Steam](https://www.kaggle.com/datasets/antonkozyriev/game-recommendations-on-steam) (Kaggle) | 41M reviews with hours: extra training rows, label validation |
| [Steam Games Dataset](https://www.kaggle.com/datasets/fronkongames/steam-games-dataset) (FronkonGames) | Game catalog, including 2024–2026 releases |
| Steam Web API (`collect/steam_reviews.py`) | Our 2026 libraries and reviews; Steam IDs stored only as salted hashes |

## Reproducing D2

Python 3.12; `pip install -r requirements.txt`. Copy `.env.example` to `.env` and fill in your own keys (never commit it).

```
python clean/build_clean.py        # clean every table, 21 validation checks
python clean/audit_clean.py        # audit report
python clean/data_dictionary.py    # data dictionary (.md and .csv)
python clean/reserve_test.py       # reserve test/validation players (runs once)
python eda/d2_figures.py           # figures and summary tables
python eda/note_figures.py         # compact figures for the data note
python dashboard/load_supabase.py  # load summary tables into Supabase (public.eda_*)
modal deploy dashboard/modal_app.py
python d2/final/build_note.py      # render the data note
```

Running now: `collect/steamspy_refill.py` refills missing tags and regular prices from SteamSpy (about 24 h);
apply it with `clean/merge_steamspy.py`.
