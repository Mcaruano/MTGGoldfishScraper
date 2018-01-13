# MTGGoldfishScraper
The entire point of this script is to help you determine how close you are to building the Modern Metagame decks that interest you based on the cards you currently own, as well as showing you the top five Modern Budget decks that share the most value (paper price) with those Modern Metagame decks. MTGGoldfish.com is the source for all of the deck information.

# Setup
1. Install the Selenium Python library
```bash
pip install Selenium
```
2. Go to https://github.com/mozilla/geckodriver/releases and download the Firefox geckodriver for your OS. This is a sub-dependency of Selenium, as this script uses the Firefox WebDriver
3. Add "geckodriver" to your PATH
4. Install FireFox on your computer if you haven't already.
	* **Note** that minor issues can arise due to nuanced differences in FireFox versions and the Selenium API. While I cannot possibly document all of those here, just know that your most likely solution will be to install an older version of FireFox

# Usage
## Configuration
This script utilizes two separate configuration files:
* **desired_decks.txt** - This is where you list the **URLs** of the Modern Metagame decks you're interested in building towards. These URLs *must* be links to decks in the "Modern" sub-section of the "Metagame" decks section on MTGGoldfish.com, as this script does HTML parsing based on the specific layouts/elements of these pages. One URL is provided as an example
* **owned_cards.txt** - This is where you can list the cards you own as well as their quantities. Obviously, you shouldn't be listing all of the cards you own here, just the cards that you know are used in the decks listed in desired_decks.txt. One example is provided.

## Caching
This script utilizes local caching of deck data so that web-scraping is not required on each run, as the web-scraping can take 15 minutes or more to fetch all deck data for the Budget decks and the desired decks (depending on how many desired decks you list). When the script is run, if any cached decks are older than 30 days, a warning message is displayed recommending that you update your deck data. Deck data can be updated via the "-u" flag.

## Execution
```bash
python mtggoldfish.py
```
Running this command will perform the following actions:
1. All decks listed in *desired_decks.txt* will be parsed from MTGGoldfish.com. Cached data will be used instead for any decks that have been previously fetched.
2. For each deck listed in *desired_decks.txt*, a report will be generated using the information in *owned_cards.txt*, if any. The report will tell you how many cards you already own in each deck in *desired_decks.txt*, how much paper value that translates to, as well as list the quantities and names of those cards.

```bash
python mtggoldfish.py -b
```
Specifying the "-b" flag informs the script to perform an analysis of all of the Budget decks on MTGGoldfish.com in addition to the Owned Cards analysis. Specifically, the following actions will be performed:
1. All decks listed in *desired_decks.txt* will be parsed from MTGGoldfish.com. Cached data will be used instead for any decks that have been previously fetched.
2. All Modern Budget decks from https://www.mtggoldfish.com/decks/budget/modern#paper will be parsed. Cached data will be used instead for any decks that have been previously fetched.
3. For each deck listed in *desired_decks.txt*, a report will be generated using the information in *owned_cards.txt*, if any. The report will tell you how many cards you already own in each deck in *desired_decks.txt*, how much paper value that translates to, as well as list the quantities and names of those cards.
4. For each deck listed in *desired_decks.txt*, a report will be generated listing the top-five Budget Modern decks that overlap the most (according to paper value), sorted descending. It will list how much value overlaps, as well as the number of cards. This will not actually list the cards, however, as that would generate excessive output.

```bash
python mtggoldfish.py -u
```
Specifying the "-u" flag informs the script to update all of the decks in the cache. Since the web-fetch is what takes the most time, by far, a Budget Analysis and Owned Cards Analysis is also provided. Specifically, the following actions will be performed:
1. All decks listed in *desired_decks.txt* will be parsed from MTGGoldfish.com. **This will disregard any cached data.**
2. All Modern Budget decks from https://www.mtggoldfish.com/decks/budget/modern#paper will be parsed. **This will disregard any cached data.**
3. For each deck listed in *desired_decks.txt*, a report will be generated using the information in *owned_cards.txt*, if any. The report will tell you how many cards you already own in each deck in *desired_decks.txt*, how much paper value that translates to, as well as list the quantities and names of those cards.
4. For each deck listed in *desired_decks.txt*, a report will be generated listing the top-five Budget Modern decks that overlap the most (according to paper value), sorted descending. It will list how much value overlaps, as well as the number of cards. This will not actually list the cards, however, as that would generate excessive output.


