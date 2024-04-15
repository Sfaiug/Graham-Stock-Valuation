import requests
from bs4 import BeautifulSoup
import logging
from decimal import Decimal, InvalidOperation
import os
import shutil
import json

# ANSI escape codes for colors
GREEN = '\033[92m'
BLUE = '\033[94m'
RED = '\033[91m'
YELLOW = '\033[93m'
ENDC = '\033[0m'

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='stock_analysis.log', filemode='w')

# Define the headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def clear_screen():
    if os.name == 'posix':
        os.system('clear')
    else:
        os.system('cls')

def center_text(text, color):
    terminal_width = shutil.get_terminal_size().columns
    centered_text = text.center(terminal_width)
    return f"{color}{centered_text}{ENDC}"

def safe_request(url):
    """Safely make a request to the given URL."""
    try:
        response = requests.get(url, headers=headers, timeout=10) # added timeout
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"{RED}Request failed: {e}{ENDC}")
        return None

def get_stock_price(url, selector):
    """Retrieve the current stock price from a given URL and selector."""
    response = safe_request(url)
    if response:
        soup = BeautifulSoup(response.content, 'html.parser')
        element = soup.select_one(selector)
        if element and element.text:
            return parse_stock_price(element.text)
        else:
            logging.error(f"{RED}Stock price element not found or is empty.{ENDC}")
    return None

def parse_float(value):
    """Attempt to parse a value to a float."""
    try:
        return Decimal(value.replace(',', '').strip('%')) / 100
    except (ValueError, InvalidOperation) as e:
        logging.error(f"{RED}Unable to parse float from value: {value} Error: {e}{ENDC}")
        return None

def get_financial_data(url, selector):
    """General method to scrape financial data from a given URL and selector."""
    response = safe_request(url)
    if response:
        soup = BeautifulSoup(response.content, 'html.parser')
        element = soup.select_one(selector)
        if element:
            return parse_float(element.text)
        else:
            logging.error(f"{RED}Target element not found.{ENDC}")
    return None

def parse_stock_price(price_str):
    """Parse the stock price from the string, removing any formatting."""
    try:
        # Ensure price_str is a string before attempting to replace commas
        if isinstance(price_str, Decimal):
            price_str = str(price_str)
        # Remove commas for thousands and trim any whitespace
        return Decimal(price_str.replace(',', '').strip())
    except (ValueError, InvalidOperation) as e:
        logging.error(f"{RED}Unable to parse stock price from string: {price_str} Error: {e}{ENDC}")
        return None

def calculate_intrinsic_value(eps, g, y):
    """Calculate the intrinsic value of the stock."""
    # Check for negative EPS or growth rate
    if eps <= 0 or g <= 0:
        logging.info(f"{RED}EPS or growth rate is negative. Stock not worth buying.{ENDC}")
        return None

    if eps is not None and g is not None and y is not None:
        # Convert all operands to Decimal
        eps = Decimal(eps)
        g = Decimal(g)
        y = Decimal(y)
        seven = Decimal(7)
        four_point_four = Decimal('4.4')
        one_hundred = Decimal(100)

        v = (eps * (seven + (g * one_hundred)) * four_point_four) / y
        return v
    else:
        logging.error(f"{RED}Unable to calculate intrinsic value due to missing data.{ENDC}")
        return None

def read_tickers_from_json(file_path):
    """Read stock tickers from a JSON file."""
    try:
        with open(file_path, 'r') as file:
            tickers = json.load(file)
        return tickers
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"{RED}Error reading from JSON file: {e}{ENDC}")
        return None

def main():
    try:
        clear_screen()
        print(center_text("Stock Analysis Tool", YELLOW))
        
        tickers = read_tickers_from_json("tickers.json")
        if tickers is None:
            logging.error(f"{RED}No tickers to process.{ENDC}")
            return
        
        logging.info(f"Processing {len(tickers)} tickers...")

        worth_buying = []

        for ticker in tickers:
            try:
                print(f"Processing {ticker}...")
                stock_price_url = f'https://finance.yahoo.com/quote/{ticker}'
                stock_price_selector = "#quote-header-info > div.My\\(6px\\).Pos\\(r\\).smartphone_Mt\\(6px\\).W\\(100\\%\\) > div.D\\(ib\\).Va\\(m\\).Maw\\(65\\%\\).Ov\\(h\\) > div > fin-streamer.Fw\\(b\\).Fz\\(36px\\).Mb\\(-4px\\).D\\(ib\\)"
                stock_price = get_stock_price(stock_price_url, stock_price_selector)
                
                if stock_price is None:
                    logging.error(f"{RED}Stock price for {ticker} could not be retrieved.{ENDC}")
                    continue
                stock_price = parse_stock_price(stock_price)
                if stock_price is None:
                    logging.error(f"{RED}Stock price for {ticker} is not a number.{ENDC}")
                    continue
                eps_url = f'https://finance.yahoo.com/quote/{ticker}'
                eps_selector = "#quote-summary > div.D\\(ib\\).W\\(1\\/2\\).Bxz\\(bb\\).Pstart\\(12px\\).Va\\(t\\).ie-7_D\\(i\\).ie-7_Pos\\(a\\).smartphone_D\\(b\\).smartphone_W\\(100\\%\\).smartphone_Pstart\\(0px\\).smartphone_BdB.smartphone_Bdc\\(\\$seperatorColor\\) > table > tbody > tr:nth-child(4) > td.Ta\\(end\\).Fw\\(600\\).Lh\\(14px\\)"
                eps = get_financial_data(eps_url, eps_selector)
                if eps is None:
                    continue

                growth_url = f'https://finance.yahoo.com/quote/{ticker}/analysis'
                growth_selector = "#Col1-0-AnalystLeafPage-Proxy > section > table:nth-child(7) > tbody > tr:nth-child(5) > td:nth-child(2)"
                g = get_financial_data(growth_url, growth_selector)
                if g is None:
                    continue

                bond_url = 'https://ycharts.com/indicators/moodys_seasoned_aaa_corporate_bond_yield'
                bond_selector = "body > main > div > div:nth-child(5) > div > div > div > div > div.col-md-8 > div.hidden-md > div:nth-child(3) > div.panel-content > div > div:nth-child(1) > table > tbody > tr:nth-child(1) > td:nth-child(2)"
                y = get_financial_data(bond_url, bond_selector)
                if y is None:
                    continue

                intrinsic_value = calculate_intrinsic_value(eps, g, y)
                if intrinsic_value is not None:
                    margin_of_safety_value = intrinsic_value * Decimal('0.8')
                    is_worth_buying = stock_price < margin_of_safety_value
                    recommendation = "Buy" if is_worth_buying else "Don't Buy"
                    color = GREEN if is_worth_buying else RED
                    print(center_text(f"Ticker: {ticker}, Current Price: {stock_price}, Intrinsic Value: {intrinsic_value:.2f}, MOS Value: {margin_of_safety_value:.2f}, Recommendation: {recommendation}", color))

                    if is_worth_buying:
                        worth_buying.append(ticker)

            except Exception as e:
                logging.error(f"An error occurred while processing {ticker}: {e}")

        # Print the list of tickers worth buying
        if worth_buying:
            print("\nTickers worth buying:")
            for ticker in worth_buying:
                print(f"{GREEN}{ticker}{ENDC}")
        else:
            print(f"{RED}No tickers worth buying identified.{ENDC}")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
    input("Press Enter to continue...")  # Pause at the end of the script 