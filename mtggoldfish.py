# -*- coding: utf-8 -*-
"""
This script parses some meta Modern decklists that we would eventually want to play from mtggoldfish.com.
It then scrapes all of the budget deck lists and reports back with budget decks that are more than match_threshold
identical to one or more of your desired Modern meta decks.
"""

import csv
from datetime import datetime
import errno
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

# Final Report dict keys
DECK_PRICE_KEY = 'Deck Price'
SHARED_CARDS_KEY = 'Shared Cards'
SHARED_VALUE_KEY = 'Shared Value'


"""
Simple configuration class. Contains the URLs to all desired decks, as well as the match threshold
"""
class Configuration(object):
    def __init__(self):
        self.match_threshold = 60
        self.matt_desired_decks = [
                # "https://www.mtggoldfish.com/archetype/modern-abzan#paper",
                # "https://www.mtggoldfish.com/archetype/modern-counters-company#paper",
                "https://www.mtggoldfish.com/archetype/modern-eldrazi-tron-26966#paper"
            ]
        self.mel_desired_decks = [
                'https://www.mtggoldfish.com/archetype/modern-burn-34574#paper',
                'https://www.mtggoldfish.com/archetype/modern-affinity-8972#paper'
            ]

    def get_match_threshold(self):
        return self.match_threshold

    def get_matt_desired_decks(self):
        return self.matt_desired_decks

    def get_mel_desired_decks(self):
        return self.mel_desired_decks

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

    def __str__(self):
        print_output = "Deck Name: %s\nDeck URL: %s\nDeck Date: %s\nDeck Price: %.2f\nDeck List:\n{\n" %(self.deck_name, self.deck_url, self.deck_date, self.deck_price)
        for card_entry in self.deck_list:
            print_output = print_output + "     %dx %s,\n" %(card_entry[CARD_QTY_KEY], card_entry[CARD_NAME_KEY])
        return print_output + "}"


"""
Given the desired deck URLs, parse all of the decks into Deck objects

:param driver: The webdriver to use for navigating the browser
:param deck_URLs_list: The list of deck URLs
"""
def parse_decks_from_list_of_urls(driver, deck_URLs_list):
    deck_objs_list = []

    for desired_deck_url in deck_URLs_list:
        deck = Deck()
        driver.get(desired_deck_url)

        deck.deck_url = desired_deck_url
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
                card_quantity = int(columns[QTY_INDEX].get_attribute('textContent').replace('\n', ''))
                card_name = columns[NAME_INDEX].get_attribute('textContent').replace('\n', '')
                individual_card_price = float(columns[PRICE_INDEX].get_attribute('textContent').replace('\n', '')) / float(card_quantity)
                deck_total_cost += float(columns[PRICE_INDEX].get_attribute('textContent').replace('\n', ''))
                deck_list.append({CARD_QTY_KEY: card_quantity, CARD_NAME_KEY: card_name, CARD_PRICE_KEY: individual_card_price})


        deck.deck_list = deck_list
        deck.deck_price = deck_total_cost
        deck_objs_list.append(deck)

    return deck_objs_list


def parse_all_budget_deck_list_URLs(driver):
    budget_modern_decks_url = "https://www.mtggoldfish.com/decks/budget/modern#paper"
    driver.get(budget_modern_decks_url)

    budget_deck_url_list = []
    deck_tiles = driver.find_elements_by_class_name("archetype-tile")
    for tile in deck_tiles:
        deck_info_container = tile.find_element_by_class_name("archetype-tile-description-wrapper").find_element_by_class_name("archetype-tile-description").find_element_by_class_name("deck-price-paper")
        deck_url = deck_info_container.find_element_by_tag_name('a').get_attribute("href")

        # For some reason, the #paper landing page contains URLS for the #online
        budget_deck_url_list.append(deck_url)

    return budget_deck_url_list


