# -*- coding: utf-8 -*-
"""
View README.md for usage: https://github.com/Mcaruano/MTGGoldfishScraper/blob/master/README.md
"""

import cPickle as pickle
from datetime import datetime
import errno
from optparse import OptionParser
import os
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import sys
import time

__author__ = "Matthew Caruano"
__date__ = "10/5/2017"


# Global variables for row indeces
QTY_INDEX = 0
NAME_INDEX = 1
PRICE_INDEX = 3

# Card dict keys
CARD_QTY_KEY = 'Card Quantity'
CARD_NAME_KEY = 'Card Name'
CARD_PRICE_KEY = 'Individual Card Price'

# Final Owned Cards Report dict keys
CARD_LIST_KEY = 'Card List'
NO_OWNED_OVERLAP_FLAG = 'No Overlap'
OWNED_CARDS_KEY = 'Owned Cards'
SAVED_VALUE_KEY = 'Saved Value'

# Final Budget Report dict keys
DECK_PRICE_KEY = 'Deck Price'
SHARED_CARDS_KEY = 'Shared Cards'
SHARED_VALUE_KEY = 'Shared Value'

"""
Deck class to contain all of the information pertaining to a single deck
"""
class Deck(object):
    def __init__(self):
        self.deck_name = ""
        self.deck_url = ""
        self.deck_date = datetime(1970,1,1)
        self.deck_price = 0.0
        self.deck_list = []

    def get_deck_name(self):
        return self.deck_name.encode('ascii')

    def get_deck_url(self):
        return self.deck_url

    def get_deck_date(self):
        return self.deck_date

    def get_deck_price(self):
        return self.deck_price

    def get_deck_list(self):
        return self.deck_list

    def get_deck_size(self):
        total_cards = 0
        for card_entry in self.deck_list:
            total_cards += card_entry[CARD_QTY_KEY]
        return total_cards

    def __str__(self):
        print_output = "Deck Name: %s\nDeck URL: %s\nDeck Date: %s\nDeck Price: %.2f\nDeck List:\n{\n" %(self.deck_name, self.deck_url, self.deck_date, self.deck_price)
        for card_entry in self.deck_list:
            print_output = print_output + "     %dx %s,\n" %(card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY])
        return print_output + "}"

"""
Checks all local cache dirs for the presence of this deck using the MTGGoldfish DeckID, as
parsed from the Deck URL.

:param deck_id: The DeckID of this deck on MTGGoldfish
"""
def is_deck_cached(deck_id):
    cache_dir = os.path.join(os.path.dirname(__file__), 'deck_cache')
    if not os.path.isdir(cache_dir): return False

    cached_decks = os.listdir(cache_dir)
    for cached_deck_file_name in cached_decks:

        # The deck file names are of the format <deck_id>_MM_DD_YYYY
        cached_deck_id = cached_deck_file_name.split('_')[0]
        if cached_deck_id == deck_id: return True

    return False

"""
Given a DeckID, parses the MM_DD_YYYY portion of a cached deck file name
and returns true if the date is >= 30 days old

:param deck_id: The DeckID of this deck on MTGGoldfish
"""
def cached_deck_is_old(deck_id):
    cache_dir = os.path.join(os.path.dirname(__file__), 'deck_cache')
    if not os.path.isdir(cache_dir): return False

    cached_decks = os.listdir(cache_dir)
    for cached_deck_file_name in cached_decks:

        # The deck file names are of the format <deck_id>_MM_DD_YYYY
        cached_deck_id = cached_deck_file_name.split('_')[0]
        if cached_deck_id == deck_id:
            cached_date = datetime.strptime(cached_deck_file_name[cached_deck_file_name.find('_') + 1:], '%m_%d_%Y')
            time_delta_since_last_update = datetime.now() - cached_date
            if time_delta_since_last_update.days >= 30: return True

    return False

"""
Given a Deck object, utilize the cPickle library to save it to a local file

:param deck: The Deck object to store to the file
:param deck_id: The DeckID for the deck from MTGGoldfish.com
"""
def save_deck_to_cache(deck, deck_id):

    # If the deck_cache subdirectory hasn't been created yet, create it
    cache_dir = os.path.join(os.path.dirname(__file__), 'deck_cache')
    if not os.path.isdir(cache_dir): os.mkdir(cache_dir)

    # If an older version of the Deck is cached, delete it first
    cached_decks = os.listdir(cache_dir)
    for existing_cache_file in cached_decks:

        # The deck file names are of the format <deck_id>_MM_DD_YYYY
        cached_deck_id = existing_cache_file.split('_')[0]
        if cached_deck_id == deck_id:
            os.remove(os.path.join(cache_dir, existing_cache_file))

    # Generate the file name for this cached Deck of the format <deck_id>_MM_DD_YYYY
    todays_date = datetime.now()
    month = todays_date.month
    day = todays_date.day
    if month <= 9: month = "0%s" %(todays_date.month)
    if day <= 9: day = "0%s" %(todays_date.day)
    cache_file_name = "%s_%s_%s_%s" %(deck_id, month, day, todays_date.year)

    with open(os.path.join(cache_dir, cache_file_name), 'wb') as output:
        pickle.dump(deck, output, pickle.HIGHEST_PROTOCOL)

"""
Given a DeckID, load the deck from the cache
"""
def load_deck_from_cache(deck_id):
    deck = Deck()

    cache_dir = os.path.join(os.path.dirname(__file__), 'deck_cache')
    cached_decks = os.listdir(cache_dir)

    # Fetch the file name of the cached deck for reading
    cached_deck_file_path = ""
    for cached_file in cached_decks:
        cached_deck_id = cached_file.split('_')[0]
        if cached_deck_id == deck_id:
            cached_deck_file_path = os.path.join(cache_dir, cached_file)
            break;

    with open(cached_deck_file_path, 'rb') as input:
        deck = pickle.load(input)

    return deck

