import warnings
warnings.filterwarnings("ignore")

import fastf1
import pandas as pd
import os
import time

# ============================
# Section 1: Setup
# ============================

# Ensure cache directory exists
os.makedirs('cache', exist_ok=True)
fastf1.Cache.enable_cache('cache')

# ============================
# Section 2: Extraction Functions
# ============================

def extract_session_data(year, circuit, session_type):
    """Load and return a session (Race, Quali, Sprint, etc.)."""
    session = fastf1.get_session(year, circuit, session_type)
    session.load()
    return session

def get_race_results(session):
    """Extract race or sprint results safely."""
    results = session.results

    return pd.DataFrame({
        'driver': results['Abbreviation'],
        'team': results['TeamName'],
        'grid_position': results['GridPosition'],
        'finishing_position': results['Position'],
        'points': results['Points'],
        'status': results['Status'],
        'fastest_lap_time': results.get('FastestLapTime', pd.NA),
        'fastest_lap_speed': results.get('FastestLapSpeed', pd.NA)
    })
    
def get_qualifying_results(session):
    """Extract qualifying or sprint shootout results safely."""
    results = session.results

    return pd.DataFrame({
        'driver': results['Abbreviation'],
        'team': results['TeamName'],
        'qualifying_position': results['Position'],
        'Q1_time': results.get('Q1', pd.NA),
        'Q2_time': results.get('Q2', pd.NA),
        'Q3_time': results.get('Q3', pd.NA)
    })
    
