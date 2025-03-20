from flask import Flask, request, jsonify
import requests
import os
import sys
from bs4 import BeautifulSoup

app = Flask(__name__)

# Log startup info
print("Starting Flask application...", file=sys.stderr)
print(f"Python version: {sys.version}", file=sys.stderr)
print("Flask module loaded successfully", file=sys.stderr)

# Configuration
DOWNLOADER_URL = "https://allinonedownloader.com/system/9aa30e91d1faf74.php"
BASE_URL = "https://allinonedownloader.com/"
BURKUL_URL = "https://burkul.com/crs.php?ck=0&ref=https%3A%2F%2Fallinonedownloader.com%2F&rex=https%3A%2F%2Fwww.google.com%2F&tt=769x721&_=1742439524793"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "dnt": "1",
    "origin": "https://allinonedownloader.com",
    "priority": "u=1, i",
    "referer": "https://allinonedownloader.com/",
    "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
    "cache-control": "no-cache",
    "pragma": "no-cache"
}

BURKUL_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "dnt": "1",
    "origin": "https://allinonedownloader.com",
    "priority": "u=1, i",
    "referer": "https://allinonedownloader.com/",
    "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36"
}

def fetch_session_data():
    """Fetch cookies and CSRF token for session creation"""
    session = requests.Session()
    try:
        # Step 1: Fetch cookies from burkul.com
        burkul_response = session.get(BURKUL_URL, headers=BURKUL_HEADERS)
        print(f"Burkul response status: {burkul_response.status_code}", file=sys.stderr)
        print(f"Burkul cookies: {session.cookies.get_dict()}", file=sys.stderr)

        # Step 2: Fetch the main page to get additional cookies and CSRF token
        base_response = session.get(BASE_URL, headers=HEADERS)
        print(f"Base page response status: {base_response.status_code}", file=sys.stderr)
        cookies = session.cookies.get_dict()
        print(f"Combined cookies: {cookies}", file=sys.stderr)

        # Parse HTML for CSRF token
        soup = BeautifulSoup(base_response.text, 'html.parser')
        csrf_token = None
        meta_token = soup.find('meta', {'name': 'csrf-token'})
        if meta_token and meta_token.get('content'):
            csrf_token = meta_token['content']
        else:
            input_token = soup.find('input', {'name': 'csrf_token'}) or soup.find('input', {'name': '_token'})
            if input_token and input_token.get('value'):
                csrf_token = input_token['value']
        print(f"CSRF token found: {csrf_token}", file=sys.stderr)

        return cookies, csrf_token
    except Exception as e:
        print(f"Error fetching session data: {str(e)}", file=sys.stderr)
        return {}, None

@app.route('/fetch-download', methods=['POST'])
def fetch_download():
    print("Received request to /fetch-download", file=sys.stderr)
    instagram_url = request.json.get('url') if request.json else None
    if not instagram_url:
        return jsonify({"error": "No URL provided in JSON body"}), 400

    # Fetch session data
    cookies, csrf_token = fetch_session_data()
    if not cookies:
        print("Using default cookies due to fetch failure", file=sys.stderr)
        cookies = {"PHPSESSID": os.getenv("PHPSESSID", "6eec447900df04afe0bda14b1fc6fe51")}

    payload = {
        "url": instagram_url,
        "token": os.getenv("DOWNLOADER_TOKEN", "13f7110858ce1449a6a77592fd3a827d45622ecea97bfb2ed78a6c2484bf054d"),
        "urlhash": os.getenv("DOWNLOADER_URLHASH", "Vz3+I1TBsKviPT64o0GtBoKOHe4X2FJjr3XV55cnfJOR8bkwofyDt0X9LCOdRCQotoZIiq3C1M74ynJPOm8//6xxi+aXtjuCSfqFM13lW3c=")
    }
    if csrf_token:
        payload["csrf_token"] = csrf_token  # Adjust key if needed

    try:
        session = requests.Session()
        if csrf_token:
            HEADERS["X-CSRF-Token"] = csrf_token  # Add to headers if required
        response = session.post(DOWNLOADER_URL, headers=HEADERS, cookies=cookies, data=payload)
        print(f"Downloader response status: {response.status_code}", file=sys.stderr)
        print(f"Downloader response text: {response.text}", file=sys.stderr)
        if response.status_code == 200:
            data = response.json()
            return jsonify(data), 200
        else:
            return jsonify({"error": f"Failed to fetch data from downloader: {response.status_code}", "details": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": "An error occurred", "details": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    print("Received request to /", file=sys.stderr)
    return jsonify({"message": "Welcome to the Downloader API", "endpoint": "/fetch-download"}), 200

@app.route('/health', methods=['GET'])
def health_check():
    print("Received request to /health", file=sys.stderr)
    return jsonify({"status": "healthy"}), 200

@app.route('/test', methods=['GET'])
def test():
    print("Received request to /test", file=sys.stderr)
    return jsonify({"message": "Server is running", "routes": ["/", "/fetch-download", "/health", "/test"]}), 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    print(f"Flask app running on port {port}", file=sys.stderr)
    app.run(host='0.0.0.0', port=port, debug=False)
