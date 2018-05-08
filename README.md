# MTGGoldfishScraper
The entire point of this script is to help you determine how close you are to building the Metagame decks in the Magic Format of your choice (Modern, Standard, Commander, etc) that interest you based on the cards you currently own, as well as showing you the top five Budget decks in that Format that share the most value (paper price) with those Modern Metagame decks. MTGGoldfish.com is the source for all of the deck information.

# Setup
Download all of the files to the *same* directory. Namely, **mtggoldfish.py**, **owned_cards.txt**, and **desired_decks.txt**. It doesn't matter if you do proper git things and clone this repository, or if you simply copy and paste the files, the important thing is that they must all be in the same directory on your computer.
## OSX
1. Install the Selenium Python library
```bash
pip install Selenium
```
2. Install the "progress" Python library (for nice-looking progress bars)
```bash
pip install progress
```
3. Go to https://github.com/mozilla/geckodriver/releases and download the Firefox geckodriver for your OS. This is a sub-dependency of Selenium, as this script uses the Firefox WebDriver
4. Add "geckodriver" to your PATH
5. Install FireFox on your computer if you haven't already.
	* **Note** that minor issues can arise due to nuanced differences in FireFox versions and the Selenium API. While I cannot possibly document all of those here, just know that your most likely solution will be to install an older version of FireFox

## Windows
At the time of writing this I can't say that I support Windows. However, the script doesn't make any assumptions about directory structure, so that should hold up. I'm just wondering whether or not my hard-coded newline characters might be a problem when parsing the files and printing to the terminal. The TL;DR is that **I have not tested this on Windows**. If someone else wants to do this testing (and provide Setup instructions for this README) for Windows, I would gladly accept any Pull Requests.

# Usage
## Configuration
This script utilizes two separate configuration files:
* **desired_decks.txt** - This is where you list the **URLs** of the Modern (or the format specified via the -F flag) Metagame decks you're interested in building towards. These URLs *must* be links to decks in the "Modern" sub-section of the "Metagame" decks section on MTGGoldfish.com, as this script does HTML parsing based on the specific layouts/elements of these pages. One URL is provided as an example. Having URLs here is required in order to perform the "Owned Cards" or "Budget Deck" analyses.
* **owned_cards.txt** - This is where you can list the cards you own as well as their quantities. Obviously, you shouldn't be listing all of the cards you own here. Think of it this way: if you can say *"this card is worth more than a few dollars and I'm pretty sure it's used somewhere in the Meta that I want to have analyzed"* about a card that you own, you should list it in owned_cards.txt. One example (of a card that doesn't exist) is provided for syntax.

## Caching
This script utilizes local caching of deck data so that web-scraping is not required on each run, as the web-scraping can take 15 minutes or more to fetch all deck data for the Budget decks and the desired decks (depending on how many desired decks you list). When the script is run, if any cached decks are older than 30 days, a warning message is displayed recommending that you update your deck data. Deck data can be updated via the "-u" flag.

## Execution
```bash
python mtggoldfish.py -h
```
Displays detailed help for the script, explaining the various flags

```bash
python mtggoldfish.py -f
```
Instructs the script to write all final reports out to a text file. The file will be created in the same directory as the script, with the naming format: **deck_report_MM_DD_YYYY.txt**. This flag can be combined with any variation of the other flags.

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
2. All Modern (or the format specified via the -F flag) Budget decks from https://www.mtggoldfish.com/decks/budget/modern#paper will be parsed. Cached data will be used instead for any decks that have been previously fetched.
3. For each deck listed in *desired_decks.txt*, a report will be generated using the information in *owned_cards.txt*, if any. The report will tell you how many cards you already own in each deck in *desired_decks.txt*, how much paper value that translates to, as well as list the quantities and names of those cards.
4. For each deck listed in *desired_decks.txt*, a report will be generated listing the top-five Budget Modern (or the format specified via the -F flag) decks that overlap the most (according to paper value), sorted descending. It will list how much value overlaps, as well as the number of cards. This will not actually list the cards, however, as that would generate excessive output. The report will, however, use any cards listed in *owned_cards.txt* to generate a report of how many cards from each budget deck you already own, together with their value and a full list of the specific cards.