def get_lap_times(session):
    """Extract lap times."""
    return session.laps[['Driver', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time', 'Compound', 'TyreLife', 'PitOutTime', 'PitInTime']]

def get_pit_stops(session):
    """Detect pit stops from laps safely."""
    laps = session.laps

    if laps.empty:
        return pd.DataFrame()

    if 'PitInTime' not in laps.columns or 'PitOutTime' not in laps.columns:
        return pd.DataFrame()

    pitstops = laps.dropna(subset=['PitInTime', 'PitOutTime']).copy()

    if 'PitLaneTime' not in pitstops.columns:
        pitstops['PitLaneTime'] = (pitstops['PitOutTime'] - pitstops['PitInTime'])

    pitstops_df = pitstops[['Driver', 'LapNumber', 'PitInTime', 'PitOutTime', 'PitLaneTime']].copy()
    pitstops_df['PitStopDurationSeconds'] = pitstops_df['PitLaneTime'].dt.total_seconds()

    return pitstops_df

def get_tire_stints(session):
    """Safely extract tire stint information from laps data."""
    laps = session.laps

    if laps.empty:
        return pd.DataFrame()

    expected_columns = ['Driver', 'Stint', 'Compound', 'LapStartTime', 'LapEndTime', 'TyreLife']

    # Only keep columns that actually exist
    available_columns = [col for col in expected_columns if col in laps.columns]

    if not available_columns:
        return pd.DataFrame()

    tire_data = laps[available_columns].dropna()

    return tire_data

def get_telemetry_data(session, drivers):
    """Extract telemetry data per driver, picking the fastest lap."""
    telemetry_data = {}

    for drv in drivers:
        driver_laps = session.laps.pick_driver(drv)

        if driver_laps.empty:
            continue

        # Pick the lap with minimum LapTime
        best_lap = driver_laps.pick_fastest()

        if best_lap is None:
            continue

        try:
            car_data = best_lap.get_car_data().add_distance()
            telemetry_data[drv] = car_data[['Distance', 'Speed', 'Throttle', 'Brake', 'DRS']]
        except Exception as e:
            print(f"Warning: Failed telemetry for driver {drv}: {e}")
            continue

    return telemetry_data

# ============================
# Section 3: Saving Functions
# ============================

def save_dataframes(dfs, base_path):
    """Save multiple DataFrames to CSV."""
    for name, df in dfs.items():
        df.to_csv(os.path.join(base_path, f"{name}.csv"), index=False)

def save_telemetry(telemetry_data, telemetry_path):
    """Save telemetry per driver as Parquet."""
    os.makedirs(telemetry_path, exist_ok=True)
    for driver, df in telemetry_data.items():
        df.to_parquet(os.path.join(telemetry_path, f"{driver}.parquet"))

# ============================
# Section 4: Document Generation
# ============================

def generate_race_document(year, circuit, race_results, quali_results, pitstops, tire_stints,
                            sprint_results=None, sprint_laps=None, sprint_shootout_results=None):
    """Generate a full text summary of the race and sprint."""
    
    doc = f"{circuit.upper()} Grand Prix {year}\n\n"

    doc += "Race Results:\n"
    for idx, row in race_results.sort_values('finishing_position').head(10).iterrows():
        doc += f"{row['finishing_position']}. {row['driver']} ({row['team']}) - {row['points']} pts - Status: {row['status']}\n"

    doc += "\nFastest Laps (Race):\n"
    top_fast = race_results[['driver', 'fastest_lap_time']].sort_values('fastest_lap_time').dropna().head(5)
    for idx, row in top_fast.iterrows():
        doc += f"{row['driver']}: {row['fastest_lap_time']}\n"

    doc += "\nQualifying Top 5:\n"
    for idx, row in quali_results.sort_values('qualifying_position').head(5).iterrows():
        doc += f"{row['qualifying_position']}. {row['driver']} ({row['team']}) - Q3: {row['Q3_time']}\n"

    doc += "\nPit Stops:\n"
    if not pitstops.empty:
        for idx, row in pitstops.iterrows():
            doc += f"{row['Driver']} pitted on Lap {row['LapNumber']}, duration {row['PitStopDurationSeconds']:.2f} seconds\n"
    else:
        doc += "No pit stops recorded.\n"

    doc += "\nTire Stints:\n"
    if not tire_stints.empty:
        doc += tire_stints[['Driver', 'Compound', 'Stint', 'LapStart', 'LapEnd']].to_string(index=False)
    else:
        doc += "No tire stint data."

    # Sprint Details
    if sprint_results is not None:
        doc += "\n\nSprint Race Results:\n"
        for idx, row in sprint_results.sort_values('finishing_position').head(8).iterrows():
            doc += f"{row['finishing_position']}. {row['driver']} ({row['team']}) - {row['points']} pts\n"

    if sprint_laps is not None:
        doc += "\nFastest Laps (Sprint):\n"
        sprint_fastest = sprint_laps[['Driver', 'LapTime']].sort_values('LapTime').dropna().head(5)
        for idx, row in sprint_fastest.iterrows():
            doc += f"{row['Driver']}: {row['LapTime']}\n"

    if sprint_shootout_results is not None:
        doc += "\nSprint Shootout Top 5:\n"
        for idx, row in sprint_shootout_results.sort_values('qualifying_position').head(5).iterrows():
            doc += f"{row['qualifying_position']}. {row['driver']} ({row['team']}) - Best Time: {row['Q3_time']}\n"

    return doc

# ============================
# Section 5: Race Processing
# ============================

def process_single_race(year, circuit):
    """Full ETL for a single race event, with strong validation."""
    try:
        print(f"\n==============================")
        print(f"Processing {circuit.upper()} {year}")
        print(f"==============================")

        race_session = extract_session_data(year, circuit, 'R')
        if race_session.results is None or race_session.laps.empty:
            print(f"Race session data missing for {circuit} {year}, skipping...")
            return

        base_dir = f"data/{year}/{circuit.lower().replace(' ', '_')}/"
        os.makedirs(base_dir, exist_ok=True)

        # Race Data
        race_results = get_race_results(race_session)
        race_laps = get_lap_times(race_session)
        pitstops = get_pit_stops(race_session)
        tire_stints = get_tire_stints(race_session)
        telemetry_race = get_telemetry_data(race_session, race_results['driver'].tolist())
        save_dataframes({
            'race_results': race_results,
            'race_laps': race_laps,
            'pitstops': pitstops,
            'tire_stints': tire_stints
        }, base_dir)
        save_telemetry(telemetry_race, os.path.join(base_dir, 'telemetry_race'))

        # Qualifying Data
        quali_results = None
        try:
            quali_session = extract_session_data(year, circuit, 'Q')
            if quali_session.results is not None:
                quali_results = get_qualifying_results(quali_session)
                save_dataframes({'qualifying_results': quali_results}, base_dir)
                telemetry_quali = get_telemetry_data(quali_session, quali_results['driver'].tolist())
                save_telemetry(telemetry_quali, os.path.join(base_dir, 'telemetry_qualifying'))
        except Exception as e:
            print(f"Qualifying session issue: {e}")

        # Sprint Sessions
        sprint_results, sprint_laps, sprint_shootout_results = None, None, None
        try:
            sprint_shootout_session = extract_session_data(year, circuit, 'SS')
            if sprint_shootout_session.results is not None:
                sprint_shootout_results = get_qualifying_results(sprint_shootout_session)
                save_dataframes({'sprint_shootout_results': sprint_shootout_results}, base_dir)
                telemetry_ss = get_telemetry_data(sprint_shootout_session, sprint_shootout_results['driver'].tolist())
                save_telemetry(telemetry_ss, os.path.join(base_dir, 'telemetry_sprint_shootout'))
        except Exception as e:
            print(f"Sprint Shootout session issue: {e}")

        try:
            sprint_session = extract_session_data(year, circuit, 'S')
            if sprint_session.results is not None:
                sprint_results = get_race_results(sprint_session)
                sprint_laps = get_lap_times(sprint_session)
                save_dataframes({
                    'sprint_results': sprint_results,
                    'sprint_laps': sprint_laps
                }, base_dir)
                telemetry_sprint = get_telemetry_data(sprint_session, sprint_results['driver'].tolist())
                save_telemetry(telemetry_sprint, os.path.join(base_dir, 'telemetry_sprint'))
        except Exception as e:
            print(f"Sprint Race session issue: {e}")

        # Generate document
        if quali_results is not None:
            print("Generating race_summary.txt...")
            race_doc = generate_race_document(
                year, circuit, race_results, quali_results if quali_results is not None else pd.DataFrame(),
                pitstops if not pitstops.empty else pd.DataFrame(),
                tire_stints if not tire_stints.empty else pd.DataFrame(),
                sprint_results=sprint_results,
                sprint_laps=sprint_laps,
                sprint_shootout_results=sprint_shootout_results
            )
            
            with open(os.path.join(base_dir, 'race_summary.txt'), 'w', encoding='utf-8') as f:
                f.write(race_doc)

        print(f"Finished {circuit} {year}")

    except Exception as e:
        print(f"Critical error in {circuit} {year}: {e}")



def get_all_events(year):
    if year == 2022:
        return [
            'Bahrain Grand Prix', 'Saudi Arabian Grand Prix', 'Australian Grand Prix', 
            'Emilia Romagna Grand Prix', 'Miami Grand Prix', 'Spanish Grand Prix', 
            'Monaco Grand Prix', 'Azerbaijan Grand Prix', 'Canadian Grand Prix', 
            'British Grand Prix', 'Austrian Grand Prix', 'French Grand Prix', 
            'Hungarian Grand Prix', 'Belgian Grand Prix', 'Dutch Grand Prix', 
            'Italian Grand Prix', 'Singapore Grand Prix', 'Japanese Grand Prix', 
            'United States Grand Prix', 'Mexico City Grand Prix', 'São Paulo Grand Prix', 
            'Abu Dhabi Grand Prix'
        ]

    elif year == 2023:
        return [
            'Bahrain Grand Prix','Saudi Arabian Grand Prix','Australian Grand Prix',
            'Azerbaijan Grand Prix','Miami Grand Prix','Monaco Grand Prix','Spanish Grand Prix',
            'Canadian Grand Prix','Austrian Grand Prix','British Grand Prix','Hungarian Grand Prix',
            'Belgian Grand Prix','Dutch Grand Prix','Italian Grand Prix','Singapore Grand Prix',
            'Japanese Grand Prix','Qatar Grand Prix','United States Grand Prix','Mexico City Grand Prix',
            'São Paulo Grand Prix','Las Vegas Grand Prix','Abu Dhabi Grand Prix']

    elif year == 2024:
        return ['Bahrain Grand Prix','Saudi Arabian Grand Prix','Australian Grand Prix',
         'Japanese Grand Prix','Chinese Grand Prix','Miami Grand Prix',
         'Emilia Romagna Grand Prix','Monaco Grand Prix','Canadian Grand Prix',
         'Spanish Grand Prix','Austrian Grand Prix','British Grand Prix','Hungarian Grand Prix',
         'Belgian Grand Prix','Dutch Grand Prix','Italian Grand Prix','Azerbaijan Grand Prix','Singapore Grand Prix',
         'United States Grand Prix','Mexico City Grand Prix','São Paulo Grand Prix',
         'Las Vegas Grand Prix','Qatar Grand Prix','Abu Dhabi Grand Prix']

    else:
        raise ValueError(f"No events available for year {year}")

def main():
    """Main overnight-safe runner."""
    years = [2023, 2024]

    log_path = "log.txt"
    with open(log_path, "w", encoding="utf-8") as logfile:
        logfile.write("🏁 F1 ETL Run Log\n\n")

    for year in years:
        print(f"\n========================")
        print(f"Starting Year {year}")
        print(f"========================\n")

        circuits = get_all_events(year)

        for circuit in circuits:
            try:
                process_single_race(year, circuit)
                message = f"Successfully processed {circuit} {year}\n"
                print(message)
            except Exception as e:
                message = f"Critical failure processing {circuit} {year}: {e}\n"
                print(message)

            with open(log_path, "a", encoding="utf-8") as logfile:
                logfile.write(message)

            time.sleep(3)

if __name__ == "__main__":
    main()