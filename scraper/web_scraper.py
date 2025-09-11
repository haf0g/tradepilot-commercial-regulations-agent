# scraper/web_scraper.py
import os
import logging
from pathlib import Path
import requests
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError
import time
import re
import json

# --- Configuration ---
EXPORT_COUNTRY = os.getenv("SCRAPER_EXPORT_COUNTRY", "Morocco")
IMPORT_COUNTRY = os.getenv("SCRAPER_IMPORT_COUNTRY", "United States Of America")
PRODUCT_QUERY = os.getenv("SCRAPER_PRODUCT_QUERY", "olive")

# Logger
logger = logging.getLogger(__name__)

def clean_pdfs_folder(pdfs_directory: Path):
    """
    Supprime tous les fichiers PDF existants dans le dossier spécifié.
    """
    if not pdfs_directory.exists():
        logger.info(f"PDF folder {pdfs_directory} does not exist, creating it.")
        pdfs_directory.mkdir(parents=True, exist_ok=True)
        return

    logger.info(f"Cleaning existing PDFs in {pdfs_directory}")
    cleaned_count = 0
    for item in pdfs_directory.iterdir():
        # Supprimer uniquement les fichiers .pdf
        if item.is_file() and item.suffix.lower() == '.pdf':
            try:
                item.unlink()
                logger.debug(f"Deleted old PDF: {item.name}")
                cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {item.name}: {e}")
        # Supprimer les dossiers de logs ou autres si nécessaire
        # elif item.is_dir():
        #     shutil.rmtree(item)
        #     logger.debug(f"Deleted old directory: {item.name}")
        #     cleaned_count += 1
    logger.info(f"Cleaned {cleaned_count} old PDF files from {pdfs_directory}")

def create_folder_structure(base_data_dir: str):
    """Create the required folder structure for scraped data."""
    base_path = Path(base_data_dir)
    # Only create the main pdfs folder as requested
    pdfs_folder = base_path / 'pdfs'
    pdfs_folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured directory exists: {pdfs_folder}")

def clean_filename(text, max_length=100):
    """Create a clean, safe filename from text."""
    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)
    # Replace problematic characters
    text = re.sub(r'[^\w\s\-_.]', '_', text)
    # Replace multiple spaces/underscores with single underscore
    text = re.sub(r'[\s_]+', '_', text)
    # Remove leading/trailing underscores
    text = text.strip('_')
    # Limit length
    if len(text) > max_length:
        text = text[:max_length].rsplit('_', 1)[0]
    return text

def download_pdf(pdf_url: str, filename: str, base_url: str, folder: str):
    """Download a PDF file from a URL to a specified folder."""
    try:
        # Make URL absolute if relative
        if not pdf_url.startswith(("http://", "https://")):
            pdf_url = urljoin(base_url, pdf_url)
        logger.info(f"Attempting to download PDF: {pdf_url}")

        response = requests.get(pdf_url, stream=True, timeout=30)
        response.raise_for_status()

        # Ensure folder exists
        Path(folder).mkdir(parents=True, exist_ok=True)

        # Clean and ensure .pdf extension
        clean_name = clean_filename(filename)
        if not clean_name.lower().endswith('.pdf'):
            clean_name += '.pdf'
        filepath = Path(folder) / clean_name

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Successfully downloaded: {filepath}")
        # --- Retourner un dictionnaire avec l'URL et le chemin local ---
        return {
            "original_url": pdf_url,
            "local_path": str(filepath.resolve()) # Chemin absolu pour éviter les problèmes
        }
    except Exception as e:
        logger.error(f"Error downloading PDF {pdf_url}: {e}")
        return None

