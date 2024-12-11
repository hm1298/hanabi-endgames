import requests
import logging

# Set up basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# constants
MAX_TIME = 12

def fetch(url):
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
    response = fetch(url)
    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError:
        reason = "Error: Failed to decode JSON response."
        logging.error(reason)
        print(reason)

    return data
