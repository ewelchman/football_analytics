import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import time

def make_soup(url):
	res = requests.get(url)
	soup = BeautifulSoup(res.text, 'lxml')
	return soup

class pbp_drive():

	def parse_drive(self,drive):
	
		# Try to read drive header
		header = drive.find("div",{"class":"accordion-header"})
		self.is_half = False
		if header == None:  # Then we've got end of a half or something
			self.is_half = True
			text = drive.find("span",{"class":"post-play"}).contents
			df = pd.DataFrame([[[],text]], columns=['downdist','detail'])
			return df

		# Grab information from drive header
		possessor_logo = drive.find("span",{"class":"home-logo"}).contents[0]
		s = "nfl/500/"
		e = ".png"
		# Cut off pieces of url before and after home team
		self.offense = (str(possessor_logo).split(s))[1].split(e)[0].upper()
		# Get result of the drive
		try:
		    self.result = header.find("span",{"class":"headline"}).contents
		except:
			print("Couldn't parse drive result")
			self.result = ""
		# Get info about home/away score
		home_info = header.find("span",{"class":"home"}).contents
		self.home_team = home_info[0].contents[0]
		self.home_score_after = home_info[1].contents[0]
		away_info = header.find("span",{"class":"away"}).contents
		self.away_team = away_info[0].contents[0]
		self.away_score_after = away_info[1].contents[0]
		# Get drive summary
		self.drive_detail = header.find("span",{"class":"drive-details"}).contents
		self.num_plays = self.drive_detail[0].split()[0]
		self.num_yards = self.drive_detail[0].split()[2]
		self.time_of_poss = self.drive_detail[0].split()[4]

		# Make a play-by-play dataframe for the drive
		# Grab info about individual plays from this drive
		playlist = []
		plays = drive.find_all("li")
		for p in plays:
			try:
				downdist = p.h3.contents
				detail = p.span.contents[0].replace("\n","").replace("\t","")
				playlist.append([downdist,detail])
			except:
				pass

		# Return a DataFrame of plays for this drive
		df = pd.DataFrame(playlist, columns=['downdist','detail'])
		df['play_num'] = df.index + 1
		return df


def get_game_df(url):

	# if no .com in url, assume it's a gameid.
	if not ".com" in url:
		url = "http://www.espn.com/nfl/playbyplay?gameId="+str(url)
	
	# Make a soub object from html
	soup = make_soup(url)

	# Find article with play-by-play table
	article = soup.find("article",{"class":"sub-module play-by-play"})

	# Article is structured like accordion, with items corresponding to individual drives
	accordion = article.find("ul",{"class":"css-accordion"})
	drives = accordion.find_all("li",{"class":"accordion-item"})

	# Parse each of the drives into a DataFrame
	drivelist = []
	for i, drive in enumerate(drives):
		# Initialize drive object, then parse
		d = pbp_drive()
		d.df = d.parse_drive(drive)
		d.drive_num = i

		if i == 0:
			d.home_score_before = 0
			d.away_score_before = 0
		else:
			d.home_score_before = drivelist[-1].home_score_after
			d.away_score_before = drivelist[-1].away_score_after

		# If the drive isn't a special section marking end of half/game
		# Then add drive's DataFrame to the drive list
		if not d.is_half:
			d.df['home'] = d.home_team
			d.df['away'] = d.away_team
			d.df['possession'] = d.offense
			d.df['home_score_before'] = d.home_score_before
			d.df['away_score_before'] = d.away_score_before
			d.df['home_score_after'] = d.home_score_after
			d.df['away_score_after'] = d.away_score_after
			d.df['drive_num'] = d.drive_num

			drivelist.append(d)

	# Make a DataFrame for individual drives
	drive_dicts = [
		{
			'drive':dd.drive_num,
			'offense':dd.offense,
			'plays':dd.num_plays,
			'yds_gained':dd.num_yards,
			'time':dd.time_of_poss,
			'result':dd.result[0],
			'home':dd.home_team,
			'away':dd.away_team,
			'home_score_before':dd.home_score_before,
			'away_score_before':dd.away_score_before,
			'home_score_after':dd.home_score_after,
			'away_score_after':dd.away_score_after
		} for dd in drivelist
	]
	drives_df = pd.DataFrame(drive_dicts)

	pbp_df = pd.concat([d.df for d in drivelist])
	return pbp_df, drives_df


# Function to get gameIds for a particular year/week
def get_gameid(season,week):
	# Make soup object for appropriate page
	url = "http://www.espn.com/nfl/schedule/_/week/{0}/year/{1}/seasontype/2".format(week,season)
	soup = make_soup(url)
	sched_page = soup.find("section",{"id":"main-container"})

	# Make a list for gameids
	gameids = []
	# and dictionary for results
	results = {}
	for link in sched_page.find_all('a'):
		if 'gameId=' in link.get('href'):
			# Extract last bit of url listed
			s = "gameId="
			this_game = link.get('href').split(s)[1]
			gameids.append(this_game)
			# And add text displayed to a dictionary
			try:
				results[this_game] = link.contents[0]
			except:
				results[this_game] = link.contents
	return gameids, results


# Function to return a DataFrame containing basic info about a particular week's games
def weekly_games(season,week):
	gameids, results = get_gameid(season,week)
	# Make list of dictionary entries for each individual game
	data = [
		{
			'gameid':gid,
			'season':season,
			'week':week,
			'result':results[gid]
		} for gid in gameids
	]
	# Turn list of dicts into DataFrame
	week_df = pd.DataFrame(data)
	week_df['gameid'] = week_df['gameid'].astype(str)
	week_df.set_index('gameid', inplace=True)
	return week_df


def scrape_gameset(games_df):
	"""
	Takes a DataFrame whose index consists of gameids.
	Scrapees drive list and play-by-play for each of the games.
	Returns a tuple containing 3 DataFrames
	"""

	# List of DFs for each game
	pbp_list = []
	drivelevel_list = []
	game_home = {}
	game_away = {}

	for gid in games_df.index:
		try:
			# Scrape individual game page
			print("Scraping gameid",gid)
			pbp_df, drives_df = get_game_df(gid)
			pbp_df['gameid'] = gid
			drives_df['gameid'] = gid
			# Re-index drives dataframe with unique driveid
			for i in drives_df.index:
				drives_df.loc[i,'driveid'] = gid+"-"+str(i)
			drives_df.set_index(['driveid'], inplace=True)
			# Re-index pbp dataframe with unique playid
			playids = [gid+"-"+str(i) for i in range(len(pbp_df.index))]
			pbp_df['playid'] = playids
			pbp_df.set_index(['playid'], inplace=True)

			game_home[gid] = pbp_df['home'].values[0]
			game_away[gid] = pbp_df['away'].values[0]

			pbp_list.append(pbp_df)
			drivelevel_list.append(drives_df)

		except:
			print("Failed to scrape gameid",gid)

		time.sleep(0.25)

	# Merge DFs together
	allplays_df = pd.concat(pbp_list)
	alldrives_df = pd.concat(drivelevel_list)

	return (games_df, alldrives_df, allplays_df)