"""
Parse the owned_cards.txt file and return the cards as a list of dictionaries of card records
using CARD_QTY_KEY and CARD_NAME_KEY
"""
def parse_owned_cards():
    owned_cards = []
    script_dir = os.path.dirname(__file__)
    owned_cards_file = open(os.path.join(script_dir, 'owned_cards.txt'), 'r')
    for line in owned_cards_file:

        # Disregard comments and empty lines
        if line[0] == "#" or len(line) <= 1: continue

        separator_index = line.find(' ')
        if separator_index == -1: continue
        card_quantity = int(line[:separator_index])
        card_name = line[separator_index + 1:].replace('\n', '')

        # Double-check to make sure the user hasn't entered this card in more than once. If so, we aren't going
        # to try to resolve this for the user by making assumptions. Instead, we will point this out via a Print
        # statement for them to resolve, and kill the script
        for card_entry in owned_cards:
            if card_entry[CARD_NAME_KEY].lower() == card_name.lower():
                print "[ERROR]: \"%s\" occurs more than once in owned_cards.txt. Exiting." %(card_name)
                sys.exit(0)

        owned_cards.append({CARD_QTY_KEY: card_quantity, CARD_NAME_KEY: card_name})

    owned_cards_file.close()

    return owned_cards

"""
Parse the desired_decks.txt file and return a list of the URLs contained within
"""
def parse_desired_deck_URLs():
    desired_deck_URLs = []
    script_dir = os.path.dirname(__file__)
    desired_cards_file = open(os.path.join(script_dir, 'desired_decks.txt'))
    for line in desired_cards_file:

        # Disregard comments and empty lines
        if line[0] == "#" or len(line) <= 1: continue

        desired_deck_URLs.append(line)

    desired_cards_file.close()

    return desired_deck_URLs

"""
Given the desired deck URLs, parse all of the decks into Deck objects

:param update_cache: If set to True, we will ignore any cached versions of these decks
:param deck_URLs_list: The list of deck URLs
"""
def parse_decks_from_list_of_urls(update_cache, deck_URLs_list):
    deck_objs_list = []
    num_cached_decks = 0
    num_old_cached_decks = 0

    if update_cache:
        print "   Manual cache update requested, updating all local deck caches."

    for deck_url in deck_URLs_list:
        deck = Deck()

        # The URL format is either "https://www.mtggoldfish.com/deck/784979$paper" for a Budget deck
        # or "https://www.mtggoldfish.com/archetype/modern-grixis-death-s-shadow#paper" for a Modern Meta deck
        if "deck/" in deck_url:
            deck_id = deck_url.split('deck/')[1].split("#")[0]
        else:
            deck_id = deck_url.split('archetype/')[1].split("#")[0]

        # Check whether or not a cached version of this deck exists locally, and use that instead
        if not update_cache and is_deck_cached(deck_id):
            num_cached_decks += 1
            if cached_deck_is_old(deck_id): num_old_cached_decks += 1

            # Load the deck from the cache
            deck_objs_list.append(load_deck_from_cache(deck_id))
            continue

        driver = webdriver.Firefox()
        try:
            driver.get(deck_url)
        except:
            print "   [ERROR]: Failed to navigate to \"%s\"" %(deck_url)
            print "   Check your internet connection. Also note that sometimes MTGGoldfish.com experiences issues, try navigating to this URL yourself and see if it works. Try running the script again."
            driver.close()
            sys.exit(0)

        deck.deck_url = deck_url
        raw_deck_name_parse = driver.find_element_by_class_name("deck-view-title").get_attribute('textContent').replace('\n', '')

        # The formatting of the name field is different on the meta page vs the budget pages. On the budget pages it is followed with
        # "by <author>" while on the meta pages it is followed by "Suggest a Better Name"
        if raw_deck_name_parse.find('by ') > 0:
            deck.deck_name = raw_deck_name_parse[:raw_deck_name_parse.find('by ')].encode('ascii')
        else:
            deck.deck_name = raw_deck_name_parse[:-len("Suggest a Better Name")].encode('ascii')
        
        deck_date_as_string = driver.find_element_by_class_name("deck-view-description").get_attribute('textContent').replace('\n', '')[-len("MMM DD, YYYY"):]
        deck.deck_date = datetime.strptime(deck_date_as_string, '%b %d, %Y')

        # Iterate over all of the rows in the deck list and build the deck object
        deck_list = []
        deck_total_cost = 0.0
        rows_element = driver.find_element_by_id('tab-paper').find_element_by_class_name('deck-view-decklist').find_element_by_class_name('deck-view-decklist-inner')
        rows_element = rows_element.find_element_by_class_name("deck-view-deck-table").find_element_by_tag_name("tbody").find_elements_by_tag_name("tr")
        for row in rows_element:
            columns = row.find_elements_by_tag_name("td")

            # Disregard any of the section title rows such as "Creatures", "Planeswalkers", etc
            if len(columns) == 4:
                card_name = columns[NAME_INDEX].get_attribute('textContent').replace('\n', '')

                # We don't care about Basic Mana in any analysis.
                if card_name.lower() in ["mountain", "swamp", "plains", "island", "forest"]: continue

                card_quantity = int(columns[QTY_INDEX].get_attribute('textContent').replace('\n', ''))
                individual_card_price = float(columns[PRICE_INDEX].get_attribute('textContent').replace('\n', '')) / float(card_quantity)
                deck_total_cost += float(columns[PRICE_INDEX].get_attribute('textContent').replace('\n', ''))

                # It's possible for a card to appear in the list twice if it is present in both the main deck and the sideboard.
                # If this happens, we need to just update the Quantity and Price of the existing record
                record_already_exist = False
                for entry in deck_list:
                    if entry[CARD_NAME_KEY] == card_name:
                        record_already_exist = True
                        entry[CARD_QTY_KEY] += card_quantity
                if not record_already_exist:
                    deck_list.append({CARD_QTY_KEY: card_quantity, CARD_NAME_KEY: card_name, CARD_PRICE_KEY: individual_card_price})


        deck.deck_list = deck_list
        deck.deck_price = deck_total_cost
        deck_objs_list.append(deck)

        # Cache the deck
        save_deck_to_cache(deck, deck_id)

        driver.close()

    # Print number of cached decks used
    print "   Finished fetching deck data. %s of %s decks were fetched from the cache." %(num_cached_decks, len(deck_URLs_list))

    # Print number of stale decks and recommend updating
    if num_old_cached_decks > 0:
        print ("   [WARNING]: %s  of %s cached decks in this fetch were created more than 30 days ago."
               " Prices may have changed significantly since then."
               " You should run \"python mtggoldfish.py -u\" to update your cached decks." %(num_old_cached_decks, len(deck_URLs_list)))
    return deck_objs_list

