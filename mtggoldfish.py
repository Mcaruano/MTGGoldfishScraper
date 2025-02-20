# -*- coding: utf-8 -*-
"""
View README.md for usage: https://github.com/Mcaruano/MTGGoldfishScraper/blob/master/README.md
"""

from __future__ import print_function
import six
from six.moves import cPickle as pickle
from datetime import datetime
import errno
from optparse import OptionParser
import os
from progress.bar import IncrementalBar
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
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
        self.deck_date = datetime(1970, 1, 1)
        self.deck_price = 0.0
        self.deck_list = []

    def get_deck_name(self):
        if six.PY2:
            return self.deck_name.encode('ascii')
        else:
            return self.deck_name

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
        print_output = "Deck Name: %s\nDeck URL: %s\nDeck Date: %s\nDeck Price: %.2f\nDeck List:\n{\n" % (
            self.deck_name, self.deck_url, self.deck_date, self.deck_price)
        for card_entry in self.deck_list:
            print_output = print_output + \
                "     %dx %s,\n" % (
                    card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY])
        return print_output + "}"


"""
Checks all local cache dirs for the presence of this deck using the MTGGoldfish DeckID, as
parsed from the Deck URL.

:param deck_id: The DeckID of this deck on MTGGoldfish
"""
def is_deck_cached(deck_id):
    cache_dir = os.path.join(os.path.dirname(__file__), 'deck_cache')
    if not os.path.isdir(cache_dir):
        return False

    cached_decks = os.listdir(cache_dir)
    for cached_deck_file_name in cached_decks:

        # The deck file names are of the format <deck_id>_MM_DD_YYYY
        cached_deck_id = cached_deck_file_name.split('_')[0]
        if cached_deck_id == deck_id:
            return True

    return False


"""
Given a DeckID, parses the MM_DD_YYYY portion of a cached deck file name
and returns true if the date is >= 30 days old

:param deck_id: The DeckID of this deck on MTGGoldfish
"""
def cached_deck_is_old(deck_id):
    cache_dir = os.path.join(os.path.dirname(__file__), 'deck_cache')
    if not os.path.isdir(cache_dir):
        return False

    cached_decks = os.listdir(cache_dir)
    for cached_deck_file_name in cached_decks:

        # The deck file names are of the format <deck_id>_MM_DD_YYYY
        cached_deck_id = cached_deck_file_name.split('_')[0]
        if cached_deck_id == deck_id:
            cached_date = datetime.strptime(
                cached_deck_file_name[cached_deck_file_name.find('_') + 1:], '%m_%d_%Y')
            time_delta_since_last_update = datetime.now() - cached_date
            if time_delta_since_last_update.days >= 30:
                return True

    return False


"""
Given a Deck object, utilize the cPickle library to save it to a local file

:param deck: The Deck object to store to the file
:param deck_id: The DeckID for the deck from MTGGoldfish.com
"""
def save_deck_to_cache(deck, deck_id):

    # If the deck_cache subdirectory hasn't been created yet, create it
    cache_dir = os.path.join(os.path.dirname(__file__), 'deck_cache')
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)

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
    if month <= 9:
        month = "0%s" % (todays_date.month)
    if day <= 9:
        day = "0%s" % (todays_date.day)
    cache_file_name = "%s_%s_%s_%s" % (deck_id, month, day, todays_date.year)

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
            break

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
        if line[0] == "#" or len(line) <= 1:
            continue

        separator_index = line.find(' ')
        if separator_index == -1:
            continue
        card_quantity = int(line[:separator_index])
        card_name = line[separator_index + 1:].replace('\n', '')

        # Double-check to make sure the user hasn't entered this card in more than once. If so, we aren't going
        # to try to resolve this for the user by making assumptions. Instead, we will point this out via a Print
        # statement for them to resolve, and kill the script
        for card_entry in owned_cards:
            if card_entry[CARD_NAME_KEY].lower() == card_name.lower():
                print("[ERROR]: \"%s\" occurs more than once in owned_cards.txt. Exiting." % (
                    card_name))
                sys.exit(0)

        owned_cards.append(
            {CARD_QTY_KEY: card_quantity, CARD_NAME_KEY: card_name})

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
        if line[0] == "#" or len(line) <= 1:
            continue

        desired_deck_URLs.append(line)

    desired_cards_file.close()

    return desired_deck_URLs


