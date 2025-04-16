import requests
from bs4 import BeautifulSoup
import time
import csv

# ----------- Editable Field -----------
input_season = 2015
# --------------------------------------

season_start_year = input_season - 1
season = f"{season_start_year}-{str(input_season)[-2:]}"

# NBA teams in Wikipedia URL format
teams = [
    # Western Conferece:
    # -
    # Southwest Division:
    "Houston_Rockets", "Dallas Mavericks", "New Orleans Pelicans", "Memphis Grizzlies", "San Antonio Spurs",
    # Northwest Division:
    "Denver_Nuggets", "Minnesota_Timberwolves", "Oklahoma_City_Thunder", "Portland_Trail_Blazers", "Utah_Jazz",
    # Pacific Division:
    "Golden_State_Warriors", "Los_Angeles_Clippers", "Los_Angeles_Lakers", "Phoenix_Suns", "Sacramento_Kings",
    # ------------------------------------------------------
    # Eastern Conference:
    # -
    # Atlantic Division:
    "Brooklyn_Nets", "Boston_Celtics", "New_York_Knicks", "Philadelphia_76ers", "Toronto_Raptors",
    # Central Division:
    "Chicago_Bulls", "Cleveland_Cavaliers", "Detroit_Pistons", "Indiana_Pacers", "Milwaukee_Bucks",
    # Southeast Division:
    "Atlanta_Hawks", "Charlotte_Hornets", "Miami_Heat", "Orlando_Magic", "Washington_Wizards"
]

headers = {
    'User-Agent': 'Mozilla/5.0'
}

def get_team_player_links(season, team):
    url = f"https://en.wikipedia.org/wiki/{season}_{team}_season"
    print(f"\n🔍 Scraping: {url}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to load page: {url}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    player_links = []

    season_dash = season.replace("-", "–")
    team_spaces = team.replace("_", " ")
    target_caption = f"{season_dash} {team_spaces} roster"

    for caption in soup.find_all('caption'):
        if target_caption in caption.text:
            roster_table = caption.find_parent('table')
            if roster_table:
                for row in roster_table.find_all('tr')[1:]:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        player_tag = cells[2].find('a', href=True)
                        if player_tag:
                            name = player_tag.text.strip()
                            link = f"https://en.wikipedia.org{player_tag['href']}"
                            player_links.append((name, link))
    return player_links

def get_player_playoff_games(player_url, cutoff_year):
    try:
        response = requests.get(player_url, headers=headers)
        response.raise_for_status()
    except:
        return 0

    soup = BeautifulSoup(response.content, 'html.parser')
    playoffs_heading = soup.find(id="Playoffs")
    if not playoffs_heading:
        return 0

    table = playoffs_heading.find_next('table', class_='wikitable')
    if not table:
        return 0

    total_gp = 0

    for row in table.find_all('tr'):
        cells = row.find_all('td')
        if not cells or len(cells) < 3:
            continue

        year_cell = cells[0].text.strip()
        try:
            year = int(year_cell[:4])
        except ValueError:
            continue

        if year >= cutoff_year:
            continue

        try:
            gp = int(cells[2].text.strip().replace("*", "").replace("†", ""))
            total_gp += gp
        except ValueError:
            continue

    return total_gp

# Main loop
output_rows = []

for team in teams:
    player_links = get_team_player_links(season, team)
    team_total = 0
    player_data = []

    for name, link in player_links:
        gp = get_player_playoff_games(link, input_season)
        team_total += gp
        player_data.append((name, gp))
        print(f"{name}: {gp} playoff games")
        time.sleep(0.5)

    print(f"\n🧍 Total players: {len(player_data)}")
    print(f"📊 {team.replace('_', ' ')} total playoff games: {team_total}\n")

    output_rows.append([team.replace("_", " "), input_season, team_total])

# Write to CSV
csv_filename = f"team_playoff_experience_{input_season}.csv"
with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Team", "Season", "Total Playoff Games"])
    writer.writerows(output_rows)

print(f"✅ CSV file saved as: {csv_filename}")