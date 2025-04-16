import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import sys

# Import functions from the basketball_reference_scraper API.
from basketball_reference_scraper.teams import get_roster
from basketball_reference_scraper.players import get_stats

# --- Mapping Team Abbreviations to Full Names ---
# Note: Ensure these names match the Wikipedia page titles. Some team names might differ.
TEAM_MAPPING = {
    'ATL': 'Atlanta Hawks',
    'BOS': 'Boston Celtics',
    'BRK': 'Brooklyn Nets',
    'CHI': 'Chicago Bulls',
    'CHO': 'Charlotte Hornets',
    'CLE': 'Cleveland Cavaliers',
    'DAL': 'Dallas Mavericks',
    'DEN': 'Denver Nuggets',
    'DET': 'Detroit Pistons',
    'GSW': 'Golden State Warriors',
    'HOU': 'Houston Rockets',
    'IND': 'Indiana Pacers',
    'LAC': 'Los Angeles Clippers',
    'LAL': 'Los Angeles Lakers',
    'MEM': 'Memphis Grizzlies',
    'MIA': 'Miami Heat',
    'MIL': 'Milwaukee Bucks',
    'MIN': 'Minnesota Timberwolves',
    'NOP': 'New Orleans Pelicans',
    'NYK': 'New York Knicks',
    'OKC': 'Oklahoma City Thunder',
    'ORL': 'Orlando Magic',
    'PHI': 'Philadelphia 76ers',
    'PHO': 'Phoenix Suns',
    'POR': 'Portland Trail Blazers',
    'SAC': 'Sacramento Kings',
    'SAS': 'San Antonio Spurs',
    'TOR': 'Toronto Raptors',
    'UTA': 'Utah Jazz',
    'WAS': 'Washington Wizards'
}

# --- Helper Function to Construct Wikipedia URL ---
def construct_wikipedia_url(season_input, team_full_name):
    """
    Construct Wikipedia URL for the season page.
    
    The Wikipedia URL typically uses an en dash (–) between years.
    Example: "2021–22 Golden State Warriors season"
    """
    # Replace hyphen with en dash if necessary.
    season_en_dash = season_input.replace('-', '–')
    # Construct the page title.
    page_title = f"{season_en_dash} {team_full_name} season"
    # Replace spaces with underscores for the URL.
    page_title_url = page_title.replace(" ", "_")
    url = f"https://en.wikipedia.org/wiki/{page_title_url}"
    return url

# --- Function to Scrape the Roster Names from a Wikipedia Season Page ---
def get_wikipedia_roster(url):
    """
    Scrape the Wikipedia season page for the team roster.
    This function attempts to find a table that contains roster information 
    by searching for table headers that include 'Player'.
    Returns a list of player names.
    """
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Warning: Unable to retrieve {url} (HTTP {response.status_code})")
            return []
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Attempt to find all tables
        tables = soup.find_all("table", {"class": "wikitable"})
        roster_names = []
        for table in tables:
            headers = [th.get_text().strip().lower() for th in table.find_all("th")]
            # Look for a header that suggests a player column.
            if any("player" in header for header in headers):
                # Assume the first column contains the player names.
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all(["td", "th"])
                    if cols:
                        # Clean up the player name string.
                        player = cols[0].get_text().strip()
                        if player:
                            roster_names.append(player)
                # Once a roster is found, break.
                if roster_names:
                    break
        return roster_names
    except Exception as e:
        print(f"Error scraping Wikipedia URL {url}: {e}")
        return []

# --- Function to Get a Player's VORP from their Advanced Stats ---
def get_player_vorp(player_name, season_input):
    """
    Uses the basketball_reference_scraper players.get_stats method to get advanced stats.
    Attempts to extract the player's VORP (assumed to be in the column 'ADVANCED_VORP').
    If the returned DataFrame has multiple seasons, we try to filter on the season.
    """
    try:
        # Fetch advanced stats; we assume non-playoffs, non-career mode returns season-specific stats.
        stats_df = get_stats(player_name, stat_type='ADVANCED', playoffs=False, career=False)
        if stats_df is None or stats_df.empty:
            return None
        # If a 'SEASON' column exists, try to filter on season.
        if 'SEASON' in stats_df.columns:
            # The season in the API might be formatted in a similar or different manner.
            # We attempt a case-insensitive substring search.
            matched = stats_df[stats_df['SEASON'].astype(str).str.contains(season_input.split("-")[0])]
            if not matched.empty:
                stats_row = matched.iloc[0]
            else:
                stats_row = stats_df.iloc[0]
        else:
            stats_row = stats_df.iloc[0]
        # Retrieve VORP from the advanced stats. The column name might be 'ADVANCED_VORP' or similar.
        # Adjust the column name if necessary.
        vorp = stats_row.get('ADVANCED_VORP', None)
        if vorp is None:
            # Fall back to alternative possible key name
            vorp = stats_row.get('VORP', None)
        # Convert to float if possible.
        try:
            return float(vorp)
        except (TypeError, ValueError):
            return None
    except Exception as e:
        print(f"Error retrieving advanced stats for {player_name}: {e}")
        return None