"""
Given the desired deck URLs, parse all of the decks into Deck objects

:param update_cache: If set to True, we will ignore any cached versions of these decks
:param deck_URLs_list: The list of deck URLs
"""
def parse_decks_from_list_of_urls(update_cache, deck_URLs_list, use_online_price):
    progress_bar = IncrementalBar("   Fetching Deck Data", max=len(deck_URLs_list), suffix='%(percent)d%%')
    deck_objs_list = []
    num_cached_decks = 0
    num_old_cached_decks = 0

    if update_cache:
        print("   Manual cache update requested, updating all local deck caches.")

    for deck_url in deck_URLs_list:
        deck = Deck()

        # The URL format is either "https://www.mtggoldfish.com/deck/784979#paper" for a Budget deck
        # or "https://www.mtggoldfish.com/archetype/modern-grixis-death-s-shadow#paper" for a Modern Meta deck
        # So we fetch the Deck ID from the last '/' to the '#'
        deck_id = deck_url[deck_url.rfind('/') + 1:].split("#")[0]

        # Check whether or not a cached version of this deck exists locally, and use that instead
        if not update_cache and is_deck_cached(deck_id):
            num_cached_decks += 1
            if cached_deck_is_old(deck_id):
                num_old_cached_decks += 1

            # Load the deck from the cache
            deck_objs_list.append(load_deck_from_cache(deck_id))

            progress_bar.next()
            continue

        driver = webdriver.Firefox()
        try:
            driver.get(deck_url)
        except:
            print("   [ERROR]: Failed to navigate to \"%s\"" % (deck_url))
            print("   Check your internet connection. Also note that sometimes MTGGoldfish.com experiences issues, try navigating to this URL yourself and see if it works. Try running the script again.")
            driver.close()
            sys.exit(0)

        deck.deck_url = deck_url
        # find_element_by_class_name method has been deprecated. Replaced with newer Selenium method.
        raw_deck_name_parse = driver.find_element(By.CLASS_NAME,
            "title").get_attribute('textContent').replace('\n', '')

        # The formatting of the name field is different on the meta page vs the budget pages. On the budget pages it is followed with
        # "by <author>" while on the meta pages it is followed by "Suggest a Better Name"
        if raw_deck_name_parse.find('by ') > 0:
            deck.deck_name = raw_deck_name_parse[:raw_deck_name_parse.find(
                'by ')].encode('ascii')
        else:
            deck.deck_name = raw_deck_name_parse[:-
                                                 len("Suggest a Better Name")].encode('ascii')

        # Changed _by_class_name to new (By.CLASS_NAME, to reflect updated Selenium method.
        deck_date_as_string = driver.find_element(By.CLASS_NAME, 
            "deck-container-information").get_attribute('textContent').replace('\n', '')[-len("MMM DD, YYYY"):]
        # The website uses "9" instead of "09" for date, we need to strip whitespace before parsing the date.   
        deck_date_as_string = deck_date_as_string.strip()
        deck.deck_date = datetime.strptime(deck_date_as_string, '%b %d, %Y')

        # Iterate over all of the rows in the deck list and build the deck object
        deck_list = []
        deck_total_cost = 0.0
        price_tab_element_tag = 'tab-paper'
        if use_online_price:
            price_tab_element_tag = 'tab-online'
        # Same Selenium method to update the "(By.CLASS_NAME," also applies to "(By,TAG_NAME,".
        # The website appears to have undergone changes to its structure. I've updated
            # all the CLASS_NAMES and TAG_NAMES to be able to locate and scrape the desired data.
        rows_element = driver.find_element(By.CLASS_NAME, "deck-table-container")
        table_body = rows_element.find_element(By.TAG_NAME, "tbody")
        rows = table_body.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            columns = row.find_elements(By.TAG_NAME, "td")

            # Disregard any of the section title rows such as "Creatures", "Planeswalkers", etc
            if len(columns) == 4:
                card_name = columns[NAME_INDEX].get_attribute(
                    'textContent').replace('\n', '')

                # We don't care about Basic Mana in any analysis.
                if card_name.lower() in ["mountain", "swamp", "plains", "island", "forest"]:
                    continue

                card_quantity_string = columns[QTY_INDEX].get_attribute(
                    'textContent').replace('\n', '')
                card_price_string = columns[PRICE_INDEX].get_attribute(
                    'textContent').replace('\n', '')
                
                if card_quantity_string == '':
                    card_quantity_string = '1'
                if card_price_string == '':
                    card_price_string = '0'
                # The price kept returning "\xa0" (Fun Fact: \xa0 is unicode for a non-breaking space) 
                # To fix, I cleaned the string to be able to return a float.
                else:
                    card_price_string = card_price_string.replace('\xa0', '').replace('$', '')

                card_quantity = int(card_quantity_string)
                individual_card_price = float(
                    card_price_string.replace(',', '')) / float(card_quantity)
                deck_total_cost += float(card_price_string.replace(',', ''))

                # It's possible for a card to appear in the list twice if it is present in both the main deck and the sideboard.
                # If this happens, we need to just update the Quantity and Price of the existing record
                record_already_exist = False
                for entry in deck_list:
                    if entry[CARD_NAME_KEY] == card_name:
                        record_already_exist = True
                        entry[CARD_QTY_KEY] += card_quantity
                if not record_already_exist:
                    deck_list.append(
                        {CARD_QTY_KEY: card_quantity, CARD_NAME_KEY: card_name, CARD_PRICE_KEY: individual_card_price})

        deck.deck_list = deck_list
        deck.deck_price = deck_total_cost
        deck_objs_list.append(deck)

        # Cache the deck
        save_deck_to_cache(deck, deck_id)

        driver.close()

        progress_bar.next()

    progress_bar.finish()

    # Print number of cached decks used
    print("   Finished fetching deck data. %s of %s decks were fetched from the cache." % (
        num_cached_decks, len(deck_URLs_list)))

    # Print number of stale decks and recommend updating
    if num_old_cached_decks > 0:
        print("   [WARNING]: %s  of %s cached decks in this fetch were created more than 30 days ago."
              " Prices may have changed significantly since then."
              " You should run \"python mtggoldfish.py -u\" to update your cached decks." % (num_old_cached_decks, len(deck_URLs_list)))
    return deck_objs_list


