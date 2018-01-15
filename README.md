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
python mtggoldfish.py -b -u
```
Specifying the "-u" flag informs the script to ignore any and all cached deck data for this run, and instead fetch fresh data. This flag can be tacked onto either the default (Owned Cards) analysis, or the Budget Deck analysis. Specifically, the following actions will be performed:
1. All decks listed in *desired_decks.txt* will be parsed from MTGGoldfish.com. **This will disregard any cached data and perform a new fetch.**
2. If the "-b" flag is also set, all Modern Budget decks from https://www.mtggoldfish.com/decks/budget/modern#paper will be parsed. **This will disregard any cached data and perform a new fetch.**
3. For each deck listed in *desired_decks.txt*, a report will be generated using the information in *owned_cards.txt*, if any. The report will tell you how many cards you already own in each deck in *desired_decks.txt*, how much paper value that translates to, as well as list the quantities and names of those cards.
4. If the "-b" flag is set, for each deck listed in *desired_decks.txt*, a report will be generated listing the top-five Budget Modern decks that overlap the most (according to paper value), sorted descending. It will list how much value overlaps, as well as the number of cards. This will not actually list the cards, however, as that would generate excessive output.

# Example Output
This is an example of a run with the "-b" flag set. In this example, all of the deck data had already been cached from a prior run.
```bash
=====================================================
================ Beginning Fresh Run ================
=====================================================
- Fetching Deck information of desired decks...
  Finished fetching deck data. 5 of 5 decks fetched from the cache.
- Budget flag set. Fetching Deck information of all Modern Budget decks for budget analysis...
  Finished fetching deck data. 69 of 69 decks fetched from the cache.
  Done fetching all Deck information. Fetch took 7.35 seconds

- Beginning Owned Cards evaluations...

- Beginning Budget Deck List evaluations...

============================================
================ Report(s) =================
============================================

== Owned cards that are used in "Humans" ($1079.54) ==
   Number of cards owned: 2/74
   Value saved: $103.70
   Remaining cost: $975.84
   List of specific cards:
      1x Noble Hierarch ($55.20)
      1x Dark Confidant ($48.50)

== Owned cards that are used in "Eldrazi Tron" ($680.82) ==
   None of the cards you own overlap with this deck :(

== Owned cards that are used in "Affinity" ($822.68) ==
   None of the cards you own overlap with this deck :(

== Owned cards that are used in "Tron" ($628.42) ==
   Number of cards owned: 3/73
   Value saved: $210.06
   Remaining cost: $418.36
   List of specific cards:
      3x Karn Liberated ($210.06)

== Owned cards that are used in "Abzan" ($1280.05) ==
   Number of cards owned: 3/72
   Value saved: $218.57
   Remaining cost: $1061.48
   List of specific cards:
      2x Tarmogoyf ($131.58)
      1x Liliana of the Veil ($86.99)

== Budget Decks that compare to "Humans" ($1079.54) ==
   Budget Deck: Mono-White Humans
      Budget Deck cost: $132.37
      Number of cards shared: 12/74
      Value shared: $85.52
   Budget Deck: Stake Sisters
      Budget Deck cost: $112.44
      Number of cards shared: 4/74
      Value shared: $17.84
   Budget Deck: Beatdown Elves
      Budget Deck cost: $81.6
      Number of cards shared: 2/74
      Value shared: $8.16
   Budget Deck: GB Zombies
      Budget Deck cost: $99.41
      Number of cards shared: 2/74
      Value shared: $5.50
   Budget Deck: UB Mill
      Budget Deck cost: $194.68
      Number of cards shared: 2/74
      Value shared: $5.50

== Budget Decks that compare to "Eldrazi Tron" ($680.82) ==
   Budget Deck: Mono-Blue Colossus
      Budget Deck cost: $100.04
      Number of cards shared: 11/75
      Value shared: $30.69
   Budget Deck: Trading Post Tron
      Budget Deck cost: $90.76
      Number of cards shared: 18/75
      Value shared: $29.80
   Budget Deck: Mono-Green Aggro
      Budget Deck cost: $61.41
      Number of cards shared: 9/75
      Value shared: $23.79
   Budget Deck: Mono-Black Vehicles
      Budget Deck cost: $82.14
      Number of cards shared: 8/75
      Value shared: $21.68
   Budget Deck: Favorable Winds
      Budget Deck cost: $97.75
      Number of cards shared: 7/75
      Value shared: $20.67

== Budget Decks that compare to "Affinity" ($822.68) ==
   Budget Deck: UW Tempered Steel 
      Budget Deck cost: $95.61
      Number of cards shared: 32/74
      Value shared: $48.34
   Budget Deck: UB Mill
      Budget Deck cost: $194.68
      Number of cards shared: 1/74
      Value shared: $18.97
   Budget Deck: Heartless Summoning
      Budget Deck cost: $162.81
      Number of cards shared: 1/74
      Value shared: $18.97
   Budget Deck: Fruity Pebbles
      Budget Deck cost: $106.48
      Number of cards shared: 6/74
      Value shared: $4.16
   Budget Deck: Turn Two Tokens
      Budget Deck cost: $72.14
      Number of cards shared: 6/74
      Value shared: $4.16

== Budget Decks that compare to "Tron" ($628.42) ==
   Budget Deck: Trading Post Tron
      Budget Deck cost: $90.76
      Number of cards shared: 18/73
      Value shared: $29.80
   Budget Deck: Ironworks Combo
      Budget Deck cost: $162.51
      Number of cards shared: 10/73
      Value shared: $18.92
   Budget Deck: Red-White Allies
      Budget Deck cost: $104.51
      Number of cards shared: 5/73
      Value shared: $16.65
   Budget Deck: UR Summonings
      Budget Deck cost: $89.64
      Number of cards shared: 5/73
      Value shared: $16.65
   Budget Deck: Favorable Winds
      Budget Deck cost: $97.75
      Number of cards shared: 5/73
      Value shared: $15.17

== Budget Decks that compare to "Abzan" ($1280.05) ==
   Budget Deck: Abzan Rites
      Budget Deck cost: $94.57
      Number of cards shared: 15/72
      Value shared: $45.42
   Budget Deck: WB Aristocrats
      Budget Deck cost: $101.95
      Number of cards shared: 12/72
      Value shared: $39.49
   Budget Deck: UB Mill
      Budget Deck cost: $194.68
      Number of cards shared: 2/72
      Value shared: $37.94
   Budget Deck: Heartless Summoning
      Budget Deck cost: $162.81
      Number of cards shared: 2/72
      Value shared: $37.94
   Budget Deck: Mono-White Emeria Control
      Budget Deck cost: $117.38
      Number of cards shared: 5/72
      Value shared: $31.16
```
