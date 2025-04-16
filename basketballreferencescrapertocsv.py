import requests
from bs4 import BeautifulSoup
import csv
import re
import time

def extract_team_stats(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    title = soup.title.string
    match = re.match(r"(\d{4}-\d{2}) (.*?) Roster and Stats", title)
    if not match:
        raise ValueError("Page format is unexpected")
    season_str, team_name = match.groups()
    season = int(season_str[:4]) + 1

    record_text = soup.get_text()

    # Extract win/loss record
    record_match = re.search(r"Record:\s*(\d+)-(\d+)", record_text)
    win_pct = None
    if record_match:
        wins = int(record_match.group(1))
        losses = int(record_match.group(2))
        win_pct = round(wins / (wins + losses), 3)

    # Extract seed
    seed_match = re.search(r"Finished\s+(\d+)(?:st|nd|rd|th)\s+in\s+NBA\s+(Eastern|Western)\s+Conference", record_text)
    seed = int(seed_match.group(1)) if seed_match else None

    # Extract SRS and ratings
    srs_match = re.search(r"SRS: ([\-\+\d\.]+) \(", record_text)
    srs = float(srs_match.group(1)) if srs_match else None

    off_rtg = def_rtg = net_rtg = None
    ratings_match = re.search(r"Off Rtg:\s*([\d\.]+)\s*\(\d+.. of 30\)\s*Def Rtg:\s*([\d\.]+)\s*\(\d+.. of 30\)\s*Net Rtg:\s*([+-]?[\d\.]+)", record_text)
    if ratings_match:
        off_rtg = float(ratings_match.group(1))
        def_rtg = float(ratings_match.group(2))
        net_rtg = float(ratings_match.group(3))

    return {
        'team': team_name.strip(),
        'season': season,
        'seed': seed,
        'win_pct': win_pct,
        'off_rtg': off_rtg,
        'def_rtg': def_rtg,
        'net_rtg': net_rtg,
        'srs': srs
    }

def write_to_csv(data_list, filename):
    fieldnames = ['team', 'season', 'seed', 'win_pct', 'off_rtg', 'def_rtg', 'net_rtg', 'srs']
    with open(filename, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for data in data_list:
            writer.writerow(data)

def scrape_season(year):
    teams = [
        # Western Conference:
        "HOU", "DAL", "SAS", "MEM", "NOP", # Southwest Division
        "LAL", "LAC", "SAC", "GSW", "PHO", # Pacific Division
        "DEN", "POR", "OKC", "UTA", "MIN", # Northwest Division
        # Eastern Conference:
        "ATL", "ORL", "MIA", "WAS", "CHO", # Southeast Division
        "BOS", "PHI", "BRK", "NYK", "TOR", # Atlantic Division
        "IND", "DET", "MIL", "CHI", "CLE"  # Central Division
    ]
    all_data = []
    for team in teams:
        url = f"https://www.basketball-reference.com/teams/{team}/{year}.html"
        try:
            print(f"Scraping {team} {year}...")
            data = extract_team_stats(url)
            all_data.append(data)
            time.sleep(2) # Be kind to the server
        except Exception as e:
            print(f"Failed to scrape {team} {year}: {e}")
    write_to_csv(all_data, f"nba_team_stats_{year}.csv")

# Season to scrape:
scrape_season(2015) # Change this to the desired season as needed
