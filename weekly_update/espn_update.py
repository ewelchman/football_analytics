#!/usr/bin/env python

import time
import read_espn
import pandas as pd
import os
import sys


###### RESULTS FILE LOCATIONS #######
filesdir = "/home/welced12/googledrive/nfl_data/devl/"
games_file = filesdir+"espn_gamedata.json"
drives_file = filesdir+"espn_drives.json"
pbp_file = filesdir+"espn_rawplays.json"


def update_json(filename, df):

	# Check for existing json file consisting of a single DataFrame
	if os.path.isfile(filename):
		print("Reading",filename)
		read_df = pd.read_json(filename, convert_axes=False)
		# Write new results on top of those from file
		for gid in df.index:
			read_df.loc[gid] = df.loc[gid,:]
	else:
		read_df = df

	# Write DataFrame to json file
	print("Writing to",filename)
	read_df.to_json(filename)


def write_results(games_df, drives_df, pbp_df):
	update_json(games_file, games_df)
	update_json(drives_file, drives_df)
	update_json(pbp_file, pbp_df)


def big_update(season, week):

	# Get games that occur(red)
	weeks_games = read_espn.weekly_games(season, week)
	# Scrape individual pages for those games
	(games_df, drives_df, pbp_df) = read_espn.scrape_gameset(weeks_games)
	# Update existing results
	write_results( games_df, drives_df, pbp_df )


### MAIN ###

if len(sys.argv) != 3:
	print("Proper usage:\n espn_update.py [season] [week]")
	sys.exit()

try:
	season = int(sys.argv[1])
	week = int(sys.argv[2])
except ValueError:
	print("Proper usage:\n espn_update.py [season] [week]\nseason and week must be integers!")
	sys.exit()

# Actually do the update
big_update(season, week)
