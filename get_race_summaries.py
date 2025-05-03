import os
import pandas as pd

def load_csv_safe(path):
    """Safely load a CSV file if it exists."""
    if os.path.exists(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            print(f"Failed loading {path}: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def generate_race_document(year, circuit_folder):
    base_path = os.path.join("data", str(year), circuit_folder)

    race_results = load_csv_safe(os.path.join(base_path, 'race_results.csv'))
    quali_results = load_csv_safe(os.path.join(base_path, 'qualifying_results.csv'))
    pitstops = load_csv_safe(os.path.join(base_path, 'pitstops.csv'))
    tire_stints = load_csv_safe(os.path.join(base_path, 'tire_stints.csv'))
    sprint_results = load_csv_safe(os.path.join(base_path, 'sprint_results.csv'))
    sprint_laps = load_csv_safe(os.path.join(base_path, 'sprint_laps.csv'))
    sprint_shootout_results = load_csv_safe(os.path.join(base_path, 'sprint_shootout_results.csv'))

    doc = f"{circuit_folder.upper().replace('_', ' ')} {year}\n\n"

    if not race_results.empty:
        doc += "Race Results:\n"
        for idx, row in race_results.sort_values('finishing_position').iterrows():
            doc += f"{row['finishing_position']}. {row['driver']} ({row['team']}) - {row['points']} pts - Status: {row['status']}\n"

    if not race_results.empty and 'fastest_lap_time' in race_results.columns:
        fastest = race_results[['driver', 'fastest_lap_time']].dropna().sort_values('fastest_lap_time')
        if not fastest.empty:
            doc += "\nFastest Laps (Race):\n"
            for idx, row in fastest.iterrows():
                doc += f"{row['driver']}: {row['fastest_lap_time']}\n"

    if not quali_results.empty:
        doc += "\nQualifying Results:\n"
        for idx, row in quali_results.sort_values('qualifying_position').iterrows():
            q3_time = row['Q3_time'] if 'Q3_time' in row and pd.notna(row['Q3_time']) else 'N/A'
            doc += f"{row['qualifying_position']}. {row['driver']} ({row['team']}) - Q3: {q3_time}\n"

    if not pitstops.empty:
        doc += "\nPit Stops:\n"
        for idx, row in pitstops.iterrows():
            duration = row.get('PitStopDurationSeconds', 'N/A')
            lap_number = row.get('LapNumber', 'N/A')
            doc += f"{row['Driver']} pitted on Lap {lap_number} - Duration: {duration} sec\n"

    if not tire_stints.empty:
        doc += "\nTire Stints:\n"
        try:
            doc += tire_stints[['Driver', 'Compound', 'Stint']].to_string(index=False)
        except Exception as e:
            print(f"Tire stint format issue for {circuit_folder}: {e}")

    if not sprint_results.empty:
        doc += "\n\nSprint Race Results:\n"
        for idx, row in sprint_results.sort_values('finishing_position').iterrows():
            doc += f"{row['finishing_position']}. {row['driver']} ({row['team']}) - {row['points']} pts\n"

    if not sprint_laps.empty:
        doc += "\nFastest Laps (Sprint):\n"
        fastest_sprint = sprint_laps[['Driver', 'LapTime']].dropna().sort_values('LapTime')
        if not fastest_sprint.empty:
            for idx, row in fastest_sprint.iterrows():
                doc += f"{row['Driver']}: {row['LapTime']}\n"

    if not sprint_shootout_results.empty:
        doc += "\nSprint Shootout Results:\n"
        for idx, row in sprint_shootout_results.sort_values('qualifying_position').iterrows():
            best_time = row.get('Q3_time', 'N/A')
            doc += f"{row['qualifying_position']}. {row['driver']} ({row['team']}) - Best Time: {best_time}\n"

    return doc

def generate_all_summaries():
    """Generate all race summaries into a single new folder."""
    data_path = "data"
    output_folder = "race_summaries"
    os.makedirs(output_folder, exist_ok=True)

    for year in os.listdir(data_path):
        year_path = os.path.join(data_path, year)
        if not os.path.isdir(year_path):
            continue

        for circuit_folder in os.listdir(year_path):
            circuit_path = os.path.join(year_path, circuit_folder)

            if not os.path.isdir(circuit_path):
                continue

            try:
                race_doc = generate_race_document(year, circuit_folder)

                output_filename = f"{circuit_folder}_{year}_summary.txt"
                output_path = os.path.join(output_folder, output_filename)

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(race_doc)

                print(f"Created summary: {output_filename}")

            except Exception as e:
                print(f"Failed to create summary for {year}/{circuit_folder}: {e}")

if __name__ == "__main__":
    generate_all_summaries()