"""
Given the URL for a category landing page on MTGGoldfish.com (such as "https://www.mtggoldfish.com/decks/budget/modern#paper"),
parse all of the URLs for the various decks on that page. It uses the #paper or #online queryparam to determine which URL to load
for each deck

:param category_landing_page_url: The URL of the category landing page that contains a list of various decks
"""
def parse_deck_urls_from_category_landing_page(category_landing_page_url):
    print("   Opening a browser real quick to snapshot deck URLs from MTGGoldfish.com, as there might be new decks that we need to fetch data for.")
    driver = webdriver.Firefox()
    driver.get(category_landing_page_url)

    # I didn't change the element names for either paper, online, or budget decks. 
    # However, it appears that functionality didn't break here, even with the old class names and tags.
    deck_URL_container_element_tag = "deck-price-paper"
    if "#online" in category_landing_page_url.lower():
        deck_URL_container_element_tag = "deck-price-online"

    budget_deck_url_list = []
    try:
        # Update Selenenium method from "_by_class_name" to "(By.CLASS_NAME,"/"(By.TAG_NAME,"
        deck_tiles = driver.find_elements(By.CLASS_NAME, "archetype-tile")
        for tile in deck_tiles:
            deck_description_container = tile.find_element(By.CLASS_NAME, "archetype-tile-description-wrapper").find_element(By.CLASS_NAME, 
                "archetype-tile-description").find_element(By.CLASS_NAME, deck_URL_container_element_tag)
            deck_url = deck_description_container.find_element(By.TAG_NAME, 
                'a').get_attribute("href")

            # For some reason, the #paper landing page contains URLS for the #online
            budget_deck_url_list.append(deck_url)
    except:
        driver.close()
        return budget_deck_url_list

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
    progress_bar = IncrementalBar("   Evaluating", max=len(desired_decks_list) * len(owned_cards_list), suffix='%(percent)d%%')
    owned_overlap_report = {}

    for desired_deck in desired_decks_list:
        owned_cards_that_overlap = []

        number_of_owned_cards_that_are_in_desired_deck = 0
        value_reduced_by_owned_cards = 0.0
        for desired_card_entry in desired_deck.get_deck_list():
            desired_card_name = desired_card_entry[CARD_NAME_KEY]

            for owned_card_entry in owned_cards_list:
                progress_bar.next()
                if owned_card_entry[CARD_NAME_KEY].lower() == desired_card_name.lower():
                    if desired_card_entry[CARD_QTY_KEY] >= owned_card_entry[CARD_QTY_KEY]:
                        number_of_owned_cards_that_are_in_desired_deck += owned_card_entry[CARD_QTY_KEY]
                        value_reduced_by_owned_cards += float(
                            owned_card_entry[CARD_QTY_KEY] * desired_card_entry[CARD_PRICE_KEY])
                        owned_cards_that_overlap.append({CARD_NAME_KEY: desired_card_name, CARD_QTY_KEY: owned_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(
                            owned_card_entry[CARD_QTY_KEY] * desired_card_entry[CARD_PRICE_KEY])})
                    else:
                        number_of_owned_cards_that_are_in_desired_deck += desired_card_entry[CARD_QTY_KEY]
                        value_reduced_by_owned_cards += float(
                            desired_card_entry[CARD_QTY_KEY]) * desired_card_entry[CARD_PRICE_KEY]
                        owned_cards_that_overlap.append({CARD_NAME_KEY: desired_card_name, CARD_QTY_KEY: desired_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(
                            desired_card_entry[CARD_QTY_KEY]) * desired_card_entry[CARD_PRICE_KEY]})
                    break

        # If we actually own some cards in this desired_deck, save the report. If not, we set the NO_OWNED_OVERLAP_FLAG so that our final report printing can know
        owned_overlap_report[desired_deck.get_deck_name()] = {}
        if value_reduced_by_owned_cards > 0:
            owned_overlap_report[desired_deck.get_deck_name()] = {OWNED_CARDS_KEY: "%d/%d" % (number_of_owned_cards_that_are_in_desired_deck, desired_deck.get_deck_size(
            )), SAVED_VALUE_KEY: value_reduced_by_owned_cards, CARD_LIST_KEY: owned_cards_that_overlap}
        else:
            owned_overlap_report[desired_deck.get_deck_name()] = {
                SAVED_VALUE_KEY: NO_OWNED_OVERLAP_FLAG}
    
    progress_bar.finish()

    return owned_overlap_report


"""
For each metagame deck in the desired format, we determine how much monetary overlap we currently possess for it,
and return back a sorted list of the Meta decks, together with which cards and what value we overlap

:param metagame_decks: A list of Deck objects representing all of the Metagame decks on MTGGoldfish.com
:param owned_cards: A list of dicts containing card info of the format: {CARD_QTY_KEY: card_quantity, CARD_NAME_KEY: card_name}
"""
def evaluate_metagame_decks(metagame_decks, owned_cards):
    progress_bar = IncrementalBar("   Evaluating", max=len(metagame_decks) * len(owned_cards), suffix='%(percent)d%%')
    metagame_deck_recommendation_report = {}

    for meta_deck in metagame_decks:
        specific_cards_owned_in_meta_deck = []
        number_of_owned_cards_that_are_in_meta_deck = 0
        value_of_meta_deck_owned = 0.0

        for owned_card_entry in owned_cards:
            owned_card_name = owned_card_entry[CARD_NAME_KEY]

            # Check for this card's presence in the meta_deck
            for meta_card_entry in meta_deck.get_deck_list():
                if meta_card_entry[CARD_NAME_KEY].lower() == owned_card_name.lower():
                    if owned_card_entry[CARD_QTY_KEY] >= meta_card_entry[CARD_QTY_KEY]:
                        number_of_owned_cards_that_are_in_meta_deck += meta_card_entry[CARD_QTY_KEY]
                        value_of_meta_deck_owned += float(
                            meta_card_entry[CARD_QTY_KEY]) * meta_card_entry[CARD_PRICE_KEY]
                        specific_cards_owned_in_meta_deck.append({CARD_NAME_KEY: owned_card_name, CARD_QTY_KEY: meta_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(
                            meta_card_entry[CARD_QTY_KEY]) * meta_card_entry[CARD_PRICE_KEY]})
                    else:
                        number_of_owned_cards_that_are_in_meta_deck += owned_card_entry[CARD_QTY_KEY]
                        value_of_meta_deck_owned += float(
                            owned_card_entry[CARD_QTY_KEY]) * meta_card_entry[CARD_PRICE_KEY]
                        specific_cards_owned_in_meta_deck.append({CARD_NAME_KEY: owned_card_name, CARD_QTY_KEY: owned_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(
                            owned_card_entry[CARD_QTY_KEY]) * meta_card_entry[CARD_PRICE_KEY]})
                    break

            progress_bar.next()

        # Only save the report if we actually own some cards in this Metagame deck
        if value_of_meta_deck_owned > 0:
            metagame_deck_recommendation_report[meta_deck.get_deck_name()] = {
            }
            metagame_deck_recommendation_report[meta_deck.get_deck_name()] = {OWNED_CARDS_KEY: "%d/%d" % (number_of_owned_cards_that_are_in_meta_deck, meta_deck.get_deck_size(
            )), SAVED_VALUE_KEY: value_of_meta_deck_owned, CARD_LIST_KEY: specific_cards_owned_in_meta_deck, DECK_PRICE_KEY: meta_deck.get_deck_price()}

    # Sort entries by value descending
    metagame_decks_sorted_by_desc_value_saved_as_list = sorted(six.iteritems(
        metagame_deck_recommendation_report), key=lambda kv: kv[1][SAVED_VALUE_KEY], reverse=True)
    
    progress_bar.finish()

    # Return only the top 15
    if len(metagame_decks_sorted_by_desc_value_saved_as_list) > 15:
        return metagame_decks_sorted_by_desc_value_saved_as_list[:15]
    else:
        return metagame_decks_sorted_by_desc_value_saved_as_list