```bash
python mtggoldfish.py -r
```
Specifying the "-r" flag informs the script to parse all of the Modern (or the format specified via the -F flag) Metagame decks listed on MTGGoldfish.com and analyze the cards listed in *owned_cards.txt* to inform you the top 15 decks in the current Modern (or the format specified via the -F flag) Metagame that you are closest to completing (according to Paper Value). It does this in addition to the Owned Cards analysis from the default script behavior. Specifically, the following actions will be performed:
1. All decks listed in *desired_decks.txt* will be parsed from MTGGoldfish.com. Cached data will be used instead for any decks that have been previously fetched.
2. All Modern (or the format specified via the -F flag) Metagame decks from https://www.mtggoldfish.com/metagame/modern/full#paper will be parsed. Cached data will be used instead for any decks that have been previously fetched.
3. For each deck listed in *desired_decks.txt*, a report will be generated using the information in *owned_cards.txt*. The report will tell you how many cards you already own in each deck in *desired_decks.txt*, how much paper value that translates to, as well as list the quantities and names of those cards.
4. A report will be generated listing the top 15 Modern (or the format specified via the -F flag) Metagame decks that you are the closest to completing (according to paper value), sorted descending. It will list how much value of that deck you currently own, as well as the specific cards and quantities.

```bash
python mtggoldfish.py -u
python mtggoldfish.py -b -u
python mtggoldfish.py -r -u
python mtggoldfish.py -b -r -u -f
```
Specifying the "-u" flag informs the script to ignore any and all cached deck data for this run, and instead fetch fresh data. This flag can be tacked onto either the default (Owned Cards) analysis, or either of the "-r" or "-b" flags. Specifically, the following actions will be performed:
1. All decks listed in *desired_decks.txt* will be parsed from MTGGoldfish.com. **This will disregard any cached data and perform a new fetch.**
2. If the "-b" flag is also set, all Modern (or the format specified via the -F flag) Budget decks from https://www.mtggoldfish.com/decks/budget/modern#paper will be parsed. **This will disregard any cached data and perform a new fetch.**
3. If the "-r" flag is also set, all Modern (or the format specified via the -F flag) Metagame decks from https://www.mtggoldfish.com/metagame/modern/full#paper will be parsed. **This will disregard any cached data and perform a new fetch.**
4. For each deck listed in *desired_decks.txt*, a report will be generated using the information in *owned_cards.txt*, if any. The report will tell you how many cards you already own in each deck in *desired_decks.txt*, how much paper value that translates to, as well as list the quantities and names of those cards.
5. If either of the "-r" or "-b" flags were set, their report analysis will also be performed.

```bash
python mtggoldfish.py -o
python mtggoldfish.py -b -o
python mtggoldfish.py -r -o
python mtggoldfish.py -b -r -u -o -f
```
Specifying the "-o" flag informs the script to do all of the same analyses it would otherwise do, except use the online (tix) values instead of paper (dollar) values. If you don't pass this flag, paper values will be used. This flag can be combined with any variation of the other flags. **IMPORTANT:** If you already have cached deck data with the paper values, you will need to use the "-u" flag during your first run with this flag set so that the actual tix values will be pulled. This is also inversely true.

```bash
python mtggoldfish.py -F <FORMAT>
python mtggoldfish.py -b -F <FORMAT>
python mtggoldfish.py -r -F <FORMAT>
python mtggoldfish.py -b -r -F <FORMAT> -u -f -o
```
Specifying the "-F" (**uppercase** F) flag informs the script to do all of the same analyses it would otherwise do as specified by your other flags, except it will perform them on the MTG game Format of your choice. **If this flag is not set, Modern will be the format analyzed**. Valid game formats are any of the formats available on MTGGoldfish.com, specifically: Standard | Modern | Pauper | Legacy | Vintage | Frontier | Commander 1v1 | Commander | Tiny Leaders. This value is *case-insensitive*. This flag can be combined with any variation of the other flags.

