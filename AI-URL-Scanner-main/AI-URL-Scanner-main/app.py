import shutil
import zipfile
import urllib3
import validators
import os
from time import sleep
from taipy.gui import Gui
import pandas as pd
import base64
import requests
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file

api_key  = os.getenv('OPENAI_API_KEY')

content = ""
url_data = pd.DataFrame()

index = """
<|text-center|  
## Bibliophile AI
Extract URL from any image. Make sure the URLs in the image(s) are readable.


#### 1. Select image(s) from your device.
Single Image / Multiple Images / Zip file <br/><br/>
<|{content}|file_selector|multiple|label=Upload Image(s)|extensions=.png,.jpg,.jpeg,.zip|>    

#### 2. Extract URLs from the selected image(s) using AI
<|Extract Links|button|on_action=extract_links|>

#### Links from the given image(s): 
<center><|{url_data}|table|rebuild=True|width=65%|>
</center>
>   
"""

df = pd.DataFrame(columns=['File Name', 'URL(s)', 'Status'])

def is_url_working(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        if response.status_code == 200:
            return True
        else:
            return False
    except requests.RequestException as e:
        return False
    except urllib3.exceptions.NewConnectionError as n:
        return False

def encode_image(image_path):   # UTF-8 Encoding
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

def get_from_chatgpt(base64_image):
    # Sending API request to chatGPT4 vision to extract URL(s) from the given image and send the response in 
    # comma separated values for further processing
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
    }

    payload = {
    "model": "gpt-4-vision-preview",
    "messages": [
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": "Extract and list only the URL(s) from the given image separated by commas \
                    without mentioning anything else."
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
            }
        ]
        }
    ],
    "max_tokens": 300
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()['choices'][0]['message']['content']
        
def update_url_dataframe(image_path, url_string):
    # Remove spaces and split into list
    urls = []
    url_found = False
    for url in url_string.split(','):
        urls.append(url.strip())

    file_name = str(os.path.basename(image_path.encode('unicode_escape')))[2:-1]

    # Updating dataframe
    for url in urls:
        if validators.url(url):
            if is_url_working(url):
                df.loc[len(df.index)] = [file_name, url, "Valid"]
            elif url.lower().endswith('pdf'):
                df.loc[len(df.index)] = [file_name, url, "Unsure"]
            else:
                df.loc[len(df.index)] = [file_name, url, "Invalid"]
            url_found = True
    
    if not url_found:
        df.loc[len(df.index)] = [file_name, "No URL found in the image", ""]
            
def extract_from_zip(path):
    from_zip_path = path
    extract_to_directory = r"C:\Users\krish\AppData\Local\Temp\bibliophile ai"
    
    # Delete Temp folder if already exists
    if os.listdir(extract_to_directory) and len(os.listdir(extract_to_directory)) != 0:
        shutil.rmtree(extract_to_directory)
    
    # Extracting zip file to the directory
    with zipfile.ZipFile(from_zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to_directory)


    # Adding all the file directories to image_list
    image_list = []
    image_found = False
    for root, dirs, files in os.walk(extract_to_directory):
        for file in files:
            if file.lower().endswith(('png', 'jpg', 'jpeg')):
                image_list.append(os.path.join(root, file))
                image_found = True
                
        if not image_found:
            print('No images in the directory')
        
    # Extracting links from the images in the zip file
    extract_links(url_list=image_list)

def extract_links(state=None, image_list=None):
    # dropping existing links from the dataframe
    df.drop(df.index, inplace=True)
    
    if image_list:
        user_upload = image_list
    else:
        user_upload = state.content
    
    # For multiple files upload
    if type(user_upload) == list:
        delay = 20
        for i in range(len(user_upload)):
            image_path = user_upload[i]
            base64_image = encode_image(image_path)
            url_string = get_from_chatgpt(base64_image)
            update_url_dataframe(image_path, url_string)
                
            sleep(delay)
            
    # For zip file upload
    elif user_upload.endswith('zip'):
        zip_path = str(user_upload)
        extract_from_zip(zip_path)
         
    # For single file upload   
    else:
        image_path = user_upload
        base64_image = encode_image(image_path)
        url_string = get_from_chatgpt(base64_image)
        update_url_dataframe(image_path, url_string)

    state.url_data = df    
    
    
Gui(page=index).run(use_reloader=True)