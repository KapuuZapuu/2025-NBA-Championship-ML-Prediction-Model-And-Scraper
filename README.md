# 2025 NBA Championship Prediction Model & Scraper
The following files were used to aquire data from various websites in order to build a machine learning prediction model for the 2025 NBA Championship:
* top10VORPold.py
* totalplayoffgames.py
* basketballreferencescrapertocsv.py
Additionally, the following files were created during the process, but weren't used in the eventual model:
* top10VORPnew.py
* topten2kratingscraper.py

Make sure you setup a virtual environment and install any dependencies or libraries to get these scripts to work.

Some things to note:
* top10VORPold.py takes ~75 minutes to complete for a single input season. Some players with weird names won't get identified, so you will need to input their VORP into the .csv manually. Basketball Reference and Wikipedia have some inconsistencies with the way their pages are set up, therefore some entire teams may not show up in the final .csv file, so check and make the manual additions accordingly
* totalplayoffgames.py may miss a team here and there-- indicated when a team has 0 playoff games of experience in the final .csv output-- in which case you have to manually edit the file to correct for this
* basketballreferencescrapertocsv.py has issues with older seasons, as the formatting for final seeding placement changes pre-2016, so you will have to manually input those as well. The file also doesn't account for historical teams like the Charlotte Bobcats or the Seattle SuperSonics (changes to the code's teams searched will fix this-- i.e. changing CHO to CHA from the Charlotte Hornets to the Charlotte Bobcats respectively).
* topten2kratingscraper.py only works for historical 2k ratings-- it can't pull ratings from the current game year.
* top10VORPnew.py was intended to be used as a replacement for top10VORPold.py using an API (https://github.com/vishaalagartha/basketball_reference_scraper), but it's functionality was limited in terms of what I needed.