"""
For each desired deck, we process each budget deck to determine how many cards from each budget deck
are present in the given desired deck. We then store 
"""
def evaluate_decks(desired_decks_list, budget_decks_list):
    report = {}
    for desired_deck in desired_decks_list:
        report[desired_deck.get_deck_name()] = {}

        for budget_deck in budget_decks_list:     
            total_non_basics_in_desired_deck = 75
            number_of_cards_from_budget_deck_that_are_in_desired_deck = 0
            value_shared_between_decks = 0.0
            for desired_card_entry in desired_deck.get_deck_list():
                desired_card_name = desired_card_entry[CARD_NAME_KEY]
                if card_is_basic_mana(desired_card_name):
                    total_non_basics_in_desired_deck -= 1
                    continue

                # Check for this card's presence in the first budget deck
                for budget_card_entry in budget_deck.get_deck_list():
                    if budget_card_entry[CARD_NAME_KEY] == desired_card_name:
                        if desired_card_entry[CARD_QTY_KEY] >= budget_card_entry[CARD_QTY_KEY]:
                            number_of_cards_from_budget_deck_that_are_in_desired_deck += budget_card_entry[CARD_QTY_KEY]
                            value_shared_between_decks += float(budget_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                        else:
                            number_of_cards_from_budget_deck_that_are_in_desired_deck += desired_card_entry[CARD_QTY_KEY]
                            value_shared_between_decks += float(desired_card_entry[CARD_QTY_KEY]) * budget_card_entry[CARD_PRICE_KEY]
                        break

            # Only bother reporting budget decks that actually overlap
            if value_shared_between_decks > 0:
                report[desired_deck.get_deck_name()][budget_deck.get_deck_name()] = {DECK_PRICE_KEY: budget_deck.get_deck_price(), SHARED_CARDS_KEY: "%d/%d" %(number_of_cards_from_budget_deck_that_are_in_desired_deck, total_non_basics_in_desired_deck), SHARED_VALUE_KEY: value_shared_between_decks}

        # Sort entries by value for this particular desired_deck now that all of the budget decks have been processed
        budget_decks_sorted_by_desc_value_as_list = sorted(report[desired_deck.get_deck_name()].iteritems(), key=lambda (k,v): v[SHARED_VALUE_KEY], reverse=True)

        # Only keep the top 5 for each
        report[desired_deck.get_deck_name()] = budget_decks_sorted_by_desc_value_as_list[:5]

    return report

"""
Given a final evaluation report, iterate over each entry and print it out to the terminal
in a clear way
"""
def print_evaluation_report(user_name, desired_decks_list, evaluation_report):
    print "\n======== %s's Report ========" %(user_name)
    for desired_deck_name_key in evaluation_report:

        # This is a super clumsy way to fetch the price of the original deck
        for desired_deck_obj in desired_decks_list:
            if desired_deck_obj.get_deck_name() == desired_deck_name_key:
                print "\n== Decks that compare to \"%s\" ($%.2f) ==" %(desired_deck_name_key, desired_deck_obj.get_deck_price())

        # The sort method turns the dictionary into a list of a tuple like this: [('Rogues', {'Shared Value': 2.87, 'Shared Cards': '1/72', 'Deck Price': 32.95}), ...]
        for budget_deck_list_record in evaluation_report[desired_deck_name_key]:
            print "   Budget Deck: %s" %(budget_deck_list_record[0])
            print "      Budget Deck cost: $%s" %(budget_deck_list_record[1][DECK_PRICE_KEY])
            print "      Number of cards shared: %s" %(budget_deck_list_record[1][SHARED_CARDS_KEY])
            print "      Value shared: $%.2f" %(budget_deck_list_record[1][SHARED_VALUE_KEY])


def card_is_basic_mana(card_name):
    return card_name in ["Mountain", "Swamp", "Plains", "Island", "Forest"]

if __name__ == "__main__":
    start_time = time.time()

    print ""
    print "====================================================="
    print "================ Beginning Fresh Run ================"
    print "====================================================="

    config = Configuration()
    driver = webdriver.Firefox()

    print "Fetching desired decks from browser..."
    matt_desired_decks = parse_decks_from_list_of_urls(driver, config.get_matt_desired_decks())
    # mel_desired_decks = parse_decks_from_list_of_urls(driver, config.get_mel_desired_decks())

    print "Fetching budget decks from browser..."
    # budget_decks_url_list = parse_all_budget_deck_list_URLs(driver)
    budget_decks_url_list = ['https://www.mtggoldfish.com/deck/784979$paper']
    budget_decks = parse_decks_from_list_of_urls(driver, budget_decks_url_list)
    driver.close()

    print "Done fetching decks from browser. Browser fetch took %s seconds" %(time.time() - start_time)

    print "\nBeginning evaluation..."
    matt_deck_report = evaluate_decks(matt_desired_decks, budget_decks)
    # mel_deck_report = evaluate_decks(mel_desired_decks, budget_decks)

    print ""
    print "========================================="
    print "================ Report ================"
    print "========================================="

    print_evaluation_report('Matt', matt_desired_decks, matt_deck_report)
    # print_evaluation_report('Mel', mel_desired_decks, mel_deck_report)

    sys.exit(0)