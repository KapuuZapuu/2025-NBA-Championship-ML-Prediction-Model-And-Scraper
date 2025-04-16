import asyncio
import aiohttp
import aiohttp_client_cache
from bs4 import BeautifulSoup, Comment
import random
import re
import unicodedata
import csv

VERBOSE = False

teams = [
    # Western Conference
    # -
    # Pacific Division:
    "Golden_State_Warriors", "Sacramento_Kings", "Los_Angeles_Lakers", "Los_Angeles_Clippers",  "Phoenix_Suns", 
    # Northwest Division:
    "Portland_Trail_Blazers", "Utah_Jazz", "Denver_Nuggets", "Minnesota_Timberwolves", "Oklahoma_City_Thunder",
    # Southwest Division:
    "Houston_Rockets", "San_Antonio_Spurs", "Dallas_Mavericks", "New_Orleans_Pelicans", "Memphis_Grizzlies", 
    # Eastern Conference
    # -
    # Atlantic Division:
    "Brooklyn_Nets", "Toronto_Raptors", "Philadelphia_76ers", "Boston_Celtics", "New_York_Knicks",
    # Central Division:
    "Cleveland_Cavaliers", "Detroit_Pistons", "Indiana_Pacers", "Chicago_Bulls", "Milwaukee_Bucks",
    # Southeast Division:
    "Miami_Heat", "Atlanta_Hawks", "Charlotte_Hornets", "Orlando_Magic", "Washington_Wizards"
]

team_abbr_map = {
    # Western Conference
    # -
    # Pacific Division:
    "Golden State Warriors": "GSW", "Sacramento Kings": "SAC", "Los Angeles Lakers": "LAL",
    "Los Angeles Clippers": "LAC", "Phoenix Suns": "PHO",
    # Northwest Division:
    "Portland Trail Blazers": "POR", "Utah Jazz": "UTA", "Denver Nuggets": "DEN",
    "Minnesota Timberwolves": "MIN", "Oklahoma City Thunder": "OKC",
    # Southwest Division:
    "Houston Rockets": "HOU", "San Antonio Spurs": "SAS", "Dallas Mavericks": "DAL",
    "New Orleans Pelicans": "NOP", "Memphis Grizzlies": "MEM",
    # Eastern Conference
    # -
    # Atlantic Division:
    "Brooklyn Nets": "BRK", "Toronto Raptors": "TOR", "Philadelphia 76ers": "PHI",
    "Boston Celtics": "BOS", "New York Knicks": "NYK",
    # Central Division:
    "Cleveland Cavaliers": "CLE", "Detroit Pistons": "DET", "Indiana Pacers": "IND",
    "Chicago Bulls": "CHI", "Milwaukee Bucks": "MIL",
    # Southeast Division:
    "Miami Heat": "MIA", "Atlanta Hawks": "ATL", "Charlotte Hornets": "CHO",
    "Orlando Magic": "ORL", "Washington Wizards": "WAS"
}

# We define a semaphore and a helper for rate limiting.
# The original code allowed 10 req/min with a delay of 6-9 seconds.
# Now, to allow up to 20 req/min, we set the delay to a random value between 3 and 3.5 seconds.
RATE_LIMIT_DELAY_LOW = 3
RATE_LIMIT_DELAY_HIGH = 3.5
rate_limiter = asyncio.Semaphore(1)


async def safe_get(url, session):
    """A helper that makes a GET request while enforcing the rate limit and random delay."""
    async with rate_limiter:
        try:
            async with session.get(url) as response:
                text = await response.text()
        except Exception as e:
            print(f"⚠️ Error fetching {url}: {e}")
            return None
        # Enforce a delay before releasing the semaphore to respect rate limit
        await asyncio.sleep(random.uniform(RATE_LIMIT_DELAY_LOW, RATE_LIMIT_DELAY_HIGH))
        return text


async def get_team_player_names(season, team, session):
    url = f"https://en.wikipedia.org/wiki/{season}_{team}_season"
    print(f"🔍 Scraping Wikipedia for team roster: {url}")
    html = await safe_get(url, session)
    if html is None:
        print(f"❌ Failed to load page: {url}")
        return []
    soup = BeautifulSoup(html, 'html.parser')
    player_names = []
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
                            player_names.append(name)
    return player_names


