import uuid
import time
import json
import configparser
import os
import requests


config = configparser.ConfigParser()
config.read("./src/api key.ini")

api_url = config['ocr']['api_url']
secret_key = config['ocr']['secret_key']


def imgs_extractor(imgsList):
    for img in imgsList:
        file_basename = os.path.splitext(os.path.basename(img))[0]

        files = [('file', open(img,'rb'))]

        request_json = {'images': [{'format': 'jpg',
                                        'name': 'demo'
                                    }],
                            'requestId': str(uuid.uuid4()),
                            'version': 'V2',
                            'timestamp': int(round(time.time() * 1000))
                        }
        
        payload = {'message': json.dumps(request_json).encode('UTF-8')}
        
        headers = {
        'X-OCR-SECRET': secret_key,
        }
        
        response = requests.request("POST", api_url, headers=headers, data=payload, files=files)
        result = response.json()


        fulltext = []
        for field in result['images'][0]['fields']:
            textpiece = field['inferText']
            fulltext.append(textpiece)
        text = ' '.join(fulltext)
        
        text = '\n'.join([i for i in text.split("\n") if len(set(i))>1])
        savetxt = os.path.join('./attachments','texts',f"{file_basename}.txt".split('/')[-1])
        f = open(savetxt,'w', encoding='utf-8')
        f.write(text)
        f.close()
    return