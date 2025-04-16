import csv
import time
import cloudscraper
from bs4 import BeautifulSoup

def get_top_10_ovrs(team_slug, season_label):
    url = f"https://www.2kratings.com/teams/{team_slug}"
    print(f"Fetching URL: {url}")

    scraper = cloudscraper.create_scraper()
    response = scraper.get(url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')

    # Debug: print a small portion of page to see what it contains
    print("Preview of page source:")
    print(soup.prettify()[:1000])

    # Find correct section using nav ID instead of p-tag text
    nav_id = f"nav-2k{str(int(season_label.split('-')[1]))[-2:]}-tab"
    print(f"Looking for nav section ID: {nav_id}")
    nav_div = soup.find('h5', id=nav_id)
    if not nav_div:
        print(f"Could not find nav section ID {nav_id} in {team_slug}")
        return [None] * 10

    # Find the table following this div
    table = nav_div.find_next('table')
    if not table:
        print(f"No table found for section ID {nav_id} in {team_slug}")
        return [None] * 10

    ovr_list = []
    for row in table.find_all('tr')[1:]:
        cells = row.find_all('td')
        if len(cells) >= 3:
            span = cells[2].find('span')
            if span and span.has_attr('data-order'):
                try:
                    ovr = int(float(span['data-order']))
                    ovr_list.append(ovr)
                except ValueError:
                    pass

    print(f"Found OVRs for {team_slug}: {ovr_list[:10]}")
    return ovr_list[:10] + [None] * (10 - len(ovr_list[:10]))

def write_ovr_csv(year):
    team_slug_map = {
        # Western Conference:
        # -
        # Northwest Division:
        "DEN": "denver-nuggets", 
        "MIN": "minnesota-timberwolves", 
        "POR": "portland-trail-blazers", 
        "OKC": "oklahoma-city-thunder",
        "UTA": "utah-jazz",
        # Southwest Division:
        "HOU": "houston-rockets",
        "DAL": "dallas-mavericks",
        "MEM": "memphis-grizzlies",
        "NOP": "new-orleans-pelicans",
        "SAS": "san-antonio-spurs",
        # Pacific Division:
        "GSW": "golden-state-warriors",
        "LAL": "los-angeles-lakers",
        "LAC": "los-angeles-clippers",
        "PHO": "phoenix-suns",
        "SAC": "sacramento-kings",
        # ------------------------------------------------------
        # Eastern Conference:
        # -
        # Atlantic Division:
        "BOS": "boston-celtics",
        "PHI": "philadelphia-76ers",
        "TOR": "toronto-raptors",
        "NYK": "new-york-knicks",
        "BRK": "brooklyn-nets",
        # Central Division:
        "MIL": "milwaukee-bucks",
        "CLE": "cleveland-cavaliers",
        "CHI": "chicago-bulls",
        "DET": "detroit-pistons",
        "IND": "indiana-pacers",
        # Southeast Division:
        "MIA": "miami-heat",
        "ATL": "atlanta-hawks",
        "WAS": "washington-wizards",
        "CHO": "charlotte-hornets",
        "ORL": "orlando-magic"
    }

    fieldnames = ['team', 'season'] + [f'player_{i+1}' for i in range(10)]
    all_data = []

    for abbr, slug in team_slug_map.items():
        season_label = f"{year - 1}-{year}"
        print(f"\nScraping {abbr} for {season_label}...")
        ovrs = get_top_10_ovrs(slug, season_label)
        row = {'team': abbr, 'season': year}  # Use END year of season
        for i in range(10):
            row[f'player_{i+1}'] = ovrs[i]
        all_data.append(row)
        time.sleep(1)

    with open(f"top_10_ovrs_{year}.csv", mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_data:
            writer.writerow(row)

write_ovr_csv(2015) # Change this to the desired season as needed