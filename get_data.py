#omsairam omsairam omsairam 



import pandas as pd
from nba_api.stats.endpoints import leaguedashptdefend
import os
import time
import pandas as pd
from nba_api.stats.endpoints import leaguedashptdefend

def get_defense_stats(year, season_type='Regular Season', per_mode='PerGame', defense_category='Less Than 6Ft'):
    # --- 1. SET UP FOLDERS ---
    season_str = f'{year}-{str(year + 1)[-2:]}'
    folder_path = os.path.join("nba_data", season_str)
    os.makedirs(folder_path, exist_ok=True)
    
    file_name = f"{defense_category.lower().replace(' ', '_')}.csv"
    full_path = os.path.join(folder_path, file_name)

    # Skip if we already have the data
    if os.path.exists(full_path):
        print(f"⏩ Already have {season_str} - {defense_category}")
        return

    # --- 2. YOUR ORIGINAL CALL ---
    print(f"📡 Fetching {season_str}: {defense_category}...")
    
    # Adding a longer timeout here specifically to stop the "Read Timeout" errors
    defense_stats = leaguedashptdefend.LeagueDashPtDefend(
        defense_category=defense_category, 
        season=season_str,
        season_type_all_star=season_type,
        per_mode_simple=per_mode,
        timeout=120 # Bumped up to prevent the crash you saw
    )

    df = defense_stats.get_data_frames()[0]
    
    # --- 3. SAVE TO CSV ---
    df.to_csv(full_path, index=False)
    print(f"✅ Saved to {full_path}")

if __name__ == "__main__":
    # The Years you requested
    YEARS = range(2019, 2026) # 2019 to 2025 (which becomes 25-26)
    
    # The Categories available
    CATEGORIES = [
        'Overall', '3 Pointers', '2 Pointers', 
        'Less Than 6Ft', 'Less Than 10Ft', 'Greater Than 15Ft'
    ]

    # --- NECESSARY LOOPS ---
    for y in YEARS:
        for cat in CATEGORIES:
            try:
                get_defense_stats(year=y, defense_category=cat)
                
                # A small nap to prevent the NBA server from getting angry
                time.sleep(3) 
                
            except Exception as e:
                print(f"❌ Error on {y} {cat}: {e}")
                print("Waiting 10 seconds before trying next...")
                time.sleep(10)