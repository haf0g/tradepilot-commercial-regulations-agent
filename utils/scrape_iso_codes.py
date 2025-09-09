import requests
from bs4 import BeautifulSoup
import csv

def scrape_iso_codes(url: str, output_filename: str):
    """
    Scrapes the ISO 3166-1 numeric codes table from the given Wikipedia URL
    and saves the data to a CSV file.

    Args:
        url (str): The URL of the Wikipedia page.
        output_filename (str): The name of the output CSV file.
    """
    print(f"Fetching data from: {url}")
     # --- ADD THIS PART: Define headers ---
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
        # Using a common Chrome browser user agent string
        # You can find updated strings easily online if needed
    }

    try:
        # 1. Fetch the webpage content WITH HEADERS
        response = requests.get(url, headers=headers) 
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print("Page fetched successfully.")

        # 2. Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        print("HTML content parsed.")

        # 3. Find the specific table
        # The table has class 'wikitable sortable'
        table = soup.find('table', {'class': 'wikitable sortable'})

        if not table:
            print("Error: Could not find the target table on the page.")
            return

        print("Target table found.")

        # 4. Extract data from table rows
        rows = table.find('tbody').find_all('tr') # Get rows within the table body
        if not rows:
             print("Error: Could not find table rows.")
             return

        # Prepare data list
        data = []

        # Iterate through rows, skipping the header row (index 0)
        for row in rows[1:]: # Start from the second row (index 1)
            cells = row.find_all(['td', 'th']) # Find both td and th cells in the row
            if len(cells) >= 2: # Ensure the row has at least code and name cells
                # Extract code (text content of the first cell)
                # The code is inside a <span class="monospaced">
                code_span = cells[0].find('span', {'class': 'monospaced'})
                code = code_span.text.strip() if code_span else cells[0].text.strip()

                # Extract country name (text content of the link in the second cell)
                # The country name is inside an <a> tag within the second cell
                name_link = cells[1].find('a')
                name = name_link.text.strip() if name_link else cells[1].text.strip()

                # Optional: Extract notes (text content of the third cell, if it exists)
                # notes = cells[2].text.strip() if len(cells) > 2 else ""

                # Append the extracted data as a tuple/list
                data.append([code, name]) # We only save Code and Name for now
                # data.append([code, name, notes]) # Uncomment if you want notes too

        print(f"Extracted {len(data)} country entries.")

        # 5. Write data to CSV file
        if data:
            with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Write header row
                writer.writerow(['Code', 'Country Name']) # Adjust header if including notes
                # writer.writerow(['Code', 'Country Name', 'Notes'])
                # Write data rows
                writer.writerows(data)

            print(f"Data successfully saved to '{output_filename}'")
        else:
            print("No data found to write to the CSV file.")


    except requests.exceptions.RequestException as e:
        print(f"Error fetching the webpage: {e}")
    except Exception as e: # Catch other potential errors during parsing/writing
        print(f"An error occurred during scraping or file writing: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    WIKI_URL = "https://en.wikipedia.org/wiki/ISO_3166-1_numeric"
    OUTPUT_FILE = "data/csv/iso_country_codes.csv"

    scrape_iso_codes(WIKI_URL, OUTPUT_FILE)