def scrape_all_pdfs_on_results_page(page, base_url, download_folder='data/pdfs'):
    """Scrape and download all PDF links found on the results page."""
    logger.info("Starting to scrape all PDFs from the results page...")
    downloaded_files = []
    scraped_urls = []
    try:
        # Find ALL links ending with .pdf
        # We look within the main results section for better precision
        # The results are loaded into #fta-horz-list
        results_container = page.query_selector('#fta-horz-list')
        if not results_container:
            logger.warning("Results container #fta-horz-list not found. Searching entire page.")
            results_container = page
        
        pdf_links = results_container.query_selector_all('a[href$=".pdf"]')
        logger.info(f"Found {len(pdf_links)} PDF links on the results page.")

        for i, link in enumerate(pdf_links):
            try:
                href = link.get_attribute('href')
                link_text = link.inner_text().strip()
                
                if href:
                    # Use link text as filename base, or a generic name
                    filename_base = link_text if link_text else f"document_{i+1}"
                    logger.info(f"Downloading PDF {i+1}/{len(pdf_links)}: {filename_base}")
                    # --- Récupérer le résultat de download_pdf ---
                    download_result = download_pdf(href, filename_base, base_url, download_folder)
                    if download_result:
                        downloaded_files.append(download_result["local_path"])
                        # --- Stocker le lien original et le chemin local ---
                        scraped_urls.append(download_result)
                else:
                    logger.warning(f"PDF link {i+1} has no href attribute.")
            except Exception as e:
                logger.error(f"Error processing PDF link {i+1}: {e}")

        logger.info(f"Finished scraping PDFs. Total downloaded: {len(downloaded_files)}")
        return downloaded_files, scraped_urls

    except Exception as e:
        logger.error(f"An error occurred while scraping PDFs from the results page: {e}")
        return [], []
    
def click_non_pref_regime_checkbox(page):
    """
    Tente de cliquer sur la case 'Non-preferential regime' en s'assurant qu'elle est visible.
    """
    try:
        checkbox_selector = '#filter-nonPrefRoo'
        logger.info(f"Looking for 'Non-preferential regime' checkbox: {checkbox_selector}")
        
        # 1. Attendre que l'élément soit attaché au DOM
        page.wait_for_selector(checkbox_selector, state='attached', timeout=10000)
        checkbox = page.query_selector(checkbox_selector)
        
        if not checkbox:
            logger.warning("Checkbox element not found in the DOM after waiting.")
            return False

        logger.debug("Checkbox found in DOM.")

        # 2. Vérifier si déjà coché (gestion d'erreur autour de is_checked)
        try:
            if page.is_checked(checkbox_selector):
                logger.info("Checkbox 'Non-preferential regime' is already checked.")
                return True
        except Exception as e:
            logger.debug(f"Could not determine checkbox state with is_checked(): {e}. Proceeding.")

        # 3. S'assurer que le conteneur des filtres est visible
        # Le conteneur est '.filters .onoff'
        logger.debug("Ensuring filter container is visible...")
        filters_container = page.query_selector('.filters .onoff')
        if filters_container:
            # Cliquer sur le conteneur ou un élément à l'intérieur pour le rendre actif
            # Par exemple, cliquer sur le texte "Filters"
            filter_label = filters_container.query_selector('.lbl')
            if filter_label and filter_label.is_visible():
                filter_label.click()
                logger.debug("Clicked on 'Filters' label to ensure container is active.")
                page.wait_for_timeout(500) # Attendre un peu

        # 4. Défilement et focus
        logger.debug("Attempting to scroll checkbox into view and focus...")
        
        # a. Faire défiler l'élément dans le viewport (bloc central)
        page.evaluate("""element => element.scrollIntoView({block: 'center', inline: 'nearest'})""", checkbox)
        page.wait_for_timeout(1000) # Attendre le défilement
        
        # b. Forcer le focus sur la page/le body pour s'assurer que rien ne bloque
        page.evaluate("""document.body.focus()""")
        page.wait_for_timeout(500)
        
        # c. Forcer le focus sur l'élément lui-même
        page.evaluate("""element => element.focus()""", checkbox)
        page.wait_for_timeout(500)

        # 5. Vérifier la visibilité de l'élément
        if not checkbox.is_visible():
            logger.warning("Checkbox is still not visible after scroll and focus attempts.")
            # On peut essayer de cliquer sur le label associé comme dernier recours
            # Le label est le <label> parent de l'input
            label_selector = f'label:has(> input{checkbox_selector})'
            label = page.query_selector(label_selector)
            if label and label.is_visible():
                 logger.info("Found associated label, attempting to click it.")
                 label.click()
                 page.wait_for_timeout(2000)
                 return True
            else:
                 logger.error("Checkbox and its associated label are not visible.")
                 return False

        # 6. Tentative de clic avec plusieurs stratégies
        logger.debug("Attempting to click the checkbox...")
        
        # a. Clic forcé
        try:
            checkbox.click(force=True)
            logger.info("Checkbox clicked successfully with force=True.")
            page.wait_for_timeout(2000) # Attendre la mise à jour de l'UI
            return True
        except Exception as e:
            logger.debug(f"Force click failed: {e}")

        # b. Clic via JavaScript
        try:
            page.evaluate("element => { if (element && typeof element.click === 'function') element.click(); }", checkbox)
            logger.info("Checkbox clicked successfully via JavaScript.")
            page.wait_for_timeout(2000)
            return True
        except Exception as e:
            logger.debug(f"JavaScript click failed: {e}")

        logger.error("All click strategies for the 'Non-preferential regime' checkbox failed.")
        return False
            
    except TimeoutError as te:
        logger.error(f"Timeout while interacting with 'Non-preferential regime' checkbox: {te}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error interacting with 'Non-preferential regime' checkbox: {e}", exc_info=True)
        return False

