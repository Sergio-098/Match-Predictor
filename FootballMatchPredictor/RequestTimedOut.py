import requests
import time

url = 'https://fbref.com/en/comps/9/Premier-League-Stats'
response = requests.get(url)

if response.status_code == 403:
    print("Access forbidden. Your IP might be blocked.")
elif response.status_code == 429:
    print("Too many requests. You are being rate limited.")
else:
    print(f"HTTP Status Code: {response.status_code}")

if response.status_code == 429:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        print(f"Rate limited. Retry after {retry_after} seconds.")
        time.sleep(int(retry_after))