# Example Output
This is an example of a run with the "-b" and "-r" flags set. In this example, all of the deck data had already been cached from a prior run.
```bash
python mtggoldfish.py -b -r

=====================================================
================ Beginning Fresh Run ================
=====================================================

Fetching Deck information for decks listed in desired_decks.txt.
   Finished fetching deck data. 1 of 1 decks were fetched from the cache.

Recommend flag set. Fetching Deck information of all Modern Metagame decks for Recommendation analysis...
   Opening a browser real quick to snapshot the URLs for all of the Modern Metagame decks on MTGGoldfish.com, as there might be new ones.
   Finished fetching deck data. 3 of 3 decks were fetched from the cache.

Budget flag set. Fetching Deck information of all Modern Budget decks for budget analysis...
   Opening a browser real quick to snapshot the URLs for all of the Budget decks on MTGGoldfish.com, as there might be new ones.
   Finished fetching deck data. 70 of 70 decks were fetched from the cache.

Done fetching all Deck information. Fetch took 8.60 seconds

Computing Modern Metagame Deck Recommendation evaluations...

Computing Budget Deck List evaluations...

============================================
================ Report(s) =================
============================================

=== Modern Metagame deck recommendation report based on Cards listed in owned_cards.txt ===

   #1 Closest Match:
      Modern Meta Deck: "Affinity" ($824.64)
      Number of cards owned: 4/74
      Value of cards owned: $89.97
      Remaining cost: $734.67
      List of specific cards:
         1x Arcbound Ravager ($42.00)
         3x Thoughtseize ($47.97)

   #2 Closest Match:
      Modern Meta Deck: "Grixis Death's Shadow" ($979.79)
      Number of cards owned: 7/73
      Value of cards owned: $81.92
      Remaining cost: $897.87
      List of specific cards:
         4x Thoughtseize ($63.96)
         1x Street Wraith ($6.99)
         1x Inquisition of Kozilek ($3.85)
         1x Fatal Push ($7.12)

=== Budget Deck report comparing against Desired Decks listed in desired_decks.txt ===
   Budget Decks that compare to Desired Deck: "Grixis Death's Shadow" ($979.79):

      #1 Closest Match:
         Budget Deck Name: WB Aristocrats
         Budget Deck cost: $102.59
         Number of cards shared: 6/67
         Value shared: $31.82
         Owned Cards Report:
            Number of cards owned: 2/67
            Value of cards owned: $10.97
            Remaining cost: $91.62
            List of specific cards:
               1x Fatal Push ($7.12)
               1x Inquisition of Kozilek ($3.85)

      #2 Closest Match:
         Budget Deck Name: Mono-Red Hollow One
         Budget Deck cost: $89.48
         Number of cards shared: 4/55
         Value shared: $27.96
         Owned Cards Report:
            Number of cards owned: 2/55
            Value of cards owned: $16.00
            Remaining cost: $73.48
            List of specific cards:
               1x Bloodghast ($9.01)
               1x Street Wraith ($6.99)

      #3 Closest Match:
         Budget Deck Name: 42 Land Swan Hunt
         Budget Deck cost: $93.09
         Number of cards shared: 2/48
         Value shared: $16.65
         Owned Cards Report:
               None of the cards listed in owned_cards.txt are used in this deck :(

      #4 Closest Match:
         Budget Deck Name: GB End
         Budget Deck cost: $82.71
         Number of cards shared: 3/64
         Value shared: $10.46
         Owned Cards Report:
            Number of cards owned: 1/64
            Value of cards owned: $3.85
            Remaining cost: $78.86
            List of specific cards:
               1x Inquisition of Kozilek ($3.85)

      #5 Closest Match:
         Budget Deck Name: Mono-Black Vehicles
         Budget Deck cost: $82.62
         Number of cards shared: 3/55
         Value shared: $10.46
         Owned Cards Report:
            Number of cards owned: 1/55
            Value of cards owned: $3.85
            Remaining cost: $78.77
            List of specific cards:
               1x Inquisition of Kozilek ($3.85)
```