def verify_player_team_season(bbr_html, target_season, target_team_abbr):
    soup = BeautifulSoup(bbr_html, 'html.parser')
    def process_table(table, source=""):
        if not table:
            if VERBOSE:
                print(f"❌ No table found in {source}")
            return False
        if VERBOSE:
            print(f"🧩 Found per_game_stats table in {source}!")
        tbody = table.find('tbody')
        if not tbody:
            if VERBOSE:
                print(f"❌ <tbody> missing in {source}")
            return False
        rows = tbody.find_all('tr')
        if VERBOSE:
            print(f"📊 Found {len(rows)} rows in {source}")
        for i, row in enumerate(rows):
            season_cell = row.find('th', {'data-stat': 'year_id'})
            team_cell = row.find('td', {'data-stat': 'team_name_abbr'})
            if VERBOSE:
                print(f"\n🔁 {source} Row {i+1}:")
                if season_cell:
                    print(f"   ✅ season: {season_cell.get_text(strip=True)}")
                if team_cell:
                    print(f"   ✅ team: {team_cell.get_text(strip=True)}")
            if season_cell and team_cell:
                season_raw = season_cell.get_text(strip=True)
                team_raw = team_cell.get_text(strip=True)
                if season_raw.endswith(str(target_season)[-2:]) and team_raw == target_team_abbr:
                    if VERBOSE:
                        print(f"✅ MATCH FOUND in {source}: {season_raw}, {team_raw}")
                    return True
        return False

    main_table = BeautifulSoup(bbr_html, 'html.parser').find('table', id='per_game_stats')
    if process_table(main_table, "main HTML"):
        return True
    for comment in BeautifulSoup(bbr_html, 'html.parser').find_all(string=lambda text: isinstance(text, Comment)):
        comment_soup = BeautifulSoup(comment, 'html.parser')
        table = comment_soup.find('table', id='per_game_stats')
        if process_table(table, "HTML comment"):
            return True
    return False


async def find_bbr_url_for_player(player_name, target_season, target_team_abbr, session):
    base_url = "https://www.basketball-reference.com/players"
    parts = player_name.strip().split()

    # Define suffix tokens (removing punctuation for matching)
    suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
    # Filter out tokens that are common suffixes
    parts = [p for p in parts if p.lower().replace(".", "") not in suffixes]

    if len(parts) < 2:
        print(f"⚠️ Skipping incomplete name: {player_name}")
        return None

    # If the first two tokens are initials (end with a period), combine them.
    if len(parts) >= 3 and parts[0].endswith('.') and parts[1].endswith('.'):
        first_name = parts[0] + parts[1]  # e.g., "A." + "J." becomes "A.J."
        last_name = parts[-1]
    else:
        first_name, last_name = parts[0], parts[-1]

    def ascii_only(text):
        return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    
    first_name_ascii = ascii_only(first_name)
    last_name_ascii = ascii_only(last_name)
    
    # Remove non-alphabetic characters from the first name to get correct initials.
    import re
    first_name_clean = re.sub(r'[^A-Za-z]', '', first_name_ascii)
    
    first_initial = last_name_ascii[0].lower()
    # Using first 5 of the last name and first 2 letters of the cleaned first name.
    lookup_slug = (last_name_ascii[:5] + first_name_clean[:2]).lower()
    lookup_slug = re.sub(r'[^a-z]', '', lookup_slug)

    def normalize_and_standardize_name(name):
        name = unicodedata.normalize("NFKD", name)
        name = re.sub(r'[^\w\s]', '', name)
        tokens = name.strip().split()
        suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
        reordered = []
        for token in tokens:
            if token.lower() in suffixes:
                reordered.insert(1, token.lower())
            else:
                reordered.append(token.lower())
        return ''.join(reordered)

    # Try a few slug variations.
    for i in range(1, 9):
        suffix = f"{i:02d}"
        slug = f"{lookup_slug}{suffix}"
        url = f"{base_url}/{first_initial}/{slug}.html"
        html = await safe_get(url, session)
        if not html:
            continue
        if verify_player_team_season(html, target_season, target_team_abbr):
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.find('title')
            if not title_tag:
                continue
            title_text = title_tag.text.strip()
            bbr_name = title_text.split(" Stats")[0]
            norm_bbr = normalize_and_standardize_name(bbr_name)
            norm_target = normalize_and_standardize_name(player_name)
            print(f"✅ Verified Match: {player_name} → {url} ({bbr_name})")
            return url
        else:
            print(f"❌ {player_name} not active for {target_team_abbr} in {target_season} at {url}")
    print(f"❌ No match found for {player_name}")
    return None


