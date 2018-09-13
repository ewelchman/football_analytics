#!/usr/bin/env python

import pandas as pd

rawplays_file = "/home/welced12/googledrive/nfl_data/devl/espn_rawplays.json"
parsedplays_file = "/home/welced12/googledrive/nfl_data/devl/espn_parsedplays.json"


def parse_downdist(df):
    # Given a DataFrame, return dictionaries for down, distance, and fieldpos
    down = []
    dist = []
    home_fieldpos = []
    
    hometeam = df.home.values
    awayteam = df.away.values
    
    def get_fieldpos(teamside, ydline, j):
        if teamside == hometeam[j]:
            # Ball is on home team's half. Location should be negative
            return -1*(50-ydline)
        elif teamside == awayteam[j]:
            return 50-ydline
        else:
            return "x"
        
    
    for j, c in enumerate(df.downdist.values):
        
        x = str(c).strip("[]'")
        # Check for an empty list. This probably means end of qtr/half
        if (not x) or x==None:
            down.append(0)
            dist.append(0)
            home_fieldpos.append(0)
            
        else:
            x = [x]
            pieces = x[0].split()
            
            # Parse down
            if not (pieces[0][0].isalpha() or pieces[0][0]=="&"):  # Check if first char is alpha
                # Then first char is numeric. This is down number
                down.append(int(pieces[0][0]))
            else:
                down.append(0)
                
            # Parse distance
            for i, word in enumerate(pieces):
                if (word == "and") or (word == "&"):
                    dist.append(pieces[i+1])  # Keep as string to preserve goal-to-go
            
            # Get fieldposition from home team's perspective
            for i, word in enumerate(pieces):
                if word == "at":
                    if pieces[i+1]=='50':
                        home_fieldpos.append(0)
                    else:
                        teamside = pieces[i+1]
                        ydline = int(pieces[i+2])
                        
                        fieldpos = get_fieldpos(teamside,ydline,j)
                        
                        if fieldpos=="x":
                            # Cases to account for team name not matching description
                            if teamside == "LAR":
                                teamside = "STL"
                            elif teamside == "LAC":
                                teamside = "SD"
                            fieldpos = get_fieldpos(teamside,ydline,j)
                            
                        if fieldpos=="x":
                            home_fieldpos.append(0)
                            print(pieces)
                            print("Failed to find side of field correctly")
                            
                        else:
                            home_fieldpos.append(fieldpos)
                            
    return (down, dist, home_fieldpos)


def parse_time_rem(df):
    detail = df.detail.values
    
    qtr = []
    time_rem = []
    
    for d in detail:
        try:
            if (not d) or (d == None):
                # detail is an empty list
                qtr.append(0)
                time_rem.append("0:00")
        
            else:
                pieces = d.split()
                if pieces[0][0] == "E":
                    # Found End of Quarter/Overtime line
                    qtr.append(0)
                    time_rem.append("0:00")

                elif pieces[0][0] == "(":
                    # Found beginning of standard "(1:23 - 4th)" template
                    qtr.append(pieces[2][0])
                    time_rem.append(pieces[0].lstrip("("))
            
                else:
                    # Not sure what this is, so just be safe and go to 0:00 rem in 4th
                    print(d)
                    qtr.append(0)
                    time_rem.append("0:00")
            
        except:
            print("Default parse failed for:")
            print(d)
            qtr.append(0)
            time_rem.append("0:00")       
            
    return (qtr, time_rem)


def get_secs_rem(df):
    qtr = df.qtr.values
    time_rem = df.time_rem.values
    
    secs_rem = []
    
    for i, tr in enumerate(time_rem):
        if qtr[i] in ['1','2','3','4']:
            q = int(qtr[i])
        elif qtr[i] == 'O':
            q = 4
        else:
            q = 0
        mins = int(tr.split(":")[0])
        secs = int(tr.split(":")[1])
        secs_rem.append( 900*(4-q) + 60*mins + secs )
        
    return secs_rem


# Parse play type/details

def found_pass(detail):
    d = detail.lower()
    pass_terms = [" pass", " sacked", " scramble",
                  "interception", "intercepted"]
    for term in pass_terms:
        if term in d:
            return True
    return False

def found_scramble(detail):
    d = detail.lower()
    if " scramble" in d:
        return True
    return False
    
def found_run(detail):
    d = detail.lower()
    run_terms = [" run ", " rush", " left tackle ", " up the middle ",
                 " left end ", " right end ", " left guard ", " right guard "]
    if not " scramble" in d:
        for term in run_terms:
            if term in d:
                return True
    return False

        
def found_punt(detail):
    d = detail.lower()
    if " punts " in d:
        return True
    elif " punt return" in d:
        return True
    return False
    
def found_fieldgoal(detail):
    d = detail.lower()
    if " field goal" in d:
        return True
    return False