"""
For each desired deck, we process each budget deck to determine how many cards from each budget deck
are present in the given desired deck. We then store them into a large multi-level dictionary for
eventual reporting
"""
def evaluate_budget_decks(owned_cards, desired_decks_list, budget_decks_list):
    progress_bar = IncrementalBar("   Evaluating", max=len(desired_decks_list) * len(budget_decks_list), suffix='%(percent)d%%')
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
                                    value_of_budget_deck_owned += float(
                                        budget_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                                    specific_owned_cards_in_budget_deck.append({CARD_NAME_KEY: owned_card_name, CARD_QTY_KEY: budget_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(
                                        budget_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]})

                            else:

                                # Only add this card if it doesn't already exist in the specific_owned_cards_in_budget_deck list
                                already_exists = False
                                for card_record in specific_owned_cards_in_budget_deck:
                                    if card_record[CARD_NAME_KEY] == owned_card_name:
                                        already_exists = True
                                        break
                                if not already_exists:
                                    number_of_owned_cards_that_are_in_budget_deck += owned_card_entry[CARD_QTY_KEY]
                                    value_of_budget_deck_owned += float(
                                        owned_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                                    specific_owned_cards_in_budget_deck.append({CARD_NAME_KEY: owned_card_name, CARD_QTY_KEY: owned_card_entry[CARD_QTY_KEY], CARD_PRICE_KEY: float(
                                        owned_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]})

                    if budget_card_entry[CARD_NAME_KEY].lower() == desired_card_name.lower():
                        if desired_card_entry[CARD_QTY_KEY] >= budget_card_entry[CARD_QTY_KEY]:
                            number_of_cards_from_budget_deck_that_are_in_desired_deck += budget_card_entry[
                                CARD_QTY_KEY]
                            value_shared_between_decks += float(
                                budget_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                        else:
                            number_of_cards_from_budget_deck_that_are_in_desired_deck += desired_card_entry[
                                CARD_QTY_KEY]
                            value_shared_between_decks += float(
                                desired_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                        break

            # Only bother reporting budget decks that actually overlap
            if value_shared_between_decks > 0:
                budget_report[desired_deck.get_deck_name()][budget_deck.get_deck_name()] = {DECK_PRICE_KEY: budget_deck.get_deck_price(), SHARED_CARDS_KEY: "%d/%d" % (number_of_cards_from_budget_deck_that_are_in_desired_deck, budget_deck.get_deck_size(
                )), SHARED_VALUE_KEY: value_shared_between_decks, OWNED_CARDS_KEY: "%d/%d" % (number_of_owned_cards_that_are_in_budget_deck, budget_deck.get_deck_size()), SAVED_VALUE_KEY: value_of_budget_deck_owned, CARD_LIST_KEY: specific_owned_cards_in_budget_deck}

            progress_bar.next()

        # Sort entries by value for this particular desired_deck now that all of the budget decks have been processed
        budget_decks_sorted_by_desc_value_as_list = sorted(six.iteritems(
            budget_report[desired_deck.get_deck_name()]), key=lambda kv: kv[1][SHARED_VALUE_KEY], reverse=True)

        # Only keep the top 5 for each
        budget_report[desired_deck.get_deck_name(
        )] = budget_decks_sorted_by_desc_value_as_list[:5]

    progress_bar.finish()

    return budget_report


"""
Give a final evaluation report displaying how the cards that you own line up with the Metagame
decks you specified desired_decks.txt
"""
def print_owned_cards_evaluation_report(report_output_file_name, desired_decks_list, owned_cards_overlap_report, use_online_price):

    # This is super nasty, but whatever. We print to the file if we're actually given a file to print to. Otherwise we print to the terminal
    if report_output_file_name != "":
        with open(report_output_file_name, 'a') as output_file:
            output_file.write(
                "\n\n=== Owned Card report for Desired Decks listed in desired_decks.txt ===")
            for desired_deck_name_key in owned_cards_overlap_report:

                # This is a super clumsy way to fetch the price of the original deck
                desired_deck_total_cost = 0.0
                for desired_deck_obj in desired_decks_list:
                    if desired_deck_obj.get_deck_name().lower() == desired_deck_name_key.lower():
                        desired_deck_total_cost = desired_deck_obj.get_deck_price()
                        if use_online_price:
                            output_file.write("\n\n   Owned cards that are used in \"%s\" (%.2f tix):" %
                                  (desired_deck_name_key, desired_deck_total_cost))
                        else:
                            output_file.write("\n\n   Owned cards that are used in \"%s\" ($%.2f):" %
                                  (desired_deck_name_key, desired_deck_total_cost))

                # The owned_cards_overlap_report is of the format:
                # {'Saved Value': 265.96, 'Card List': [{'Card Name': u'Scalding Tarn', 'Card Quantity': 4}], 'Owned Cards': '4/73'}
                specific_owned_cards_report = owned_cards_overlap_report[desired_deck_name_key]
                if specific_owned_cards_report[SAVED_VALUE_KEY] == NO_OWNED_OVERLAP_FLAG:
                    output_file.write(
                        "\n      None of the cards you own overlap with this deck :(")
                else:
                    output_file.write("\n      Number of cards owned: %s" % (
                        specific_owned_cards_report[OWNED_CARDS_KEY]))
                    if use_online_price:
                        output_file.write("\n      Value saved: %.2f tix" %
                              (specific_owned_cards_report[SAVED_VALUE_KEY]))
                        output_file.write("\n      Remaining cost: %.2f tix" % (
                            desired_deck_total_cost - specific_owned_cards_report[SAVED_VALUE_KEY]))
                    else:
                        output_file.write("\n      Value saved: $%.2f" %
                              (specific_owned_cards_report[SAVED_VALUE_KEY]))
                        output_file.write("\n      Remaining cost: $%.2f" % (
                            desired_deck_total_cost - specific_owned_cards_report[SAVED_VALUE_KEY]))
                    output_file.write("\n      List of specific cards:")
                    for card_entry in specific_owned_cards_report[CARD_LIST_KEY]:
                        if use_online_price:
                            output_file.write("\n         %sx %s (%.2f tix)" % (
                                card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
                        else:
                            output_file.write("\n         %sx %s ($%.2f)" % (
                                card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))

    else:
        print("\n=== Owned Card report for Desired Decks listed in desired_decks.txt ===")
        for desired_deck_name_key in owned_cards_overlap_report:

            # This is a super clumsy way to fetch the price of the original deck
            desired_deck_total_cost = 0.0
            for desired_deck_obj in desired_decks_list:
                if desired_deck_obj.get_deck_name().lower() == desired_deck_name_key.lower():
                    desired_deck_total_cost = desired_deck_obj.get_deck_price()
                    if use_online_price:
                        print("\n   Owned cards that are used in \"%s\" (%.2f tix):" %
                              (desired_deck_name_key, desired_deck_total_cost))
                    else:
                        print("\n   Owned cards that are used in \"%s\" ($%.2f):" %
                              (desired_deck_name_key, desired_deck_total_cost))

            # The owned_cards_overlap_report is of the format:
            # {'Saved Value': 265.96, 'Card List': [{'Card Name': u'Scalding Tarn', 'Card Quantity': 4}], 'Owned Cards': '4/73'}
            specific_owned_cards_report = owned_cards_overlap_report[desired_deck_name_key]
            if specific_owned_cards_report[SAVED_VALUE_KEY] == NO_OWNED_OVERLAP_FLAG:
                print("      None of the cards you own overlap with this deck :(")
            else:
                print("      Number of cards owned: %s" %
                      (specific_owned_cards_report[OWNED_CARDS_KEY]))
                if use_online_price:
                    print("      Value saved: %.2f tix" %
                          (specific_owned_cards_report[SAVED_VALUE_KEY]))
                    print("      Remaining cost: %.2f tix" % (
                        desired_deck_total_cost - specific_owned_cards_report[SAVED_VALUE_KEY]))
                else:
                    print("      Value saved: $%.2f" %
                          (specific_owned_cards_report[SAVED_VALUE_KEY]))
                    print("      Remaining cost: $%.2f" % (
                        desired_deck_total_cost - specific_owned_cards_report[SAVED_VALUE_KEY]))
                print("      List of specific cards:")
                for card_entry in specific_owned_cards_report[CARD_LIST_KEY]:
                    if use_online_price:
                        print("         %sx %s (%.2f tix)" % (
                            card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
                    else:
                        print("         %sx %s ($%.2f)" % (
                            card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))


"""
Print a final report of the Metagame decks that you have share the most value with

:param metagame_deck_recommendation_report: A list of tuples containing (<deck_name>, <report_summary_for_this_deck>) pairs,
                                                   sorted descending based on the 'Saved Value' key in the <Report_summary_for_this_deck>
"""
def print_metagame_deck_recommendation_report(report_output_file_name, metagame_deck_recommendation_report, use_online_price):

    # This is super nasty, but whatever. We print to the file if we're actually given a file to print to. Otherwise we print to the terminal
    if report_output_file_name != "":
        with open(report_output_file_name, 'a') as output_file:
            output_file.write(
                "\n\n=== Metagame deck recommendation report based on Cards listed in owned_cards.txt ===")

            # The sort method turns the dictionary into a list of a tuple like this: [('Affinity', {'Saved Value': 62.87, 'Owned Cards': '3/72', 'Deck Price': 1032.95, 'Specific Cards': [{}]}), ...]
            for deck_summary_entry in metagame_deck_recommendation_report:
                output_file.write("\n\n   #%s Closest Match:" % (
                    metagame_deck_recommendation_report.index(deck_summary_entry) + 1))
                if use_online_price:
                    output_file.write("\n      Meta Deck: \"%s\" (%.2f tix)" %
                          (deck_summary_entry[0], deck_summary_entry[1][DECK_PRICE_KEY]))
                else:
                    output_file.write("\n      Meta Deck: \"%s\" ($%.2f)" %
                          (deck_summary_entry[0], deck_summary_entry[1][DECK_PRICE_KEY]))
                output_file.write("\n      Number of cards owned: %s" %
                      (deck_summary_entry[1][OWNED_CARDS_KEY]))
                if use_online_price:
                    output_file.write("\n      Value of cards owned: %.2f tix" %
                          (deck_summary_entry[1][SAVED_VALUE_KEY]))
                else:
                    output_file.write("\n      Value of cards owned: $%.2f" %
                          (deck_summary_entry[1][SAVED_VALUE_KEY]))
                if use_online_price:
                    output_file.write("\n      Remaining cost: %.2f tix" % (
                        deck_summary_entry[1][DECK_PRICE_KEY] - deck_summary_entry[1][SAVED_VALUE_KEY]))
                else:
                    output_file.write("\n      Remaining cost: $%.2f" % (
                        deck_summary_entry[1][DECK_PRICE_KEY] - deck_summary_entry[1][SAVED_VALUE_KEY]))
                output_file.write("\n      List of specific cards:")
                for card_entry in deck_summary_entry[1][CARD_LIST_KEY]:
                    if use_online_price:
                        output_file.write("\n         %sx %s (%.2f tix)" % (
                            card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
                    else:
                        output_file.write("\n         %sx %s ($%.2f)" % (
                            card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
    else:
        print("\n=== Metagame deck recommendation report based on Cards listed in owned_cards.txt ===")

        # The sort method turns the dictionary into a list of a tuple like this: [('Affinity', {'Saved Value': 62.87, 'Owned Cards': '3/72', 'Deck Price': 1032.95, 'Specific Cards': [{}]}), ...]
        for deck_summary_entry in metagame_deck_recommendation_report:
            print("\n   #%s Closest Match:" % (
                metagame_deck_recommendation_report.index(deck_summary_entry) + 1))
            if use_online_price:
                print("      Meta Deck: \"%s\" (%.2f tix)" %
                      (deck_summary_entry[0], deck_summary_entry[1][DECK_PRICE_KEY]))
            else:
                print("      Meta Deck: \"%s\" ($%.2f)" %
                      (deck_summary_entry[0], deck_summary_entry[1][DECK_PRICE_KEY]))
            print("      Number of cards owned: %s" %
                  (deck_summary_entry[1][OWNED_CARDS_KEY]))
            if use_online_price:
                print("      Value of cards owned: %.2f tix" %
                      (deck_summary_entry[1][SAVED_VALUE_KEY]))
            else:
                print("      Value of cards owned: $%.2f" %
                      (deck_summary_entry[1][SAVED_VALUE_KEY]))
            if use_online_price:
                print("      Remaining cost: %.2f tix" % (
                    deck_summary_entry[1][DECK_PRICE_KEY] - deck_summary_entry[1][SAVED_VALUE_KEY]))
            else:
                print("      Remaining cost: $%.2f" % (
                    deck_summary_entry[1][DECK_PRICE_KEY] - deck_summary_entry[1][SAVED_VALUE_KEY]))
            print("      List of specific cards:")
            for card_entry in deck_summary_entry[1][CARD_LIST_KEY]:
                if use_online_price:
                    print("         %sx %s (%.2f tix)" % (
                        card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
                else:
                    print("         %sx %s ($%.2f)" % (
                        card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))


"""
Give a final evaluation report for the Budget decks by iterating
over each entry and printing it out to the terminal in a clear way
"""
def print_budget_evaluation_report(report_output_file_name, desired_decks_list, budget_deck_report, use_online_price):

    # This is super nasty, but whatever. We print to the file if we're actually given a file to print to. Otherwise we print to the terminal
    if report_output_file_name != "":
        with open(report_output_file_name, 'a') as output_file:
            output_file.write(
                "\n\n=== Budget Deck report comparing against Desired Decks listed in desired_decks.txt ===")
            for desired_deck_name_key in budget_deck_report:

                # This is a super clumsy way to fetch the price of the original deck
                for desired_deck_obj in desired_decks_list:
                    if desired_deck_obj.get_deck_name().lower() == desired_deck_name_key.lower():
                        if use_online_price:
                            output_file.write("\n   Budget Decks that compare to Desired Deck: \"%s\" (%.2f tix):" % (
                                desired_deck_name_key, desired_deck_obj.get_deck_price()))
                        else:
                            output_file.write("\n   Budget Decks that compare to Desired Deck: \"%s\" ($%.2f):" % (
                                desired_deck_name_key, desired_deck_obj.get_deck_price()))

                # The sort method turns the dictionary into a list of a tuple like this: [('Rogues', {'Shared Value': 2.87, 'Shared Cards': '1/72', 'Deck Price': 32.95}), ...]
                for budget_deck_list_record in budget_deck_report[desired_deck_name_key]:
                    output_file.write("\n\n      #%s Closest Match:" % (
                        budget_deck_report[desired_deck_name_key].index(budget_deck_list_record) + 1))
                    output_file.write("\n         Budget Deck Name: %s" % (
                        budget_deck_list_record[0]))
                    if use_online_price:
                        output_file.write("\n         Budget Deck cost: %s tix" % (
                            budget_deck_list_record[1][DECK_PRICE_KEY]))
                    else:
                        output_file.write("\n         Budget Deck cost: $%s" % (
                            budget_deck_list_record[1][DECK_PRICE_KEY]))
                    output_file.write("\n         Number of cards shared: %s" % (
                        budget_deck_list_record[1][SHARED_CARDS_KEY]))
                    if use_online_price:
                        output_file.write("\n         Value shared: %.2f tix" % (
                            budget_deck_list_record[1][SHARED_VALUE_KEY]))
                    else:
                        output_file.write("\n         Value shared: $%.2f" % (
                            budget_deck_list_record[1][SHARED_VALUE_KEY]))
                    output_file.write("\n         Owned Cards Report:")
                    if budget_deck_list_record[1][SAVED_VALUE_KEY] != 0:
                        output_file.write("\n            Number of cards owned: %s" % (
                            budget_deck_list_record[1][OWNED_CARDS_KEY]))
                        if use_online_price:
                            output_file.write("\n            Value of cards owned: %.2f tix" % (
                                budget_deck_list_record[1][SAVED_VALUE_KEY]))
                        else:
                            output_file.write("\n            Value of cards owned: $%.2f" % (
                                budget_deck_list_record[1][SAVED_VALUE_KEY]))
                        if use_online_price:
                            output_file.write("\n            Remaining cost: %.2f tix" % (
                                budget_deck_list_record[1][DECK_PRICE_KEY] - budget_deck_list_record[1][SAVED_VALUE_KEY]))
                        else:
                            output_file.write("\n            Remaining cost: $%.2f" % (
                                budget_deck_list_record[1][DECK_PRICE_KEY] - budget_deck_list_record[1][SAVED_VALUE_KEY]))
                        output_file.write(
                            "\n            List of specific cards:")
                        for card_entry in budget_deck_list_record[1][CARD_LIST_KEY]:
                            if use_online_price:
                                output_file.write("\n               %sx %s (%.2f tix)" % (
                                    card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
                            else:
                                output_file.write("\n               %sx %s ($%.2f)" % (
                                    card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
                    else:
                        output_file.write(
                            "\n               None of the cards listed in owned_cards.txt are used in this deck :(")

    else:
        print("\n=== Budget Deck report comparing against Desired Decks listed in desired_decks.txt ===")
        for desired_deck_name_key in budget_deck_report:

            # This is a super clumsy way to fetch the price of the original deck
            for desired_deck_obj in desired_decks_list:
                if desired_deck_obj.get_deck_name().lower() == desired_deck_name_key.lower():
                    print("   Budget Decks that compare to Desired Deck: \"%s\" ($%.2f):" % (
                        desired_deck_name_key, desired_deck_obj.get_deck_price()))

            # The sort method turns the dictionary into a list of a tuple like this: [('Rogues', {'Shared Value': 2.87, 'Shared Cards': '1/72', 'Deck Price': 32.95}), ...]
            for budget_deck_list_record in budget_deck_report[desired_deck_name_key]:
                print("\n      #%s Closest Match:" % (
                    budget_deck_report[desired_deck_name_key].index(budget_deck_list_record) + 1))
                print("         Budget Deck Name: %s" %
                      (budget_deck_list_record[0]))
                if use_online_price:
                    print("         Budget Deck cost: %s tix" % (
                        budget_deck_list_record[1][DECK_PRICE_KEY]))
                else:
                    print("         Budget Deck cost: $%s" % (
                        budget_deck_list_record[1][DECK_PRICE_KEY]))
                print("         Number of cards shared: %s" % (
                    budget_deck_list_record[1][SHARED_CARDS_KEY]))
                if use_online_price:
                    print("         Value shared: %.2f tix" % (
                        budget_deck_list_record[1][SHARED_VALUE_KEY]))
                else:
                    print("         Value shared: $%.2f" % (
                        budget_deck_list_record[1][SHARED_VALUE_KEY]))
                print("         Owned Cards Report:")
                if budget_deck_list_record[1][SAVED_VALUE_KEY] != 0:
                    print("            Number of cards owned: %s" % (
                        budget_deck_list_record[1][OWNED_CARDS_KEY]))
                    if use_online_price:
                        print("            Value of cards owned: %.2f tix" % (
                            budget_deck_list_record[1][SAVED_VALUE_KEY]))
                    else:
                        print("            Value of cards owned: $%.2f" % (
                            budget_deck_list_record[1][SAVED_VALUE_KEY]))
                    if use_online_price:
                        print("            Remaining cost: %.2f tix" % (
                            budget_deck_list_record[1][DECK_PRICE_KEY] - budget_deck_list_record[1][SAVED_VALUE_KEY]))
                    else:
                        print("            Remaining cost: $%.2f" % (
                            budget_deck_list_record[1][DECK_PRICE_KEY] - budget_deck_list_record[1][SAVED_VALUE_KEY]))
                    print(
                        "            List of specific cards:")
                    for card_entry in budget_deck_list_record[1][CARD_LIST_KEY]:
                        if use_online_price:
                            print("               %sx %s (%.2f tix)" % (
                                card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
                        else:
                            print("               %sx %s ($%.2f)" % (
                                card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY], card_entry[CARD_PRICE_KEY]))
                else:
                    print(
                        "               None of the cards listed in owned_cards.txt are used in this deck :(")


"""
Given the desired Format (Modern, Standard, Vintage, etc) and whether or not the user desired online vs paper pricing,
return a tuple containing the URLs where the corresponding Metagame and Budget decks can be found

:param desired_format: The desired Format to analyze
:param use_online_price: True if the user wants pricing analysis to be performed in online (tix) pricing
"""
def determine_meta_and_budget_URLs(desired_format, use_online_price):
    pricing_query_param = "#paper"
    if use_online_price:
        pricing_query_param = "#online"

    if desired_format == "standard":
        return ("https://www.mtggoldfish.com/metagame/standard/full" + pricing_query_param, "https://www.mtggoldfish.com/decks/budget/standard" + pricing_query_param)
    elif desired_format == "modern":
        return ("https://www.mtggoldfish.com/metagame/modern/full" + pricing_query_param, "https://www.mtggoldfish.com/decks/budget/modern" + pricing_query_param)
    elif desired_format == "pauper":
        return ("https://www.mtggoldfish.com/metagame/pauper/full" + pricing_query_param, "https://www.mtggoldfish.com/decks/budget/pauper" + pricing_query_param)
    elif desired_format == "legacy":
        return ("https://www.mtggoldfish.com/metagame/legacy/full" + pricing_query_param, "https://www.mtggoldfish.com/decks/budget/legacy" + pricing_query_param)
    elif desired_format == "vintage":
        return ("https://www.mtggoldfish.com/metagame/vintage/full" + pricing_query_param, "https://www.mtggoldfish.com/decks/budget/vintage" + pricing_query_param)
    elif desired_format == "frontier":
        return ("https://www.mtggoldfish.com/metagame/frontier/full" + pricing_query_param, "https://www.mtggoldfish.com/decks/budget/frontier" + pricing_query_param)
    elif desired_format == "commander 1v1":
        return ("https://www.mtggoldfish.com/metagame/commander_1v1/full" + pricing_query_param, "https://www.mtggoldfish.com/decks/budget/commander_1v1" + pricing_query_param)
    elif desired_format == "commander":
        return ("https://www.mtggoldfish.com/metagame/commander/full" + pricing_query_param, "https://www.mtggoldfish.com/decks/budget/commander" + pricing_query_param)
    elif desired_format == "tiny leaders":
        return ("https://www.mtggoldfish.com/metagame/tiny_leaders/full" + pricing_query_param, "https://www.mtggoldfish.com/decks/budget/tiny_leaders" + pricing_query_param)
    else:
        return (None, None)


if __name__ == "__main__":
    print("")
    print("=====================================================")
    print("================ Beginning Fresh Run ================")
    print("=====================================================")

    parser = OptionParser(description=("This script parses decks you'd like to build into from MTGGoldfish.com, listed as URLS in desired_decks.txt"
                                       " as well as any cards listed in owned_cards.txt to tell you how far along you already are to constructing"
                                       " those desired decks with the cards you already own. Additionally, this script can perform up to two additional"
                                       " evaluations by specifying the \"-b\" and/or \"-r\" flag(s)"))
    parser.add_option("-b", "--budget",
        dest="parse_budget",
        help="Parse all Budget decks of the desired gameplay format (specified with the -F flag) from MTGGoldfish and then run a \"Budget Deck\" analysis as described in the README. Data for any decks which have been fetched previously will not be re-fetched, unless the \"-u\" flag is specified. Likewise, any new decks fetched will have their data cached for future runs. This can take 10 minutes or more for the first run.",
        action='store_const',
        const=True)
    parser.add_option("-r", "--recommend",
        dest="recommend_meta_decks",
        help="Parse all Metagame decks of the desired gameplay format (specified with the -F flag) from MTGGoldfish and then run a \"Modern Metagame Deck\" analysis as described in the README. Data for any decks which have been fetched previously will not be re-fetched, unless the \"-u\" flag is specified. Likewise, any new decks fetched will have their data cached for future runs. This can take 10 minutes or more for the first run.",
        action='store_const',
        const=True)
    parser.add_option("-o", "--online",
        dest="use_online_price",
        help="If this flag is specified, all designated analyses will be run using the online (tix) value of cards instead of paper value",
        action='store_const',
        const=True)
    parser.add_option("-F", "--format",
        dest="desired_format",
        default="modern",
        help="Specify the gameplay format you want to run the designated analyses for. Valid formats are (case insensitive): Standard | Modern | Pauper | Legacy | Vintage | Frontier | Commander 1v1 | Commander | Tiny Leaders [default: %default]",)
    parser.add_option("-u", "--update",
        dest="update_cache",
        help="Fetches fresh data for all decks required during this run (cache-bust). This can take 10 minutes or more",
        action='store_const',
        const=True)
    parser.add_option("-f", "--file",
        dest="print_to_file",
        help="Informs the script to print all reports to a .txt file. The file name will be of the format: deck_report_MM_DD_YYYY.txt, overwriting any existing report with the same file name.",
        action='store_const',
        const=True)
    (options, args) = parser.parse_args()

    owned_cards = parse_owned_cards()
    desired_deck_URLs = parse_desired_deck_URLs()

    # Sanitize Format input
    if options.desired_format.lower() not in ["standard", "modern", "pauper", "legacy", "vintage", "frontier", "commander 1v1", "commander", "tiny leaders"]:
        print(
            "\n[ERROR] Format \"%s\" is not a valid format. Exiting" %
            options.desired_format)
        sys.exit(0)

    (url_for_meta_decks, url_for_budget_decks) = determine_meta_and_budget_URLs(
        options.desired_format, options.use_online_price)

    start_time = time.time()
    print("\nFetching Deck information for decks listed in desired_decks.txt.")
    desired_decks = parse_decks_from_list_of_urls(
        options.update_cache, desired_deck_URLs, options.use_online_price)

    # If the User hasn't specified any cards in owned_cards.txt, then the only other reason to run this script at all is
    # to generate a report on the Budget Decks from MTGGoldfish.com. So that's what we will do.
    no_owned_cards_in_list = (len(
        owned_cards) == 1 and owned_cards[0][CARD_NAME_KEY] == "name of card that doesn't exist") or len(
        owned_cards) == 0
    should_run_budget_analysis = False
    if options.parse_budget or no_owned_cards_in_list:
        should_run_budget_analysis = True
    if should_run_budget_analysis and len(desired_decks) == 0:
        print(
            "\n[ERROR] Budget Analysis implied but there are no decks listed in desired_decks.txt. Exiting")
        sys.exit(0)

    # Perform Metagame Recommendation Analysis if desired
    metagame_decks = []
    if options.recommend_meta_decks:

        # We can't recommend meta decks if the User supplied no cards
        if no_owned_cards_in_list:
            print(
                "\n[ERROR]: Recommend flag set, but no cards provided in owned_cards.txt. Skipping")
        else:
            print("\nRecommend flag set. Fetching Deck information of all %s Metagame decks for Recommendation analysis..." %
                options.desired_format)
            metagame_urls_list = parse_deck_urls_from_category_landing_page(
                url_for_meta_decks)
            metagame_decks = parse_decks_from_list_of_urls(
                options.update_cache, metagame_urls_list, options.use_online_price)

    # Perform Budget Analysis if desired
    budget_decks = []
    if should_run_budget_analysis and len(url_for_budget_decks) > 0:
        status_msg = ""
        if options.parse_budget is True:
            status_msg = "\nBudget flag set. "
        else:
            status_msg = "\nowned_cards.txt was empty. "
        print(status_msg + "Fetching Deck information of all %s Budget decks for budget analysis..." %
            options.desired_format)
        budget_decks_url_list = parse_deck_urls_from_category_landing_page(
            url_for_budget_decks)
        budget_decks = parse_decks_from_list_of_urls(
            options.update_cache, budget_decks_url_list, options.use_online_price)

    # Print a statement about the time it took to perform the fetches
    remaining_seconds = (time.time() - start_time)
    num_minutes = 0
    if remaining_seconds >= 60:
        num_minutes = remaining_seconds / 60
        remaining_seconds -= (num_minutes * 60)
    print("\nDone fetching all Deck information. Fetch took %d minutes and %d seconds" % (
        num_minutes, remaining_seconds))          

    if not no_owned_cards_in_list and len(desired_decks) != 0:
        print("\nComputing Owned Cards evaluations...")
        owned_cards_overlap_report = evaluate_owned_cards(
            desired_decks, owned_cards)

    # We can't recommend meta decks if the User supplied no cards
    if options.recommend_meta_decks and not no_owned_cards_in_list:
        print("\nComputing %s Metagame Deck Recommendation evaluations..." %
            options.desired_format)
        metagame_deck_recommendation_report = evaluate_metagame_decks(
            metagame_decks, owned_cards)

    if should_run_budget_analysis and len(budget_decks) == 0:
        print("\n[ERROR]: There aren't any Budget decks for %s to run an analysis on. Skipping Budget analysis." %
                options.desired_format)

    if should_run_budget_analysis and len(budget_decks) > 0:
        print("\nComputing Budget Deck List evaluations...")
        budget_deck_report = evaluate_budget_decks(
            owned_cards, desired_decks, budget_decks)

    report_output_file_name = ""
    if options.print_to_file:

        # Generate an output file with today's date, and open it for appending
        todays_date = datetime.now()
        month = todays_date.month
        day = todays_date.day
        if month <= 9:
            month = "0%s" % (todays_date.month)
        if day <= 9:
            day = "0%s" % (todays_date.day)
        report_file_name = "deck_report_%s_%s_%s.txt" % (
            month, day, todays_date.year)

        script_dir = os.path.dirname(__file__)

        # If we've already generated a report today, we don't want to continue appending to that existing report, so we remove it
        if os.path.isfile(os.path.join(script_dir, report_file_name)):
            os.remove(os.path.join(script_dir, report_file_name))
        report_output_file_name = os.path.join(script_dir, report_file_name)

        print("Generating report...")
    else:
        print("")
        print("============================================")
        print("================ Report(s) =================")
        print("============================================")

    analysis_has_been_performed = False
    if not no_owned_cards_in_list and len(desired_decks) != 0:
        analysis_has_been_performed = True
        print_owned_cards_evaluation_report(
            report_output_file_name, desired_decks, owned_cards_overlap_report, options.use_online_price)

    if options.recommend_meta_decks and not no_owned_cards_in_list:
        analysis_has_been_performed = True
        print_metagame_deck_recommendation_report(
            report_output_file_name, metagame_deck_recommendation_report, options.use_online_price)

    if should_run_budget_analysis and len(budget_decks) > 0:
        analysis_has_been_performed = True
        print_budget_evaluation_report(
            report_output_file_name, desired_decks, budget_deck_report, options.use_online_price)

    if options.print_to_file and analysis_has_been_performed:
        todays_date = datetime.now()
        month = todays_date.month
        day = todays_date.day
        if month <= 9:
            month = "0%s" % (todays_date.month)
        if day <= 9:
            day = "0%s" % (todays_date.day)
        print("Report has been printed to file: \"deck_report_%s_%s_%s.txt\"" %
              (month, day, todays_date.year))

    if not analysis_has_been_performed:
        print("No analysis was performed during this run due to the data that was fetched/provided being insufficient. Try again with different data.")

    sys.exit(0)