def extract_mfn_duty(page):
    """
    Tente d'extraire les données de tarification MFN (Most Favoured Nation)
    après avoir activé le filtre 'Non-preferential regime'.
    """
    mfn_info = {
        "duties": [],
        "notes": []
    }
    try:
        logger.debug("Attempting to extract MFN duty information...")
        # Les données MFN sont souvent rendues via le template Handlebars dans #fta-horz-list
        # Nous devons trouver les éléments qui contiennent ces informations.
        
        # Cherchons les éléments de résumé qui pourraient contenir les tarifs
        summary_items = page.query_selector_all('#fta-horz-list .summary-items .s-i')
        
        if not summary_items:
             logger.info("No summary items found for MFN data.")
             mfn_info["notes"].append("No specific MFN duty items found in the summary.")
             # Il peut y avoir un message général
             no_results_msg = page.query_selector('#fta-horz-list .no-results')
             if no_results_msg:
                 msg_text = no_results_msg.inner_text().strip()
                 logger.info(f"No results message found: {msg_text}")
                 mfn_info["notes"].append(f"No results message: {msg_text}")
             return mfn_info

        for i, item in enumerate(summary_items):
            try:
                logger.debug(f"Analyzing summary item {i+1}/{len(summary_items)}")
                
                # Chercher le pourcentage du droit de douane
                # Il peut être dans un div avec une classe spécifique ou juste un div.text()
                percentage_element = item.query_selector('.number') # Essayons le sélecteur de la question
                if not percentage_element:
                    percentage_element = item.query_selector('.na-val') # Ou celui vu dans le HTML
                if not percentage_element:
                     # Si toujours pas, prenons le texte du premier div
                     percentage_element = item.query_selector('div')
                
                percentage_text = ""
                if percentage_element:
                    percentage_text = percentage_element.inner_text().strip()
                
                # Chercher le nom/type de droit
                name_element = item.query_selector('.name')
                name_text = ""
                if name_element:
                    name_text = name_element.inner_text().strip()
                
                # Assembler les données
                if percentage_text:
                    duty_info = {
                        "rate": percentage_text,
                        "type": name_text if name_text else "Unnamed Duty"
                    }
                    # Chercher des informations supplémentaires (comme "Highlight")
                    if 'highlight' in item.get_attribute('class').lower():
                        duty_info['note'] = "This rate might be highlighted for a specific reason."
                    
                    mfn_info["duties"].append(duty_info)
                    logger.debug(f"Found MFN duty: {duty_info}")
                else:
                     logger.debug(f"Summary item {i+1} did not contain a clear duty rate.")
                     
            except Exception as e:
                logger.warning(f"Error processing summary item {i+1}: {e}")

        if not mfn_info["duties"]:
             mfn_info["notes"].append("Analyzed summary items but could not extract specific duty rates.")
             logger.info("No specific MFN duties could be extracted from summary items.")

    except Exception as e:
        error_msg = f"Error extracting MFN data: {e}"
        logger.error(error_msg)
        mfn_info["notes"].append(error_msg)
    
    return mfn_info

