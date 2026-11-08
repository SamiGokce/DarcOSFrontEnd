import os
import requests

# Read your API token from the environment (REPLICATE_API_TOKEN); never hardcode it.
API_TOKEN = os.environ.get('REPLICATE_API_TOKEN')
if not API_TOKEN:
    raise SystemExit('Set REPLICATE_API_TOKEN in your environment first.')

# Set the URL for the upload endpoint
upload_url = 'https://replicate.delivery/api/v1/upload'

# Set the path to your image file
image_path = 'images/mekkana-9-10.png'

# Read the image file
with open(image_path, 'rb') as file:
    image_data = file.read()

# Set the headers with your API token
headers = {
    'Authorization': f'Bearer {API_TOKEN}',
    'Content-Type': 'application/octet-stream'
}

# Make the POST request to upload the image
response = requests.post(upload_url, headers=headers, data=image_data)

# Check the response
if response.status_code == 200:
    print("Image uploaded successfully!")
    print(f"Image URL: {response.json()['url']}")
else:
    print(f"Failed to upload image: {response.status_code} - {response.text}")