"""
Uses the Firefox WebDriver to navigate to the Modern Metagame Decks section of MTGGoldfish.com
and parses all of the URLs for all of the Modern decks into a list.
"""
def parse_all_modern_metagame_deck_urls():
    print "   Opening a browser real quick to snapshot the URLs for all of the Modern Metagame decks on MTGGoldfish.com, as there might be new ones."
    modern_metagame_decks_url = "https://www.mtggoldfish.com/metagame/modern/full#paper"
    driver = webdriver.Firefox()
    driver.get(modern_metagame_decks_url)

    modern_deck_url_list = []
    deck_tiles = driver.find_elements_by_class_name("archetype-tile")
    for tile in deck_tiles:
        deck_info_container = tile.find_element_by_class_name("archetype-tile-description-wrapper").find_element_by_class_name("archetype-tile-description").find_element_by_class_name("deck-price-paper")
        deck_url = deck_info_container.find_element_by_tag_name('a').get_attribute("href")

        # For some reason, the #paper landing page contains URLS for the #online
        modern_deck_url_list.append(deck_url)

    driver.close()
    return modern_deck_url_list

"""
Uses the Firefox WebDriver to navigate to the Modern Budget Decks section of MTGGoldfish.com
and parses all of the URLs for all of the Budget decks into a list.
"""
def parse_all_budget_deck_list_URLs():
    print "   Opening a browser real quick to snapshot the URLs for all of the Budget decks on MTGGoldfish.com, as there might be new ones."
    budget_modern_decks_url = "https://www.mtggoldfish.com/decks/budget/modern#paper"
    driver = webdriver.Firefox()
    driver.get(budget_modern_decks_url)

    budget_deck_url_list = []
    deck_tiles = driver.find_elements_by_class_name("archetype-tile")
    for tile in deck_tiles:
        deck_info_container = tile.find_element_by_class_name("archetype-tile-description-wrapper").find_element_by_class_name("archetype-tile-description").find_element_by_class_name("deck-price-paper")
        deck_url = deck_info_container.find_element_by_tag_name('a').get_attribute("href")

        # For some reason, the #paper landing page contains URLS for the #online
        budget_deck_url_list.append(deck_url)

    driver.close()
    return budget_deck_url_list

"""
For each desired deck, we determine how many of the user's Owned Cards overlap with the deck
and aggregate all such cards into a multi-level dictionary for eventual reporting/price analysis.
The final report is of the format:
    [{'Eldrazi Tron', {'Shared Value': 2.87, 'Shared Cards': '1/72', 'Card List': [{'Card Name': 'Scalding Tarn', 'Card Quantity': '1'}, ...]}}, ...]

:param desired_decks_list: A list of Deck objects representing the decks in desired_decks.txt
:param owned_cards_list: The list of Owned Cards as parsed from owned_cards.txt
"""
def evaluate_owned_cards(desired_decks_list, owned_cards_list):
    owned_overlap_report = {}
    for desired_deck in desired_decks_list:
        owned_cards_that_overlap = []

        number_of_owned_cards_that_are_in_desired_deck = 0
        value_reduced_by_owned_cards = 0.0
        for desired_card_entry in desired_deck.get_deck_list():
            desired_card_name = desired_card_entry[CARD_NAME_KEY]

            for owned_card_entry in owned_cards_list:
                if owned_card_entry[CARD_NAME_KEY].lower() == desired_card_name.lower():
                    if desired_card_entry[CARD_QTY_KEY] >= owned_card_entry[CARD_QTY_KEY]:
                        number_of_owned_cards_that_are_in_desired_deck += owned_card_entry[CARD_QTY_KEY]
                        value_reduced_by_owned_cards += float(owned_card_entry[CARD_QTY_KEY] * desired_card_entry[CARD_PRICE_KEY])
                        owned_cards_that_overlap.append({CARD_NAME_KEY: desired_card_name, CARD_QTY_KEY: owned_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(owned_card_entry[CARD_QTY_KEY] * desired_card_entry[CARD_PRICE_KEY])})
                    else:
                        number_of_owned_cards_that_are_in_desired_deck += desired_card_entry[CARD_QTY_KEY]
                        value_reduced_by_owned_cards += float(desired_card_entry[CARD_QTY_KEY]) * desired_card_entry[CARD_PRICE_KEY]
                        owned_cards_that_overlap.append({CARD_NAME_KEY: desired_card_name, CARD_QTY_KEY: desired_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(desired_card_entry[CARD_QTY_KEY]) * desired_card_entry[CARD_PRICE_KEY]})
                    break

        # If we actually own some cards in this desired_deck, save the report. If not, we set the NO_OWNED_OVERLAP_FLAG so that our final report printing can know
        owned_overlap_report[desired_deck.get_deck_name()] = {}
        if value_reduced_by_owned_cards > 0:
            owned_overlap_report[desired_deck.get_deck_name()] = {OWNED_CARDS_KEY: "%d/%d" %(number_of_owned_cards_that_are_in_desired_deck, desired_deck.get_deck_size()), SAVED_VALUE_KEY: value_reduced_by_owned_cards, CARD_LIST_KEY: owned_cards_that_overlap}
        else:
            owned_overlap_report[desired_deck.get_deck_name()] = {SAVED_VALUE_KEY: NO_OWNED_OVERLAP_FLAG}
    return owned_overlap_report