def yds_run( detail ):
    words = detail.lower().split()
    # look for yardage in format "for X yards"
    for j, w in enumerate(words):
        if w == "for" and len(words) > j+2:
            if words[j+2].rstrip(".,") in ("yd","yds","yrd","yrds","yard","yards"):
                return int(words[j+1])
            # or "for no gain"
            elif "no" in words[j+1] and "gain" in words[j+2]:
                return 0
        
        # or "X yard run/rush"
        elif w in ("yd","yds","yrd","yrds","yard","yards") and len(words) >= j+2:
            if words[j+1].rstrip(".,") in ("run","rush"):
                return int(words[j-1])
        
    return "x"
    
def yds_passed( detail ):
    words = detail.lower().split()
    # look for yardage in format "for X yards"
    for j, w in enumerate(words):
        if w == "for" and len(words) > j+2:
            if words[j+2].rstrip(".,") in ("yd","yds","yrd","yrds","yard","yards"):
                return int(words[j+1])
            # or "for no gain"
            elif "no" in words[j+1] and "gain" in words[j+2]:
                return 0
            
        # or "X yard pass"
        elif w in ("yd","yds","yrd","yrds","yard","yards") and len(words) >= j+2:
            if words[j+1].rstrip(".,") in ("pass"):
                return int(words[j-1])

    # Or maybe pass went incomplete
    if "incomplete" in detail.lower():
        return 0
    
    # Or maybe pass was intercepted. In this case, just say yds_gained is zero
    elif ("intercepted" in detail.lower()) or ("interception" in detail.lower()):
        return 0
    
    return "x"

def parse_details(df):
    df = df[['down','detail']]
    
    # Make a bunch of dictionaries for storing play-specific data
    is_parseable = {}
    is_run = {}
    is_scramble = {}
    is_pass = {}
    is_punt = {}
    is_fieldgoal = {}
    runpass_play = {}
    yds_gained = {}
    
    # Loop through details going through logic tree
    for (pid, d) in zip(df.index, df.detail.values): 
        
        # Look exclusively for play details on downs 1-4
        if df.loc[pid,'down'] in [1,2,3,4]:
            
            # Parse a scramble
            if found_scramble(d):
                is_scramble[pid] = True
                yds_gained[pid] = yds_run(d)
                
            if found_run(d):
                is_run[pid] = True
                yds_gained[pid] = yds_run(d)
                
            if found_pass(d):
                is_pass[pid] = True
                yds_gained[pid] = yds_passed(d)
                
            elif found_punt(d):
                is_punt[pid] = True
                is_parseable[pid] = True
                
            elif found_fieldgoal(d):
                is_fieldgoal[pid] = True
                is_parseable[pid] = True
                
            # Check whether play was totally "parseable"
            if (
                ((pid in is_run) | (pid in is_pass) | (pid in is_scramble)) 
                &
                (pid in yds_gained)
            ):
                runpass_play[pid] = True
                is_parseable[pid] = True

    return [is_parseable, is_run, is_scramble, is_pass,
            is_punt, is_fieldgoal, runpass_play, yds_gained]


### MAIN ###
# Read rawplays DataFrame from file
print("Reading raw plays file")
rawplays_df = pd.read_json(rawplays_file)
parsed_df = rawplays_df.loc[:,:]

# Begin parsing details for each play
print("Parsing down and distance")
(down, dist, fieldpos) = parse_downdist(rawplays_df)
parsed_df['down'] = down
parsed_df['dist'] = dist
parsed_df['home_fieldpos'] = fieldpos

print("Parsing quarter and time remaining")
(qtr, time_rem) = parse_time_rem(rawplays_df)
parsed_df['qtr'] = qtr
parsed_df['time_rem'] = time_rem
parsed_df['secs_rem'] = get_secs_rem(parsed_df)

print("Parsing play details")
detail_tuple = parse_details(parsed_df)
parsed_df['is_parseable'] = pd.Series(detail_tuple[0])
parsed_df['is_run'] = pd.Series(detail_tuple[1])
parsed_df['is_scramble'] = pd.Series(detail_tuple[2])
parsed_df['is_pass'] = pd.Series(detail_tuple[3])
parsed_df['is_punt'] = pd.Series(detail_tuple[4])
parsed_df['is_fieldgoal'] = pd.Series(detail_tuple[5])
parsed_df['runpass_play'] = pd.Series(detail_tuple[6])
parsed_df['yds_gained'] = pd.Series(detail_tuple[7])
# Fill empty values with False or 0, depending on column
tf_cols = ['is_parseable','is_run','is_pass','is_scramble',
           'is_punt','is_fieldgoal','runpass_play']
parsed_df[tf_cols] = parsed_df[tf_cols].fillna("False")
parsed_df['yds_gained'] = parsed_df['yds_gained'].fillna(0)

# Write parsed DataFrame to new file
print("Writing parsed DataFrame to",parsedplays_file)
parsed_df.to_json(parsedplays_file)
