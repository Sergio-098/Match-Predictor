import pandas as pd
import numpy as np
from plotly.express.trendline_functions import rolling
from sklearn.ensemble import RandomForestClassifier as Rf
from sklearn.metrics import precision_score

class MissingDict(dict):
    __missing__ = lambda self, key: key

maps_values = {"Brighton and Hove Albion": "Brighton",
               "Manchester United": "Manchester Utd",
               "Newcastle United": "Newcastle Utd",
               "Tottenham Hotspur": "Tottenham",
               "West Ham United": "West Ham",
               "Wolverhampton Wanderers": "Wolves"
               }

mapping = MissingDict(**maps_values)

def rolling_averages3(group, c, nc):
    """Find rolling averages of different metrics"""
    group = group.sort_values('date')
    rolling_stats = group[c].rolling(3, closed='left').mean()
    group[nc] = rolling_stats
    group = group.dropna(subset=nc)
    return group

def make_predictions(data, lst):
    """run predictions into ml model"""
    rf = Rf(n_estimators=50, min_samples_split=10, random_state=1)
    train = data[data['season'] < 2024]
    test = data[data['season'] >= 2024]
    rf.fit(train[lst], train['target'])
    preds = rf.predict(test[lst])
    comb = pd.DataFrame(dict(actual=test['target'], predicted=preds),
                            index=test.index)
    prec = precision_score(test['target'], preds)

    return comb, prec

matches = pd.read_csv('Prem_Match_Stats.csv', index_col=0)
matches = matches.sort_values(by=['date', 'time'])
matches['team'] = matches['team'].replace(mapping)

matches = matches.reset_index()
matches['date'] = pd.to_datetime(matches['date'])

matches['target'] = (matches['result'] == 'W').astype(int)

matches['H_or_A'] = matches['venue'].astype('category').cat.codes
matches['opp_code'] = matches['opponent'].astype('category').cat.codes
matches['hour'] = matches['time'].str.replace(":.+", "", regex=True).astype(int)
matches['day_code'] = matches['day'].astype('category').cat.codes
matches = matches.fillna({'referee': 0})
matches['ref'] = matches['referee'].astype('category').cat.codes

predictors = ['H_or_A', 'opp_code', 'hour', 'day_code', 'ref']

matches['won'] = matches['result'].apply(lambda x: 1 if x == 'W' else 0)
matches = matches.sort_values(by=['team', 'season', 'date'])
grouped = matches[matches['result'].notna()].groupby(['team', 'season'])
matches['won_last'] = grouped['won'].shift(1)
matches['won_last_2'] = grouped['won'].shift(1).rolling(window=2).sum()
matches['won_last_3'] = grouped['won'].shift(1).rolling(window=3).sum()
matches['won_last_5'] = grouped['won'].shift(1).rolling(window=5).sum()
matches['won_last_10'] = grouped['won'].shift(1).rolling(window=10).sum()
matches['wins_this_season'] = grouped['won'].cumsum()
matches = matches.fillna({'won_last': 0, 'won_last_2': 0, 'won_last_3': 0,
                'won_last_5': 0, 'won_last_10': 0, 'wins_this_season': 0})

team_win_metrics = matches[['team', 'season', 'date', 'won_last', 'won_last_2',
                            'won_last_3', 'wins_this_season']]
team_win_metrics.rename(columns={
    'won_last': 'opponent_won_last',
    'won_last_2': 'opponent_won_last_2',
    'won_last_3': 'opponent_won_last_3',
    'wins_this_season': 'opponent_wins_this_season'
}, inplace=True)

matches = matches.merge(team_win_metrics[['team', 'season', 'opponent_won_last',
    'opponent_won_last_2', 'opponent_won_last_3', 'opponent_wins_this_season']],
                        left_on=['opponent', 'season'],
                        right_on=['team', 'season'],
                        suffixes=('', '_opponent'))

matches['points'] = matches['result'].map({'W': 3, 'D': 1, 'L': 0})
grouped = matches.groupby(['team', 'season'])
matches['points_this_season'] = grouped['points'].cumsum()
matches['points_this_season'].fillna(0, inplace=True)
team_points = matches[['date', 'team', 'season', 'points_this_season']]
team_points.rename(columns={'team': 'opponent', 'points_this_season':
                                'opponent_points_this_season'}, inplace=True)
matches = matches.merge(team_points[['date', 'opponent', 'season',
                                     'opponent_points_this_season']],
                        left_on=['date', 'opponent', 'season'],
                        right_on=['date', 'opponent', 'season'],
                        suffixes=('', '_opponent'))

predictors.extend(['points_this_season', 'opponent_points_this_season',
                   'opponent_won_last', 'opponent_won_last_2',
                   'opponent_won_last_3', 'opponent_wins_this_season',
                   'won_last', 'won_last_2', 'won_last_3', 'won_last_5',
                   'won_last_10', 'wins_this_season'])


cols = ['gf', 'ga', 'sh', 'sot', 'dist', 'fk', 'pk', 'pkatt', 'psxg+/-',
        'sca', 'recov']
new_cols3 = [f"{c}_rolling3" for c in cols]

rolling_averages3(matches, cols, new_cols3)

matches_rolling = matches.groupby('team').apply(lambda x:
                                                rolling_averages3(x, cols,
                                                                  new_cols3))
matches_rolling = matches_rolling.droplevel('team')
matches_rolling.index = range(matches_rolling.shape[0])
predictors.extend(new_cols3)

combined, precision = make_predictions(matches_rolling, predictors)
combined = combined.merge(matches_rolling[['date', 'team', 'opponent', 'result']],
                          left_index=True, right_index=True)
merged = combined.merge(combined, left_on=['date', 'team'],
                                right_on=['date', 'opponent'])

merged['BET_WIN'] = (merged['predicted_x'] == 1) & (merged['predicted_y'] == 0)

bet_table = merged[['date', 'team_x', 'team_y', 'BET_WIN']]
bet_table = bet_table.sort_values('date')

print(bet_table.tail(20))
print(precision)