"""
For each modern metagame deck, we determine how much monetary overlap we currently possess for it,
and return back a sorted list of the Modern decks, together with which cards and what value we overlap

:param modern_metagame_decks: A list of Deck objects representing all of the Modern Metagame decks on MTGGoldfish.com
:param owned_cards: A list of dicts containing card info of the format: {CARD_QTY_KEY: card_quantity, CARD_NAME_KEY: card_name}
"""
def evaluate_modern_metagame_decks(modern_metagame_decks, owned_cards):
    modern_metagame_deck_recommendation_report = {}
    for modern_meta_deck in modern_metagame_decks:
        specific_cards_owned_in_meta_deck = []
        number_of_owned_cards_that_are_in_modern_meta_deck = 0
        value_of_meta_deck_owned = 0.0

        for owned_card_entry in owned_cards:
            owned_card_name = owned_card_entry[CARD_NAME_KEY]

            # Check for this card's presence in the modern_meta_deck
            for modern_meta_card_entry in modern_meta_deck.get_deck_list():
                if modern_meta_card_entry[CARD_NAME_KEY].lower() == owned_card_name.lower():
                    if owned_card_entry[CARD_QTY_KEY] >= modern_meta_card_entry[CARD_QTY_KEY]:
                        number_of_owned_cards_that_are_in_modern_meta_deck += modern_meta_card_entry[CARD_QTY_KEY]
                        value_of_meta_deck_owned += float(modern_meta_card_entry[CARD_QTY_KEY]) * modern_meta_card_entry[CARD_PRICE_KEY]
                        specific_cards_owned_in_meta_deck.append({CARD_NAME_KEY: owned_card_name, CARD_QTY_KEY: modern_meta_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(modern_meta_card_entry[CARD_QTY_KEY]) * modern_meta_card_entry[CARD_PRICE_KEY]})
                    else:
                        number_of_owned_cards_that_are_in_modern_meta_deck += owned_card_entry[CARD_QTY_KEY]
                        value_of_meta_deck_owned += float(owned_card_entry[CARD_QTY_KEY]) * modern_meta_card_entry[CARD_PRICE_KEY]
                        specific_cards_owned_in_meta_deck.append({CARD_NAME_KEY: owned_card_name, CARD_QTY_KEY: owned_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(owned_card_entry[CARD_QTY_KEY]) * modern_meta_card_entry[CARD_PRICE_KEY]})
                    break

        # Only save the report if we actually own some cards in this Modern Metagame deck
        if value_of_meta_deck_owned > 0:
            modern_metagame_deck_recommendation_report[modern_meta_deck.get_deck_name()] = {}
            modern_metagame_deck_recommendation_report[modern_meta_deck.get_deck_name()] = {OWNED_CARDS_KEY: "%d/%d" %(number_of_owned_cards_that_are_in_modern_meta_deck, modern_meta_deck.get_deck_size()), SAVED_VALUE_KEY: value_of_meta_deck_owned, CARD_LIST_KEY: specific_cards_owned_in_meta_deck, DECK_PRICE_KEY: modern_meta_deck.get_deck_price()}

    # Sort entries by value descending
    modern_metagame_decks_sorted_by_desc_value_saved_as_list = sorted(modern_metagame_deck_recommendation_report.iteritems(), key=lambda (k, v): v[SAVED_VALUE_KEY], reverse=True)

    # Return only the top 15
    if len(modern_metagame_decks_sorted_by_desc_value_saved_as_list) > 15:
        return modern_metagame_decks_sorted_by_desc_value_saved_as_list[:15]
    else:
        return modern_metagame_decks_sorted_by_desc_value_saved_as_list 

