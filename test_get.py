import os
import requests
import json

JULES_API_KEY = os.environ.get("JULES_API_KEY")
SESSION_ID = "250730695216863293"

headers = {
    "x-goog-api-key": JULES_API_KEY
}

# 1. Try GET on the session itself
url1 = f"https://jules.googleapis.com/v1alpha/sessions/{SESSION_ID}"
print(f"GET {url1}")
resp1 = requests.get(url1, headers=headers)
print(resp1.status_code)
if resp1.status_code == 200:
    print(list(resp1.json().keys()))
else:
    print(resp1.text)

# 2. Try GET on the activities
url2 = f"https://jules.googleapis.com/v1alpha/sessions/{SESSION_ID}/activities"
print(f"\nGET {url2}")
resp2 = requests.get(url2, headers=headers)
print(resp2.status_code)
if resp2.status_code == 200:
    print(list(resp2.json().keys()))
else:
    print(resp2.text)
