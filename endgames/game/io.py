"""I/O methods for reading input from files and web sources."""

import requests
import logging

# Set up basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# constants
MAX_TIME = 12

def fetch(url):
    """Fetches page from url using requests.

    Minor error handling.

    Args:
        url (str): a URL to access

    Returns:
        Response: a Response object from url
    """
    try:
        response = requests.get(url, timeout=MAX_TIME)
        response.raise_for_status()
        print("Request successful!")
    except requests.exceptions.Timeout:
        reason = f"Error: The request to {url} timed out after {MAX_TIME} seconds."
        logging.error(reason)
        print(reason)
    except requests.exceptions.RequestException as e:
        reason = f"Error: An error with the request occurred: {e}"
        logging.error(reason)
        print(reason)

    return response

def fetch_json(url):
    """Fetches JSON from url using requests.

    Args:
        url (str): a URL to access

    Returns:
        Any: an interpreted JSON, typically a dict or list of dicts
    """
    response = fetch(url)
    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        reason = "Error: Failed to decode JSON response."
        logging.error(reason)
        print(reason)

    return data

def read_printout(file_path):
    """Reads in data, typically hanabi decks, from a file

    Args:
        file_path (str): the file path

    Returns:
        list: list of file lines, interpreted as a hanabi deck
    """
    try:
        decks = []
        with open(file_path, 'r', encoding="utf-8") as file:
            for line in file.readlines():
                line = line.strip()
                line = line.strip("[]")
                deck = [el.strip() for el in line.split(",")]
                if len(deck) == 1:
                    deck = [el.strip() for el in deck[0].split()]
                decks.append(deck)
        return decks
    except FileNotFoundError as e:
        reason = f"Error: Failed to find file at {file_path}: {e}"
        logging.error(reason)
        print(reason)
        raise e
    except IOError as e:
        reason = f"Error: Failed to read file at {file_path}: {e}"
        logging.error(reason)
        print(reason)
        raise e