"""
For each desired deck, we process each budget deck to determine how many cards from each budget deck
are present in the given desired deck. We then store them into a large multi-level dictionary for
eventual reporting
"""
def evaluate_budget_decks(owned_cards, desired_decks_list, budget_decks_list):
    budget_report = {}
    for desired_deck in desired_decks_list:
        budget_report[desired_deck.get_deck_name()] = {}

        for budget_deck in budget_decks_list:
            number_of_cards_from_budget_deck_that_are_in_desired_deck = 0
            value_shared_between_decks = 0.0
            number_of_owned_cards_that_are_in_budget_deck = 0
            value_of_budget_deck_owned = 0.0
            specific_owned_cards_in_budget_deck = []

            # This is literally N^3 and I should be ashamed, but with data sets this small it doesn't matter in the slightest
            for desired_card_entry in desired_deck.get_deck_list():
                desired_card_name = desired_card_entry[CARD_NAME_KEY]

                # Check for this card's presence in the first budget deck
                for budget_card_entry in budget_deck.get_deck_list():

                    # Check to see if we own this card for our Owned Cards mini-report
                    for owned_card_entry in owned_cards:
                        owned_card_name = owned_card_entry[CARD_NAME_KEY]
                        if budget_card_entry[CARD_NAME_KEY].lower() == owned_card_name.lower():
                            if owned_card_entry[CARD_QTY_KEY] >= budget_card_entry[CARD_QTY_KEY]:
                                
                                # Only process this card if it doesn't already exist in the specific_owned_cards_in_budget_deck list
                                already_exists = False
                                for card_record in specific_owned_cards_in_budget_deck:
                                    if card_record[CARD_NAME_KEY] == owned_card_name:
                                        already_exists = True
                                        break
                                if not already_exists:
                                    number_of_owned_cards_that_are_in_budget_deck += budget_card_entry[CARD_QTY_KEY]
                                    value_of_budget_deck_owned += float(budget_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                                    specific_owned_cards_in_budget_deck.append({CARD_NAME_KEY: owned_card_name, CARD_QTY_KEY: budget_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(budget_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]})

                            else:

                                # Only add this card if it doesn't already exist in the specific_owned_cards_in_budget_deck list
                                already_exists = False
                                for card_record in specific_owned_cards_in_budget_deck:
                                    if card_record[CARD_NAME_KEY] == owned_card_name:
                                        already_exists = True
                                        break
                                if not already_exists:
                                    number_of_owned_cards_that_are_in_budget_deck += owned_card_entry[CARD_QTY_KEY]
                                    value_of_budget_deck_owned += float(owned_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                                    specific_owned_cards_in_budget_deck.append({CARD_NAME_KEY: owned_card_name, CARD_QTY_KEY: owned_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(owned_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]})

                    if budget_card_entry[CARD_NAME_KEY].lower() == desired_card_name.lower():
                        if desired_card_entry[CARD_QTY_KEY] >= budget_card_entry[CARD_QTY_KEY]:
                            number_of_cards_from_budget_deck_that_are_in_desired_deck += budget_card_entry[CARD_QTY_KEY]
                            value_shared_between_decks += float(budget_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                        else:
                            number_of_cards_from_budget_deck_that_are_in_desired_deck += desired_card_entry[CARD_QTY_KEY]
                            value_shared_between_decks += float(desired_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                        break

            # Only bother reporting budget decks that actually overlap
            if value_shared_between_decks > 0:
                budget_report[desired_deck.get_deck_name()][budget_deck.get_deck_name()] = {DECK_PRICE_KEY: budget_deck.get_deck_price(), SHARED_CARDS_KEY: "%d/%d" %(number_of_cards_from_budget_deck_that_are_in_desired_deck, budget_deck.get_deck_size()), SHARED_VALUE_KEY: value_shared_between_decks, OWNED_CARDS_KEY: "%d/%d" %(number_of_owned_cards_that_are_in_budget_deck, budget_deck.get_deck_size()), SAVED_VALUE_KEY: value_of_budget_deck_owned, CARD_LIST_KEY: specific_owned_cards_in_budget_deck}

        # Sort entries by value for this particular desired_deck now that all of the budget decks have been processed
        budget_decks_sorted_by_desc_value_as_list = sorted(budget_report[desired_deck.get_deck_name()].iteritems(), key=lambda (k,v): v[SHARED_VALUE_KEY], reverse=True)

        # Only keep the top 5 for each
        budget_report[desired_deck.get_deck_name()] = budget_decks_sorted_by_desc_value_as_list[:5]

    return budget_report

"""
Give a final evaluation report displaying how the cards that you own line up in the Modern Metagame
decks you specified desired_decks.txt
"""
def print_owned_cards_evaluation_report(report_output_file_name, desired_decks_list, owned_cards_overlap_report):

    # This is super nasty, but whatever. We print to the file if we're actually given a file to print to. Otherwise we print to the terminal
    if report_output_file_name != "":
        with open(report_output_file_name, 'a') as output_file:
            output_file.write("\n\n=== Owned Card report for Desired Decks listed in desired_decks.txt ===")
            for desired_deck_name_key in owned_cards_overlap_report:

                # This is a super clumsy way to fetch the price of the original deck
                desired_deck_total_cost = 0.0
                for desired_deck_obj in desired_decks_list:
                    if desired_deck_obj.get_deck_name().lower() == desired_deck_name_key.lower():
                        desired_deck_total_cost = desired_deck_obj.get_deck_price()
                        output_file.write("\n   Owned cards that are used in \"%s\" ($%.2f):" %(desired_deck_name_key, desired_deck_total_cost))

                # The owned_cards_overlap_report is of the format:
                # {'Saved Value': 265.96, 'Card List': [{'Card Name': u'Scalding Tarn', 'Card Quantity': 4}], 'Owned Cards': '4/73'}
                specific_owned_cards_report = owned_cards_overlap_report[desired_deck_name_key]
                if specific_owned_cards_report[SAVED_VALUE_KEY] == NO_OWNED_OVERLAP_FLAG:
                    output_file.write("\n      None of the cards you own overlap with this deck :(")
                else:
                    output_file.write("\n      Number of cards owned: %s" %(specific_owned_cards_report[OWNED_CARDS_KEY]))
                    output_file.write("\n      Value saved: $%.2f" %(specific_owned_cards_report[SAVED_VALUE_KEY]))
                    output_file.write("\n      Remaining cost: $%.2f" %(desired_deck_total_cost - specific_owned_cards_report[SAVED_VALUE_KEY]))
                    output_file.write("\n      List of specific cards:")
                    for card_entry in specific_owned_cards_report[CARD_LIST_KEY]:
                        output_file.write("\n         %sx %s ($%.2f)" %(card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))

    else:
        print "\n=== Owned Card report for Desired Decks listed in desired_decks.txt ==="
        for desired_deck_name_key in owned_cards_overlap_report:

            # This is a super clumsy way to fetch the price of the original deck
            desired_deck_total_cost = 0.0
            for desired_deck_obj in desired_decks_list:
                if desired_deck_obj.get_deck_name().lower() == desired_deck_name_key.lower():
                    desired_deck_total_cost = desired_deck_obj.get_deck_price()
                    print "   Owned cards that are used in \"%s\" ($%.2f):" %(desired_deck_name_key, desired_deck_total_cost)

            # The owned_cards_overlap_report is of the format:
            # {'Saved Value': 265.96, 'Card List': [{'Card Name': u'Scalding Tarn', 'Card Quantity': 4}], 'Owned Cards': '4/73'}
            specific_owned_cards_report = owned_cards_overlap_report[desired_deck_name_key]
            if specific_owned_cards_report[SAVED_VALUE_KEY] == NO_OWNED_OVERLAP_FLAG:
                print "      None of the cards you own overlap with this deck :("
            else:
                print "      Number of cards owned: %s" %(specific_owned_cards_report[OWNED_CARDS_KEY])
                print "      Value saved: $%.2f" %(specific_owned_cards_report[SAVED_VALUE_KEY])
                print "      Remaining cost: $%.2f" %(desired_deck_total_cost - specific_owned_cards_report[SAVED_VALUE_KEY])
                print "      List of specific cards:"
                for card_entry in specific_owned_cards_report[CARD_LIST_KEY]:
                    print "         %sx %s ($%.2f)" %(card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY])

"""
Print a final report of the Modern Metagame decks that you have share the most value with

:param modern_metagame_deck_recommendation_report: A list of tuples containing (<deck_name>, <report_summary_for_this_deck>) pairs,
                                                   sorted descending based on the 'Saved Value' key in the <Report_summary_for_this_deck>
"""
def print_modern_metagame_deck_recommendation_report(report_output_file_name, modern_metagame_deck_recommendation_report):

    # This is super nasty, but whatever. We print to the file if we're actually given a file to print to. Otherwise we print to the terminal
    if report_output_file_name != "":
        with open(report_output_file_name, 'a') as output_file:
            output_file.write("\n\n=== Modern Metagame deck recommendation report based on Cards listed in owned_cards.txt ===")

            # The sort method turns the dictionary into a list of a tuple like this: [('Affinity', {'Saved Value': 62.87, 'Owned Cards': '3/72', 'Deck Price': 1032.95, 'Specific Cards': [{}]}), ...]
            for deck_summary_entry in modern_metagame_deck_recommendation_report:
                output_file.write("\n\n   #%s Closest Match:" %(modern_metagame_deck_recommendation_report.index(deck_summary_entry) + 1))
                output_file.write("\n      Modern Meta Deck: \"%s\" ($%.2f)" %(deck_summary_entry[0], deck_summary_entry[1][DECK_PRICE_KEY]))
                output_file.write("\n      Number of cards owned: %s" %(deck_summary_entry[1][OWNED_CARDS_KEY]))
                output_file.write("\n      Value of cards owned: $%.2f" %(deck_summary_entry[1][SAVED_VALUE_KEY]))
                output_file.write("\n      Remaining cost: $%.2f" %(deck_summary_entry[1][DECK_PRICE_KEY] - deck_summary_entry[1][SAVED_VALUE_KEY]))
                output_file.write("\n      List of specific cards:")
                for card_entry in deck_summary_entry[1][CARD_LIST_KEY]:
                    output_file.write("\n         %sx %s ($%.2f)" %(card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
    else:
        print "\n=== Modern Metagame deck recommendation report based on Cards listed in owned_cards.txt ==="

        # The sort method turns the dictionary into a list of a tuple like this: [('Affinity', {'Saved Value': 62.87, 'Owned Cards': '3/72', 'Deck Price': 1032.95, 'Specific Cards': [{}]}), ...]
        for deck_summary_entry in modern_metagame_deck_recommendation_report:
            print "\n   #%s Closest Match:" %(modern_metagame_deck_recommendation_report.index(deck_summary_entry) + 1)
            print "      Modern Meta Deck: \"%s\" ($%.2f)" %(deck_summary_entry[0], deck_summary_entry[1][DECK_PRICE_KEY])
            print "      Number of cards owned: %s" %(deck_summary_entry[1][OWNED_CARDS_KEY])
            print "      Value of cards owned: $%.2f" %(deck_summary_entry[1][SAVED_VALUE_KEY])
            print "      Remaining cost: $%.2f" %(deck_summary_entry[1][DECK_PRICE_KEY] - deck_summary_entry[1][SAVED_VALUE_KEY])
            print "      List of specific cards:"
            for card_entry in deck_summary_entry[1][CARD_LIST_KEY]:
                print "         %sx %s ($%.2f)" %(card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY])

"""
Give a final evaluation report for the Budget decks by iterating
over each entry and printing it out to the terminal in a clear way
"""
def print_budget_evaluation_report(report_output_file_name, desired_decks_list, budget_deck_report):

    # This is super nasty, but whatever. We print to the file if we're actually given a file to print to. Otherwise we print to the terminal
    if report_output_file_name != "":
        with open(report_output_file_name, 'a') as output_file:
            output_file.write("\n\n=== Budget Deck report comparing against Desired Decks listed in desired_decks.txt ===")
            for desired_deck_name_key in budget_deck_report:

                # This is a super clumsy way to fetch the price of the original deck
                for desired_deck_obj in desired_decks_list:
                    if desired_deck_obj.get_deck_name().lower() == desired_deck_name_key.lower():
                        output_file.write("\n   Budget Decks that compare to Desired Deck: \"%s\" ($%.2f):" %(desired_deck_name_key, desired_deck_obj.get_deck_price()))

                # The sort method turns the dictionary into a list of a tuple like this: [('Rogues', {'Shared Value': 2.87, 'Shared Cards': '1/72', 'Deck Price': 32.95}), ...]
                for budget_deck_list_record in budget_deck_report[desired_deck_name_key]:
                    output_file.write("\n\n      #%s Closest Match:" %(budget_deck_report[desired_deck_name_key].index(budget_deck_list_record) + 1))
                    output_file.write("\n         Budget Deck Name: %s" %(budget_deck_list_record[0]))
                    output_file.write("\n         Budget Deck cost: $%s" %(budget_deck_list_record[1][DECK_PRICE_KEY]))
                    output_file.write("\n         Number of cards shared: %s" %(budget_deck_list_record[1][SHARED_CARDS_KEY]))
                    output_file.write("\n         Value shared: $%.2f" %(budget_deck_list_record[1][SHARED_VALUE_KEY]))
                    output_file.write("\n         Owned Cards Report:")
                    if budget_deck_list_record[1][SAVED_VALUE_KEY] != 0:
                        output_file.write("\n            Number of cards owned: %s" %(budget_deck_list_record[1][OWNED_CARDS_KEY]))
                        output_file.write("\n            Value of cards owned: $%.2f" %(budget_deck_list_record[1][SAVED_VALUE_KEY]))
                        output_file.write("\n            Remaining cost: $%.2f" %(budget_deck_list_record[1][DECK_PRICE_KEY] - budget_deck_list_record[1][SAVED_VALUE_KEY]))
                        output_file.write("\n            List of specific cards:")
                        for card_entry in budget_deck_list_record[1][CARD_LIST_KEY]:
                            output_file.write("\n               %sx %s ($%.2f)" %(card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
                    else:
                        output_file.write("\n               None of the cards listed in owned_cards.txt are used in this deck :(")

    else:
        print "\n=== Budget Deck report comparing against Desired Decks listed in desired_decks.txt ==="
        for desired_deck_name_key in budget_deck_report:

            # This is a super clumsy way to fetch the price of the original deck
            for desired_deck_obj in desired_decks_list:
                if desired_deck_obj.get_deck_name().lower() == desired_deck_name_key.lower():
                    print "   Budget Decks that compare to Desired Deck: \"%s\" ($%.2f):" %(desired_deck_name_key, desired_deck_obj.get_deck_price())

            # The sort method turns the dictionary into a list of a tuple like this: [('Rogues', {'Shared Value': 2.87, 'Shared Cards': '1/72', 'Deck Price': 32.95}), ...]
            for budget_deck_list_record in budget_deck_report[desired_deck_name_key]:
                print "\n      #%s Closest Match:" %(budget_deck_report[desired_deck_name_key].index(budget_deck_list_record) + 1)
                print "         Budget Deck Name: %s" %(budget_deck_list_record[0])
                print "         Budget Deck cost: $%s" %(budget_deck_list_record[1][DECK_PRICE_KEY])
                print "         Number of cards shared: %s" %(budget_deck_list_record[1][SHARED_CARDS_KEY])
                print "         Value shared: $%.2f" %(budget_deck_list_record[1][SHARED_VALUE_KEY])
                print "         Owned Cards Report:"
                if budget_deck_list_record[1][SAVED_VALUE_KEY] != 0:
                    print "            Number of cards owned: %s" %(budget_deck_list_record[1][OWNED_CARDS_KEY])
                    print "            Value of cards owned: $%.2f" %(budget_deck_list_record[1][SAVED_VALUE_KEY])
                    print "            Remaining cost: $%.2f" %(budget_deck_list_record[1][DECK_PRICE_KEY] - budget_deck_list_record[1][SAVED_VALUE_KEY])
                    print "            List of specific cards:"
                    for card_entry in budget_deck_list_record[1][CARD_LIST_KEY]:
                        print "               %sx %s ($%.2f)" %(card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY])
                else:
                    print "               None of the cards listed in owned_cards.txt are used in this deck :("

if __name__ == "__main__":
    print ""
    print "====================================================="
    print "================ Beginning Fresh Run ================"
    print "====================================================="

    # Since parsing Budget decks takes FOREVER, we only do it if the user specifies the -b flag
    parser = OptionParser(description=("This script parses decks you'd like to build into from MTGGoldfish.com listed in desired_decks.txt"
                                       " as well as any cards listed in owned_cards.txt to tell you how far along you already are to constructing"
                                       " those decks with the cards you already own. Additionally, this script can parse all of Modern budget decks"
                                       " listed on MTGGoldfish.com by specifying the \"-b\" flag, which will generate a report telling you the top 5"
                                       " Budget decks that overlap the most with each of your desired decks, sorted descending by monetary overlap, NOT sheer card quantity"))
    parser.add_option("-b", "--budget", dest="parse_budget", help="Parse all Modern Budget decks from MTGGoldfish that aren't currently cached and then run an analysis as described in the README. This can take 10 minutes or more for the first run. Decks parsed this way get cached for future analysis, so that browser fetches aren't required, unless explicitly commanded to via the \"-u\" flag", action='store_const', const=True)
    parser.add_option("-r", "--recommend", dest="recommend_meta_decks", help="Parse all Modern Metagame decks from MTGGoldfish that aren't currently cached and then run an analysis as described in the README. This can take 10 minutes or more for the first run. Decks parsed this way get cached for future analysis, so that browser fetches aren't required, unless explicitly commanded to via the \"-u\" flag", action='store_const', const=True)
    parser.add_option("-u", "--update", dest="update_cache", help="Fetches fresh data for all decks specified in desired_decks.txt as well as all Modern Budget decks listed on MTGGoldfish.com. Analysis will also be provided at the end of the run. This can take 10 minutes or more", action='store_const', const=True)
    parser.add_option("-f", "--file", dest="print_to_file", help="Informs the script to print all reports to a .txt file. The file name will be of the format: deck_report_MM_DD_YYYY.txt", action='store_const', const=True)
    (options, args) = parser.parse_args()
    
    owned_cards = parse_owned_cards()
    desired_deck_URLs = parse_desired_deck_URLs()

    start_time = time.time()
    print "\nFetching Deck information for decks listed in desired_decks.txt."
    desired_decks = parse_decks_from_list_of_urls(options.update_cache, desired_deck_URLs)

    # If the User hasn't specified any cards in owned_cards.txt, then the only other reason to run this script at all is
    # to generate a report on the Budget Decks from MTGGoldfish.com. So that's what we will do.
    no_owned_cards_in_list = len(owned_cards) == 1 and owned_cards[0][CARD_NAME_KEY] == "name of card that doesn't exist"
    should_run_budget_analysis = options.parse_budget == True or no_owned_cards_in_list
    if should_run_budget_analysis and len(desired_decks) == 0:
        print "\n[ERROR] Budget Analysis implied but there are no decks listed in desired_decks.txt. Exiting"
        sys.exit(0)

    # Perform Modern Metagame Recommendation Analysis if desired
    modern_metagame_decks = []
    if options.recommend_meta_decks:

        # We can't recommend meta decks if the User supplied no cards
        if no_owned_cards_in_list:
            print "\n[ERROR]: Recommend flag set, but no cards provided in owned_cards.txt. Skipping"
        else:
            print "\nRecommend flag set. Fetching Deck information of all Modern Metagame decks for Recommendation analysis..."
            modern_metagame_urls_list = parse_all_modern_metagame_deck_urls()
            modern_metagame_decks = parse_decks_from_list_of_urls(options.update_cache, modern_metagame_urls_list)

    # Perform Budget Analysis if desired
    budget_decks = []
    if should_run_budget_analysis:
        status_msg = ""
        if options.parse_budget == True:
            status_msg = "\nBudget flag set. "
        else:
            status_msg = "\nowned_cards.txt was empty. "
        print status_msg + "Fetching Deck information of all Modern Budget decks for budget analysis..."
        budget_decks_url_list = parse_all_budget_deck_list_URLs()
        budget_decks = parse_decks_from_list_of_urls(options.update_cache, budget_decks_url_list)

    print "\nDone fetching all Deck information. Fetch took %.2f seconds" %(time.time() - start_time)

    if not no_owned_cards_in_list and len(desired_decks) == 0:
        print "\nComputing Owned Cards evaluations..."
        owned_cards_overlap_report = evaluate_owned_cards(desired_decks, owned_cards)

    # We can't recommend meta decks if the User supplied no cards
    if options.recommend_meta_decks and not no_owned_cards_in_list:
        print "\nComputing Modern Metagame Deck Recommendation evaluations..."
        modern_metagame_deck_recommendation_report = evaluate_modern_metagame_decks(modern_metagame_decks, owned_cards)

    if should_run_budget_analysis:
        print "\nComputing Budget Deck List evaluations..."
        budget_deck_report = evaluate_budget_decks(owned_cards, desired_decks, budget_decks)

    report_output_file_name = ""
    if options.print_to_file:

        # Generate an output file with today's date, and open it for appending
        todays_date = datetime.now()
        month = todays_date.month
        day = todays_date.day
        if month <= 9: month = "0%s" %(todays_date.month)
        if day <= 9: day = "0%s" %(todays_date.day)
        report_file_name = "deck_report_%s_%s_%s.txt" %(month, day, todays_date.year)

        script_dir = os.path.dirname(__file__)

        # If we've already generated a report today, we don't want to continue appending to that existing report, so we remove it
        if os.path.isfile(os.path.join(script_dir, report_file_name)): os.remove(os.path.join(script_dir, report_file_name))
        report_output_file_name = os.path.join(script_dir, report_file_name)

        print "Generating report..."
    else:
        print ""
        print "============================================"
        print "================ Report(s) ================="
        print "============================================"

    if not no_owned_cards_in_list and len(desired_decks) == 0:
        print_owned_cards_evaluation_report(report_output_file_name, desired_decks, owned_cards_overlap_report)

    if options.recommend_meta_decks and not no_owned_cards_in_list:
        print_modern_metagame_deck_recommendation_report(report_output_file_name, modern_metagame_deck_recommendation_report)

    if should_run_budget_analysis:
        print_budget_evaluation_report(report_output_file_name, desired_decks, budget_deck_report)

    if options.print_to_file:
        todays_date = datetime.now()
        month = todays_date.month
        day = todays_date.day
        if month <= 9: month = "0%s" %(todays_date.month)
        if day <= 9: day = "0%s" %(todays_date.day)
        print "Report has been printed to file: \"deck_report_%s_%s_%s.txt\"" %(month, day, todays_date.year)

    sys.exit(0)