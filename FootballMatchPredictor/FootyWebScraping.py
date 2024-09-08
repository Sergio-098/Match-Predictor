import random
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time


def rename_team(url):
    """Find team names from urls"""
    name = (url.split('/')[-1].replace("-Stats","").replace("-", " "))
    return name

def rename_duplicate_columns(df):
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols
    return df

stat_types = {
    'shooting': 'Shooting',
    'keeper': 'Goalkeeping',
    'passing': 'Passing',
    'gca': 'Goal and Shot Creation',
    'defense': 'Defensive Actions',
    'possession': 'Possession',
    'misc': 'Miscellaneous Stats'
}
stat_lists = {
    'shooting': ["Date", "Sh", "SoT", "Dist", "FK", "PK", "PKatt"],
    'keeper': ["Date", "PSxG+/-", "PSxG"],
    'passing': ["Date", "KP", "PrgP","1/3", "PPA", "CrsPA"],
    'gca': ["Date", "SCA"],
    'defense': ["Date", "TklW", "Tkl+Int"],
    'possession': ["Date", "Att 3rd", "Att Pen", "PrgR"],
    'misc': ["Date", "Recov"]
}

years = list(range(2024, 2021, -1))
all_matches = []

#find website of interest
standings_url = 'https://fbref.com/en/comps/9/Premier-League-Stats'

for year in years:
    data = requests.get(standings_url)
    soup = BeautifulSoup(data.text, 'html.parser')
    standings = soup.select('table.stats_table')[0]
    links = [l.get('href') for l in standings.find_all('a')]
    links = [l for l in links if '/squads/' in l]
    team_urls = [f"https://fbref.com{l}" for l in links]
    previous_season = soup.select("a.prev")[0].get('href')
    standings_url = f"https://fbref.com{previous_season}"

    for team in team_urls:
        team_name = rename_team(team)
        data = requests.get(team)
        matches = pd.read_html(data.text, match="Scores & Fixtures")[0]

        for stat_cat, stat_name in stat_types.items():
            soup = BeautifulSoup(data.text, 'html.parser')
            links = [l.get('href') for l in soup.find_all('a')]
            links = [l for l in links if l and f'all_comps/{stat_cat}/' in l]
            data = requests.get(f"https://fbref.com{links[0]}")
            stats = pd.read_html(data.text, match=f"{stat_name}")[0]
            stats.columns = stats.columns.droplevel()
            try:
                matches = matches.merge(stats[stat_lists[stat_cat]], on="Date",
                                        how="left")
            except ValueError:
                continue
            time.sleep(random.uniform(5, 8))

        matches = matches[matches["Comp"] == 'Premier League']
        matches["Season"] = year
        matches["Team"] = team_name
        all_matches.append(matches)
        time.sleep(random.uniform(5, 8))

match_df = pd.concat(all_matches)
match_df.columns = [c.lower() for c in match_df.columns]
match_df =  rename_duplicate_columns(match_df)
match_df.to_csv("Prem_Match_Stats.csv", index=False)
