import requests

def download_file(url, filename):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded {filename} successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")

if __name__ == "__main__":
    url = "https://comtradeapi.un.org/files/v1/app/reference/H6.json"
    filename = "data/json/H6.json"
    download_file(url, filename)