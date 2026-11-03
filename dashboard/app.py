"""Steam recommender - D2 data dashboard. Reads every number from Supabase (public.eda_* tables, read-only).

Local:  streamlit run dashboard/app.py
Modal:  modal deploy dashboard/modal_app.py
"""
import json
import os

import altair as alt
import pandas as pd
import streamlit as st
from supabase import create_client

URL = os.environ.get("SUPABASE_URL", "https://pwcywpymbhnrixolvuvv.supabase.co")
KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_e6BIJUId77nLtSXDmgPGHA_9Ms8ocKj")   # public, read-only via RLS
COLORS = {"McAuley 2017": "#0072B2", "Steam 2026": "#D55E00", "Kaggle (to 2023)": "#009E73"}   # Okabe-Ito, fixed per source


def color(d):
    """Fixed color per source; the legend lists only the sources present in this chart and sits above it."""
    present = [k for k in COLORS if k in set(d.source)]
    return alt.Color("source:N", scale=alt.Scale(domain=present, range=[COLORS[k] for k in present]),
                     legend=alt.Legend(orient="top", title=None, labelLimit=260))

st.set_page_config(page_title="Steam Recommender Data", layout="wide")


@st.cache_data(ttl=3600)
def load(table):
    rows = []
    sb = create_client(URL, KEY)
    for k in range(0, 100_000, 1000):
        r = sb.table(table).select("*").range(k, k + 999).execute().data
        rows += r
        if len(r) < 1000:
            break
    return pd.DataFrame(rows)


facts = {r.key: json.loads(r.value) for r in load("eda_facts").itertuples()}
src = load("eda_sources")

st.title("Steam Recommender: Data Preparation and EDA")
st.caption("D2 dashboard. Every number is read live from Supabase (tables public.eda_*), built by clean/build_clean.py "
           "and eda/d2_figures.py.")

c = st.columns(4)
c[0].metric("Played (player, game) rows", f"{int(src.played_rows.sum()) / 1e6:.1f} M")
c[1].metric("Players", f"{int(src.players.sum()) / 1e6:.2f} M")
c[2].metric("Library size, 2017 vs 2026", f"{facts['median_library_McAuley 2017']} vs {facts['median_library_Steam 2026']}",
            help="Median played games per player")
c[3].metric("Positive reviews, top vs bottom playtime decile", f"{facts['label_pos_bottom_top_Steam 2026'][1]:.0f}% vs "
            f"{facts['label_pos_bottom_top_Steam 2026'][0]:.0f}%", help="Steam 2026 reviews")

tabs = st.tabs(["Sources", "Playtime", "Libraries", "Popularity", "Label check", "Release years", "Data quality", "Test split"])

with tabs[0]:
    st.subheader("Data sources")
    st.markdown("**Player data** (who played what, and for how long)")
    show = src[["source", "players", "played_rows", "games", "median_hours", "median_library", "years", "role"]].copy()
    show["median_library"] = show.median_library.map(lambda v: "n/a (reviewed games only)" if pd.isna(v) else f"{v:.0f}")
    show = show.rename(columns={"played_rows": "played rows", "median_hours": "median hours per game",
                                "median_library": "median played games"})
    st.dataframe(show, hide_index=True, use_container_width=True)
    st.markdown("- **McAuley 2017** (Hugging Face mirror of the UCSD dataset) is the closest match to a live user: full "
                "libraries, including unplayed games.\n"
                "- **Steam 2026** is our own collection through Steam's official API: modern libraries, hashed IDs, no review text.\n"
                "- **Kaggle** (*Game Recommendations on Steam*, to Oct 2023) is large but holds only reviewed games, with "
                "playtime measured at review time.")
    st.markdown("**Game catalog** (what each game is)")
    cat = pd.DataFrame([{
        "source": "FronkonGames Steam Games Dataset",
        "where from": "Hugging Face (also on Kaggle), downloaded Oct 28, 2026",
        "games": f"{facts['fronkon_games']:,}",
        "new to our catalog": f"{facts['fronkon_added_to_catalog']:,} (incl. 2024-2026 releases)",
        "provides": "tags, genres, descriptions, header images, prices, review counts, SteamSpy playtimes"}])
    st.dataframe(cat, hide_index=True, use_container_width=True)
    st.markdown(f"The merged catalog joins FronkonGames, Kaggle's 2023 game list, McAuley's game metadata and Steam's app "
                f"list: **{facts['catalog_apps']:,} apps**, of which **{facts['catalog_recommendable']:,}** can be "
                "recommended (a game, on sale, released, not sexually explicit). FronkonGames is why the recommender "
                "can suggest games released after 2023. Its cleaning rules are F1-F6 in the Data quality tab.")

with tabs[1]:
    d = load("eda_playtime_hist")
    d["minutes"] = 10 ** d.log10_minutes
    st.altair_chart(alt.Chart(d).mark_line(strokeWidth=2).encode(
        x=alt.X("minutes:Q", scale=alt.Scale(type="log"), title="Playtime per (player, game), minutes (log scale)"),
        y=alt.Y("share:Q", axis=alt.Axis(format="%"), title="Share of played rows"),
        color=color(d),
        tooltip=["source", alt.Tooltip("minutes:Q", format=",.0f"), alt.Tooltip("share:Q", format=".2%")]).properties(height=380),
        use_container_width=True)
    st.markdown("**What we see:** playtime runs from minutes to thousands of hours. Kaggle's median is much higher "
                f"({facts['median_hours_Kaggle (to 2023)']} h vs {facts['median_hours_McAuley 2017']} h) because people "
                "review games they played a lot, and its export stops at 1,000 h.  \n"
                "**What it means:** raw hours can't be compared across games, so the enjoyment label ranks each player "
                "among the same game's players.")

