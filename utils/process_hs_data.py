import json

def process_hs_data(input_filepath: str, output_filepath: str):
    """
    Reads the UN H6.json file, extracts id and description,
    and saves it to a new JSON file for faster loading/matching.
    """
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f_in:
            full_data = json.load(f_in)

        if not isinstance(full_data, dict) or 'results' not in full_data:
            print(f"Error: Unexpected format in {input_filepath}")
            return

        raw_hs_list = full_data['results']
        processed_data = []

        for item in raw_hs_list:
            item_id = item.get('id')
            full_text = item.get('text', '')
            # Only consider leaf nodes (most specific codes) for matching, if desired
            # is_leaf = item.get('isLeaf') == '1' # Optional filter

            # Extract description part (after the ' - ')
            description = full_text
            if ' - ' in full_text:
                description = full_text.split(' - ', 1)[1]

            # Optional: Filter out non-leaf items or aggregates if they are not useful for matching
            # if not is_leaf or item_id == "TOTAL":
            #     continue

            # Optional: Filter by aggregation level (aggrlevel 6 is quite specific)
            # if item.get('aggrlevel') != 6: # Or maybe <= 6 for a broader match
            #     continue

            if item_id and description: # Ensure we have both parts
                # Store as a dictionary or a tuple (description, id)
                processed_data.append({'id': item_id, 'description': description})
                # Or simpler: processed_data.append((description, item_id))

        # Save the processed data
        with open(output_filepath, 'w', encoding='utf-8') as f_out:
            json.dump(processed_data, f_out, indent=4) # Use indent for readability

        print(f"Processed {len(raw_hs_list)} raw entries into {len(processed_data)} usable entries.")
        print(f"Saved processed data to {output_filepath}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_filepath}' not found.")
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from '{input_filepath}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    INPUT_FILE = "data/json/H6.json"
    OUTPUT_FILE = "data/json/hs_code_descriptions.json"
    process_hs_data(INPUT_FILE, OUTPUT_FILE)
