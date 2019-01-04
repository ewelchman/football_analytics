#!/usr/bin/env python

import pandas as pd

# Requires parsed play-by-play first!!!
rawdrives_file = "/home/welced12/googledrive/nfl_data/devl/espn_drives.json"
parseddrives_file = "/home/welced12/googledrive/nfl_data/devl/espn_parseddrives.json"
pbp_file = "/home/welced12/googledrive/nfl_data/devl/espn_parsedplays.json"


def find_endofhalves(result_list):
    is_eoh = []
    for outcome in [x.lower() for x in result_list]:
        eoh = 0
        if "end of half" in outcome:
            eoh = 1
        elif "end of game" in outcome:
            eoh = 1
        is_eoh.append(eoh)        
    return is_eoh


def find_tds(result_list):
    is_td = []
    for outcome in [x.lower() for x in result_list]:
        td = 0
        if "touchdown" in outcome:
            td = 1
            # Exceptions for probable defensive scores
            for to in ['intercept','fumble','punt']:
                if to in outcome:
                    td = 0
        is_td.append(td)
    return is_td


def find_fgs(result_list):
    is_fg = []
    for outcome in [x.lower() for x in result_list]:
        fg = 0
        if ('field goal' in outcome) or ('fg' in outcome):
            fg = 1
            if 'block' in outcome:
                fg = 0
        is_fg.append(fg)
    return is_fg


def find_punts(result_list):
    is_punt = []
    for outcome in [x.lower() for x in result_list]:
        punt = 0
        if 'punt' in outcome:
            punt = 1
        is_punt.append(punt)
    return is_punt


def find_turnovers(result_list):
    is_to = []
    for outcome in [x.lower() for x in result_list]:
        to = 0
        for word in ['intercept','fumble','downs','safety']:
            if word in outcome:
                to = 1
        is_to.append(to)
    return is_to


def get_time_in_secs(value_list):
    top_secs = [0 for x in value_list]
    for i, time in enumerate(value_list):
        (mins,secs) = time.split(":")
        total_seconds = int(secs) + 60*int(mins)
        top_secs[i] = total_seconds
    return top_secs

def get_home_poss(df):
	home_team = df.home.values
	offense = df.offense.values
	col = [ 1 if ht==off else 0 for (ht,off) in zip(home_team,offense) ]
	return col


### MAIN ###
# Read raw drives DataFrame from file
print("Reading raw drives file")
drives_df = pd.read_json(rawdrives_file)
parsed_df = drives_df.loc[:,:]

# Determine drive results
print("Parsing drive results")
parsed_df['TD'] = find_tds(drives_df['result'].values)
parsed_df['FG'] = find_fgs(drives_df['result'].values)
parsed_df['punt'] = find_punts(drives_df['result'].values)
parsed_df['turnover'] = find_turnovers(drives_df['result'].values)
parsed_df['eoh'] = find_endofhalves(drives_df['result'].values)

# Read the length of each drive in seconds
print("Translating drive lengths")
parsed_df['time_in_secs'] = get_time_in_secs(drives_df.time.values)

# To find seconds remaining at the beginning of a drive, get it from play-by-play
print("Extracting time remaining from play-by-play data")
pbp_df = pd.read_json(pbp_file)
firstplays = pbp_df.loc[ pbp_df['play_num'] == 1 ]
firstplays['driveid'] = firstplays.gameid.astype(str)+"-"+firstplays.drive_num.astype(str)
right_df = firstplays[['driveid','secs_rem']]
parsed_df = pd.merge(
    parsed_df, right_df,
    how='left',
    left_index=True,
    right_on='driveid',
)
parsed_df.set_index('driveid', inplace=True)

# Get secs left in half at beginning of a drive
left_in_half = [t if t <= 1800 else t-1800 for t in parsed_df.secs_rem.values]
parsed_df['left_in_half'] = left_in_half

# Get column for whether home team has possession
print("Determining whether home team has possession")
parsed_df['home_poss'] = get_home_poss(parsed_df)

# Write this new parsed drives DataFrame to new file
print("Writing parsed drives")
parsed_df.to_json(parseddrives_file)
