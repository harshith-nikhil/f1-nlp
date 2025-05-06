import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import fastf1
from fastf1.core import *

import os
import json


''' 
Extracting the Session Data from a Race Weekend (Race and Quali)
'''
def get_session_data(year, track, event_type):
    session_data=fastf1.get_session(year, track, event_type)
    session_data.load(laps=True, telemetry=True, weather=True)
    return session_data

def format_Time(td):
    total_sec = td.total_seconds()
    minutes = int(total_sec // 60)
    seconds = int(total_sec % 60)
    milliseconds = int((td.microseconds) / 1000)
    return f"{minutes:02}:{seconds:02}.{milliseconds:03}"

total_sec=0
def format_raceTime(td):
    global total_sec
    time_diff = td.total_seconds()
    if (time_diff == 0):
        return 0
    total_sec+=time_diff
    minutes = int(total_sec // 60)
    seconds = int(total_sec % 60)
    milliseconds = int((td.microseconds) / 1000)
    return f"{minutes:02}:{seconds:02}.{milliseconds:03}"

def preprocess_race_results(race_session):
    race_results = race_session.results
    race_results['Time']=race_results['Time'].fillna(pd.Timedelta(seconds=0))
    race_results['RaceTime'] = race_results['Time'].apply(format_raceTime)
    race_results.drop(columns=['Q1', 'Q2', 'Q3', 'HeadshotUrl', 'FirstName', 'LastName', 'TeamId', 'BroadcastName', 'TeamId', 'Time'], inplace=True)
    race_results.reset_index(drop=True)
    return race_results

def generate_laps_summary(race_session):
    laps_summary_df=race_session.laps
    laps_summary_df = laps_summary_df[(~laps_summary_df['Deleted']) & (laps_summary_df['IsAccurate']) & (laps_summary_df['LapTime'].notnull())]
    summaries = []
    pitstop_map = laps_summary_df.groupby('Driver')['Compound'].nunique().apply(lambda x: max(x - 1, 0)).to_dict()

    for driver in laps_summary_df['Driver'].unique():
        driver_laps = laps_summary_df[laps_summary_df['Driver'] == driver]

        fastest_lap = driver_laps.loc[driver_laps['LapTime'].idxmin()]
        fastest_lap_time = format_Time(fastest_lap['LapTime'])

        total_laps = driver_laps['LapNumber'].nunique()
        pitstops = pitstop_map.get(driver, 0)

        compound_groups = driver_laps.groupby('Compound')

        for compound, group in compound_groups:
            compound_summary = {
                'Driver': driver,
                'Compound': compound,
                'LapsOnCompound': len(group),
                'FastestLapOnCompound': format_Time(group['LapTime'].min()),
                'FastestSector1': format_Time(group['Sector1Time'].min()),
                'FastestSector2': format_Time(group['Sector2Time'].min()),
                'FastestSector3': format_Time(group['Sector3Time'].min()),
                'FastestLapOverall': fastest_lap_time,
                'TotalLaps': total_laps,
                'PitStops': pitstops
            }
            summaries.append(compound_summary)

    return pd.DataFrame(summaries)

def get_raceContext_json(race_results, race_name, year):
    context = get_race_results_context(race_results)
    return {
        "instruction": f"Summarize the race results of {race_name} {year}",
        "context": context,
        "response": ""
    }

def get_race_results_context(race_results):
    race_results['GridPosition']= race_results['GridPosition'].fillna(0)
    race_results["Points"]= race_results["Points"].fillna(0.0)
    context = []
    for _, row in race_results.iterrows():
        context.append({
            "driver": row["FullName"],
            "abbreviation": row["Abbreviation"],
            "team": row["TeamName"],
            "race_position": row["ClassifiedPosition"],
            "starting_position": int(row["GridPosition"]),
            "points_secured": float(row["Points"])
        })
    return context

def save_all_races_to_jsonl(race_data_dict, folder_path="jsonl", filename="f1_race_results.jsonl"):
    os.makedirs(folder_path, exist_ok=True)
    output_path = os.path.join(folder_path, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        for (race_name, year), df in race_data_dict.items():
            entry = get_raceContext_json(df, race_name, year)
            f.write(json.dumps(entry) + "\n")

    print(f"Saved {len(race_data_dict)} races to {output_path}")