with tabs[2]:
    d = load("eda_library_hist")
    st.altair_chart(alt.Chart(d).mark_bar(opacity=0.75).encode(
        x=alt.X("games_from:Q", scale=alt.Scale(type="log"), title="Played games per player (log scale)"),
        x2="games_to:Q", y=alt.Y("share:Q", title="% of players", stack=None),
        color=color(d),
        tooltip=["source", alt.Tooltip("games_from:Q", format=",.0f"), alt.Tooltip("share:Q", format=".1f")]).properties(height=380),
        use_container_width=True)
    st.markdown(f"**What we see:** the median 2026 player has played {facts['median_library_Steam 2026']} games, against "
                f"{facts['median_library_McAuley 2017']} in 2017.  \n**What it means:** a label tuned on 2017 libraries lost "
                "to plain playtime on 2026 players, so 2026 players are a separate test slice.")

with tabs[3]:
    d = load("eda_popularity_curve")
    st.altair_chart(alt.Chart(d).mark_line(strokeWidth=2).encode(
        x=alt.X("share_of_games:Q", scale=alt.Scale(type="log", domain=[0.0001, 1]), axis=alt.Axis(format="%"),
                title="Share of games, most played first (log scale)"),
        y=alt.Y("share_of_plays:Q", axis=alt.Axis(format="%"), title="Cumulative share of played rows"),
        color=color(d),
        tooltip=["source", alt.Tooltip("share_of_games:Q", format=".2%"), alt.Tooltip("share_of_plays:Q", format=".1%")]
    ).properties(height=380), use_container_width=True)
    st.markdown(f"**What we see:** the top 1% of games hold {facts['top1pct_share_Kaggle (to 2023)']}% of Kaggle plays and "
                f"{facts['top1pct_share_McAuley 2017']}% of McAuley plays.  \n**What it means:** recommending hits scores "
                "well by default; MostPopular is a required baseline and long-tail recall is tracked.")

with tabs[4]:
    d = load("eda_label_curve")
    st.altair_chart(alt.Chart(d).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=60)).encode(
        x=alt.X("decile:O", title="Player's playtime decile among the same game's players (1 = bottom 10%)"),
        y=alt.Y("pct_positive:Q", scale=alt.Scale(zero=False), title="% of reviews positive"),
        color=color(d),
        tooltip=["source", "decile", alt.Tooltip("pct_positive:Q", format=".1f"), alt.Tooltip("n:Q", format=",")]
    ).properties(height=380), use_container_width=True)
    st.markdown("**What we see:** the more a player plays a game relative to its other players, the more likely their "
                f"review is positive. Refunded games: {facts['refund_positive_pct']}% positive vs "
                f"{facts['all_reviews_positive_pct']}% overall.  \n**What it means:** within-game playtime percentile is a "
                "valid enjoyment label for players who never review. Reviews check the label; they are never trained on.")

with tabs[5]:
    d = load("eda_release_year")
    st.altair_chart(alt.Chart(d).mark_line(strokeWidth=2).encode(
        x=alt.X("release_year:O", title="Release year of the game"),
        y=alt.Y("pct_of_plays:Q", title="% of played rows"),
        color=color(d),
        tooltip=["source", "release_year", alt.Tooltip("pct_of_plays:Q", format=".1f")]).properties(height=380),
        use_container_width=True)
    st.markdown("**What we see:** McAuley stops in 2017 and Kaggle in 2023; only our 2026 libraries cover recent games.  \n"
                "**What it means:** a sampling concern: models trained mostly on older data may under-serve new releases.")

with tabs[6]:
    st.subheader("Catalog gaps (recommendable games)")
    q = load("eda_catalog_quality")
    st.dataframe(q.rename(columns={"pct_missing": "% affected"}), hide_index=True, use_container_width=True)
    st.subheader("Cleaning rules applied")
    r = load("eda_cleaning_rules").sort_values("seq")
    pick = st.multiselect("Source", sorted(r.source.unique()))
    if pick:
        r = r[r.source.isin(pick)]
    st.dataframe(r.drop(columns=["seq"]).rename(columns={"rule_id": "id", "rows_affected": "rows affected"}),
                 hide_index=True, use_container_width=True)

with tabs[7]:
    st.subheader("Reserved evaluation data")
    s = load("eda_split_counts")
    if len(s):
        st.dataframe(s.rename(columns={"eligible_5plus": "eligible (5+ visible games)", "small_1to4": "small libraries (1-4)"}),
                     hide_index=True, use_container_width=True)
    st.markdown("Players are split by a fixed hash rule: 10% test, 10% validation, 80% train, per source. Each test "
                "player's played games are split 80% visible / 20% hidden by the same kind of rule. Test players are "
                "removed from all training and scored once, at the end. Full rules: `eval/PROTOCOL.md`.")