async def get_player_vorp(bbr_url, season_str, session):
    """
    Given a player's Basketball Reference URL and season string (e.g., '2021-22'),
    fetch the advanced stats table (including those in HTML comments) and extract VORP.
    """
    html = await safe_get(bbr_url, session)
    if not html:
        print(f"❌ Could not load advanced stats for {bbr_url}")
        return None
    soup = BeautifulSoup(html, 'html.parser')
    advanced_table = soup.find('table', id='advanced')

    def extract_vorp_from_table(table):
        if not table:
            return None
        tbody = table.find('tbody')
        if not tbody:
            return None
        rows = tbody.find_all('tr', id=lambda x: x and x.startswith("advanced."))
        for row in rows:
            year_cell = row.find('th', {'data-stat': 'year_id'})
            if not year_cell:
                continue
            season_text = year_cell.get_text(strip=True)
            if season_text == season_str:
                vorp_cell = row.find('td', {'data-stat': 'vorp'})
                if vorp_cell:
                    vorp_raw = vorp_cell.get_text(strip=True)
                    try:
                        return float(vorp_raw)
                    except:
                        return None
        return None

    vorp = extract_vorp_from_table(advanced_table)
    if vorp is not None:
        return vorp
    # Fallback: check within HTML comments.
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment_soup = BeautifulSoup(comment, 'html.parser')
        table = comment_soup.find('table', id='advanced')
        vorp = extract_vorp_from_table(table)
        if vorp is not None:
            return vorp
    return None


async def main():
    input_season = 2023 # Change this to the desired season
    season = f"{input_season - 1}-{str(input_season)[-2:]}"  # e.g., "2021-22"
    results = []
    team_vorp = {}

    # Create an asynchronous cached session.
    async with aiohttp_client_cache.CachedSession(
            cache_name='basketball_cache', expire_after=86400,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/'
            }) as session:

        # Loop through teams sequentially.
        for team in teams:
            full_team_name = team.replace("_", " ")
            team_abbr = team_abbr_map.get(full_team_name)
            wiki_url = f"https://en.wikipedia.org/wiki/{season}_{team}_season"
            print(f"\n🔍 Scraping Wikipedia: {wiki_url}")
            player_names = await get_team_player_names(season, team, session)
            for player_name in player_names:
                print(f"{full_team_name} - {player_name}")
                bbr_url = await find_bbr_url_for_player(player_name, input_season, team_abbr, session)
                if bbr_url:
                    vorp = await get_player_vorp(bbr_url, season, session)
                    if vorp is not None:
                        print(f"   ↪ VORP for {season}: {vorp}")
                    else:
                        print(f"   ↪ No VORP data found for {season}")
                    results.append((full_team_name, player_name, bbr_url, vorp))
                    if vorp is not None:
                        team_vorp.setdefault(full_team_name, []).append((player_name, vorp))
                else:
                    results.append((full_team_name, player_name, "❌ Not Found", None))
                # (safe_get already delays, so no additional sleep required here)

            print("-" * 50)

        print("\n📋 FINAL RESULTS:")
        for team_name, player, link, vorp in results:
            print(f"{team_name} - {player}: {link} - VORP: {vorp}")

        # Prepare CSV rows.
        csv_rows = []
        header = ["team", "season", "player1vorp", "player2vorp", "player3vorp", "player4vorp",
                  "player5vorp", "player6vorp", "player7vorp", "player8vorp", "player9vorp"]
        csv_rows.append(header)

        print("\n🏆 TOP 9 Player VORPs by Team:")
        for team_name, players in team_vorp.items():
            sorted_players = sorted(players, key=lambda x: x[1], reverse=True)
            top9 = [p[1] for p in sorted_players[:9]]
            top9 += [""] * (9 - len(top9))
            print(f"{team_name} ({season}):")
            for i, (player, vorp) in enumerate(sorted_players[:9], start=1):
                print(f"  {i}. {player} (VORP: {vorp})")
            row = [team_name, input_season] + top9
            csv_rows.append(row)

        csv_filename = f"team_top9_vorp_{input_season}.csv"
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as f:
            import csv
            writer = csv.writer(f)
            writer.writerows(csv_rows)
        print(f"\n✅ CSV file written: {csv_filename}")


if __name__ == "__main__":
    asyncio.run(main())