def scrape_trade_pdfs(
    export_country: str = EXPORT_COUNTRY,
    import_country: str = IMPORT_COUNTRY,
    product_query: str = PRODUCT_QUERY,
    output_dir: str = "data"
):
    """
    Simplified scraping function using Playwright for the /compare page.
    1. Go to https://findrulesoforigin.org/en/home/compare  
    2. Fill Export (div.input.export), Import (div.input.import), Product (#product-list)
    3. Wait for results in #fta-horz-list to load
    4. If preferential agreements found, download PDFs.
    5. If no agreements, try to scrape MFN data.
    6. Save a mapping of original URLs to local paths.
    """
    # --- Validation des entrées ---
    if not export_country or not import_country or not product_query:
        logger.error(f"Invalid arguments for scraping: export='{export_country}', import='{import_country}', product='{product_query}'")
        error_msg_file = Path(output_dir) / "scraping_error.txt"
        error_msg_file.parent.mkdir(parents=True, exist_ok=True)
        with open(error_msg_file, 'w') as f:
            f.write(f"Scraping failed due to missing information: Exporter='{export_country}', Importer='{import_country}', Product='{product_query}'")
        return str(error_msg_file)
    
    logger.info(f"Starting simplified scraping for {export_country} -> {import_country} ({product_query})")
    create_folder_structure(output_dir)
    
    pdfs_output_dir = os.path.join(output_dir, 'pdfs')
    urls_mapping_file = os.path.join(output_dir, 'scraped_urls.json')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=0) 
        page = browser.new_page()

        try:
            compare_url = "https://findrulesoforigin.org/en/home/compare"
            logger.info(f"Navigating to compare page: {compare_url}")
            page.goto(compare_url, wait_until="domcontentloaded")

            # --- 2. Fill Export Country ---
            logger.info(f"Selecting export country: {export_country}")
            page.click("div.input.export .select2-selection")
            page.fill("div.input.export input.select2-search__field", export_country)
            page.wait_for_timeout(1000)
            page.keyboard.press("Enter")
            page.wait_for_selector("div.input.export .select2-selection__choice", timeout=3000)
            logger.info("Export country selected.")

            # --- 3. Fill Import Country ---
            logger.info(f"Selecting import country: {import_country}")
            page.click("div.input.import .select2-selection")
            page.wait_for_timeout(1500) 
            
            import_input_selectors = [
                "div.input.import input.select2-search__field",
                ".select2-container--open input.select2-search__field",
                "input.select2-search__field"
            ]
            
            search_input_import = None
            for selector in import_input_selectors:
                try:
                    search_input_import = page.query_selector(selector)
                    if search_input_import and search_input_import.is_visible():
                         logger.debug(f"Found import search input with selector: {selector}")
                         break
                except Exception as e:
                     logger.debug(f"Exception finding input with {selector}: {e}")
                     continue
            
            if not search_input_import:
                logger.error("Could not find the visible input field for import country search.")
                return urls_mapping_file
            else:
                logger.debug("Filling import country search input...")
                search_input_import.fill(import_country)
                page.wait_for_timeout(1500)

            # --- Select the Import Country Option ---
            logger.debug("Attempting to select the import country option from the dropdown...")
            try:
                page.wait_for_selector(".select2-results__option", timeout=3000)
                logger.debug("Dropdown options appeared.")
                
                option_clicked = False
                exact_option = page.query_selector(f".select2-results__option:text-is('{import_country}')")
                if exact_option:
                    logger.debug(f"Found exact match option: '{exact_option.inner_text().strip()}'")
                    exact_option.click()
                    option_clicked = True
                else:
                    logger.debug("No exact match found, searching for partial match...")
                    options = page.query_selector_all(".select2-results__option")
                    for option in options:
                        option_text = option.inner_text().strip()
                        if import_country.lower() in option_text.lower():
                            logger.debug(f"Clicking partial match option: '{option_text}'")
                            option.click()
                            option_clicked = True
                            break
                    
                if not option_clicked:
                    logger.warning("No matching option found by text. Clicking the first available option.")
                    first_option = page.query_selector(".select2-results__option")
                    if first_option:
                        first_option.click()
                        option_clicked = True
                    else:
                        raise Exception("No options available to click after dropdown appeared.")
                
                if option_clicked:
                    logger.info("Import country option selected.")
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(500)
                else:
                    raise Exception("Failed to click any option.")
                
            except TimeoutError:
                logger.error("Timeout waiting for import dropdown options to appear.")
                page.keyboard.press("Escape")
                return urls_mapping_file
            except Exception as select_e:
                logger.error(f"Error selecting import country option or closing dropdown: {select_e}")
                page.keyboard.press("Escape")
                return urls_mapping_file

            logger.info("Waiting for import selection to fully stabilize and dropdown to close...")
            page.wait_for_timeout(3000)

            # --- 4. Type Product/HS Code ---
            logger.info(f"Typing product / HS code: {product_query}")
            product_input = page.query_selector("#product-list")
            if product_input:
                product_input.fill(product_query)
                page.wait_for_timeout(1000)
            else:
                logger.error("Could not find product input field #product-list")
                return urls_mapping_file

            try:
                page.wait_for_selector("#ui-id-1 li", timeout=2000) 
                logger.debug("Autocomplete options appeared.")
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")
                logger.debug("Selected first autocomplete option.")
                page.wait_for_timeout(1000)
            except TimeoutError:
                logger.debug("No quick autocomplete detected or selected.")
                pass

            # --- 5. Wait for Results to Load (Initiale) ---
            logger.info("Waiting for initial results to load in #fta-horz-list...")
            page.wait_for_selector('#fta-horz-list', timeout=30000)
            page.wait_for_timeout(3000) 

            # ---  Vérifier le nombre d'accords ---
            logger.info("Checking the number of agreements found...")
            agreements_found = 0
            try:
                toggle_element = page.query_selector('div.found a.toggle')
                if toggle_element:
                    toggle_text = toggle_element.inner_text()
                    logger.debug(f"Toggle text found: '{toggle_text}'")
                    match = re.search(r'Total\s*(\d+)\s*Agreements', toggle_text)
                    if match:
                        agreements_found = int(match.group(1))
                        logger.info(f"Number of agreements found: {agreements_found}")
                    else:
                        logger.warning(f"Could not parse agreement count from text: '{toggle_text}'. Assuming 0.")
                else:
                    logger.warning("Toggle element for agreement count not found. Assuming 0 agreements.")
            except Exception as e:
                logger.error(f"Error while checking agreement count: {e}. Assuming 0 agreements.")
            
            pdfs_scraped = False
            scraped_urls = []
            mfn_data_extracted = {}

            # --- 6. Gestion des cas : Accords trouvés vs Non-préférentiel ---
            if agreements_found > 0:
                # --- 6a. Accords préférentiels trouvés : Scraping des PDFs ---
                logger.info("Agreements found. Initiating download of PDFs from the results page...")
                downloaded_files, scraped_urls = scrape_all_pdfs_on_results_page(page, compare_url, pdfs_output_dir)
                logger.info(f"Scraping process finished. Total PDFs downloaded to {pdfs_output_dir}: {len(downloaded_files)}")
                pdfs_scraped = True
            else:
                # --- 6b. Aucun accord trouvé : Activer le régime non-préférentiel ---
                logger.info("No preferential agreements found. Attempting to scrape non-preferential regime data...")
                try:
                    success = click_non_pref_regime_checkbox(page)
                    if success:
                        logger.info("Non-preferential regime activated. Waiting for data to load...")
                        page.wait_for_timeout(5000)
                        
                        mfn_data_extracted = extract_mfn_duty(page)
                        logger.info(f"Extracted MFN data: {mfn_data_extracted}")
                        
                        # Sauvegarder les données MFN dans un fichier
                        mfn_data_file = os.path.join(output_dir, 'mfn_data.json')
                        try:
                            with open(mfn_data_file, 'w') as f:
                                json.dump(mfn_data_extracted, f, indent=4, ensure_ascii=False)
                            logger.info(f"Saved MFN data to {mfn_data_file}")
                        except Exception as e:
                            logger.error(f"Failed to save MFN data to {mfn_data_file}: {e}")

                        pdfs_scraped = True
                    else:
                        logger.error("Failed to activate non-preferential regime. No data could be scraped.")
                        
                except Exception as e:
                    logger.error(f"Error handling non-preferential regime: {e}")

            # --- 7. Sauvegarder le mapping des URLs ---
            # Si aucun PDF n'a été scrapé mais que des données MFN le sont, on peut l'indiquer
            if not scraped_urls and mfn_data_extracted:
                 # Option : créer un fichier d'indication 
                 scraped_urls = [{"info": "No preferential PDFs found", "mfn_data_file": os.path.join(output_dir, 'mfn_data.json')}]

            try:
                with open(urls_mapping_file, 'w') as f:
                    json.dump(scraped_urls, f, indent=4, ensure_ascii=False)
                logger.info(f"Saved scraped URLs mapping to {urls_mapping_file}")
            except Exception as e:
                logger.error(f"Failed to save scraped URLs mapping to {urls_mapping_file}: {e}")

        except TimeoutError as e:
            logger.error(f"Timeout during scraping process: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during scraping: {e}", exc_info=True)
        finally:
            browser.close()
            logger.info("Browser closed.")

    return urls_mapping_file

def run_scraper():
    """Wrapper function to run the simplified scraper."""
    urls_mapping_file_path = scrape_trade_pdfs(EXPORT_COUNTRY, IMPORT_COUNTRY, PRODUCT_QUERY)
    logger.info(f"Scraper finished. URLs mapping file is at: {urls_mapping_file_path}")
    # Retourner le chemin du fichier pour qu'il puisse être utilisé ailleurs si besoin
    return urls_mapping_file_path

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    run_scraper()