# --- Main Script ---
def main():
    season_input = input("Enter NBA season (e.g. 2021-22): ").strip()
    # Determine the season end year: assume second part of the season input.
    try:
        season_end_year = int(season_input.split("-")[1])
    except (IndexError, ValueError):
        print("Invalid season format. Please use the format 'YYYY-YY'")
        sys.exit(1)
        
    # This dictionary will store per-team top 9 VORP players.
    team_top9_dict = {}
    # To keep a running summary of all validated players and their VORP for the season.
    validated_players_summary = []

    # Loop over each team abbreviation in the mapping.
    for team_abbrev, team_full_name in TEAM_MAPPING.items():
        print(f"\nProcessing team: {team_full_name} ({team_abbrev}) for season {season_input}")
        # Step 1: Get the Basketball Reference roster
        try:
            bbr_roster = get_roster(team_abbrev, season_end_year)
            # Assume the player's names are in the column 'PLAYER'
            if 'PLAYER' not in bbr_roster.columns:
                print(f"Warning: Roster for {team_full_name} does not contain a 'PLAYER' column.")
                continue
            bbr_player_names = set(bbr_roster['PLAYER'].str.strip().tolist())
        except Exception as e:
            print(f"Error retrieving roster for {team_full_name}: {e}")
            continue

        # Step 2: Scrape the Wikipedia roster
        wiki_url = construct_wikipedia_url(season_input, team_full_name)
        wiki_players = get_wikipedia_roster(wiki_url)
        wiki_player_names = set(name.strip() for name in wiki_players)
        if not wiki_player_names:
            print(f"Warning: No roster data found on Wikipedia for {team_full_name} ({wiki_url})")
        else:
            # Debug: print a few wikipedia players
            print(f"Found {len(wiki_player_names)} players on Wikipedia for {team_full_name}")

        # Cross-reference: players present in both
        validated_players = [player for player in bbr_player_names if player in wiki_player_names]
        if not validated_players:
            print(f"No validated players found for {team_full_name}. Skipping team.")
            continue

        # Step 3: For each validated player, get their VORP
        team_player_vorp = {}
        for player in validated_players:
            vorp = get_player_vorp(player, season_input)
            # Optionally add a short delay to be polite to remote servers
            time.sleep(0.5)
            if vorp is not None:
                team_player_vorp[player] = vorp
                print(f"Found {player}: VORP = {vorp:.2f}")
                validated_players_summary.append((team_full_name, player, vorp))
            else:
                print(f"Could not retrieve VORP for {player}")
        
        if not team_player_vorp:
            print(f"No VORP data found for any validated players on {team_full_name}.")
            continue
        
        # Step 4: Find the top 9 players by VORP for the team.
        sorted_players = sorted(team_player_vorp.items(), key=lambda x: x[1], reverse=True)
        top9 = [player for player, vorp in sorted_players[:9]]
        team_top9_dict[team_abbrev] = {
            'team_full_name': team_full_name,
            'season': season_input,
            'top9': top9
        }
    
    # Step 6: Output to CSV file
    output_rows = []
    for team_abbrev, data in team_top9_dict.items():
        row = {
            'Team': data['team_full_name'],
            'Season': data['season']
        }
        for i, player in enumerate(data['top9'], start=1):
            row[f"Top_{i}"] = player
        output_rows.append(row)
    output_df = pd.DataFrame(output_rows)
    output_filename = f"top9_vorp_{season_input.replace('-', '_')}.csv"
    output_df.to_csv(output_filename, index=False)
    print(f"\nCSV file '{output_filename}' created with the top 9 VORP players per team.")

    # Final summary: print total validated players and their VORP, compactly.
    if validated_players_summary:
        summary_df = pd.DataFrame(validated_players_summary, columns=["Team", "Player", "VORP"])
        # Group by team and then list the players succinctly.
        summary_group = summary_df.groupby("Team").agg(
            total_players=pd.NamedAgg(column="Player", aggfunc="count"),
            players_list=pd.NamedAgg(column="Player", aggfunc=lambda x: ", ".join(x))
        )
        print("\nSummary of validated players (per team):")
        print(summary_group)
    else:
        print("No validated player VORP data was found.")

if __name__ == "__main__":
    main()