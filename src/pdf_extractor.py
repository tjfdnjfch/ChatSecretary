import tika
tika.initVM()


import os
import fitz
from tqdm import tqdm
import re
from tika import parser
from IPython.display import clear_output
import pandas as pd
import numpy as np
import uuid
import unicodedata
import json
import time
import requests
import configparser
import glob






config = configparser.ConfigParser()
config.read("./src/api key.ini")

api_url = config['ocr']['api_url']
secret_key = config['ocr']['secret_key']



def fullhalfsize(char):
    if unicodedata.east_asian_width(char) in ['W','F']:
        return 2
    else:
        return 1

class spellchecker:
    def __init__(self, text):
        import requests
        import json
        orgStr = text
        text = text.replace('\n', '\r\n').replace('\r\r\n', '\r\n')
        while True:
            try:
                response = requests.post('http://164.125.7.61/speller/results', data={'text1': text})
                break
            except:
                print('호스트 응답을 기다리는 중입니다.')
                time.sleep(5)
        
        if response.status_code == 400:
            self.help = '맞춤법 검사기에 입력할 수 없는 문구입니다.'
            
            self.candWord = ' '.join(re.findall('[가-힣]+',orgStr))
            self.orgStr = orgStr
            self.collect = orgStr.replace(self.orgStr, self.candWord)
            self.iscollect = False
            return
            
            



        data = response.text.split('data = [', 1)[-1].rsplit('];', 1)[0]
        if "맞춤법과 문법 오류를 찾지" in response.text:
            self.help = '오류는 없습니다.'
            self.candWord = orgStr
            self.orgStr = orgStr
            self.collect = orgStr
            self.iscollect = True
        else:
            data = json.loads(data)
            data_info = data['errInfo'][0]
            self.help = data_info['help']
            self.candWord = data_info['candWord']
            self.orgStr = data_info['orgStr']
            if self.orgStr.replace(' ','') == self.candWord.replace(' ',''):
                self.collect = orgStr.replace(self.orgStr, self.candWord)
                self.iscollect = False
            else:
                self.collect = orgStr
                self.iscollect = True
        return
    
    
    
def pdf_extractor(file):
    
    file_basename = os.path.splitext(os.path.basename(file))[0]

    if not os.path.exists(os.path.join("./attachments_process", file_basename)):
        os.makedirs(os.path.join("./attachments_process", file_basename))
    else:
        files = glob.glob(f'./attachments_process/{file_basename}/*')
        for f in files:
            os.remove(f)
        

    raw = parser.from_file(file)
    if raw['content']:
        text = re.sub("\n+", "\n", raw['content'], count=0, flags=0).replace("PowerPoint 프레젠테이션", "")

        text = re.sub(r"^ⓒ.*PowerPoint$", "", text, flags=re.MULTILINE).strip("\n")

        text = '\n'.join([i for i in text.split('\n') if i.split(' ')])

        clear_output(wait=True)

        newtext_list = []

        for i in text.split('\n'):
            if len(i) == 0:
                pass
            elif (i.strip().count(' ') / (len(i)) > 0.3):
                sc = spellchecker(i.replace(' ',''))
                if sc.iscollect:
                    newtext_list.append(i)
                else:
                    newtext_list.append(sc.collect)
            else:
                newtext_list.append(i)

        text = '\n'.join(newtext_list)



        text_split = np.array(text.split('\n'))

        text_split_lengths = [sum(fullhalfsize(i) for i in t) for t in text.split('\n')]
        if len(text_split) < 5:
            minlength = np.float64(0)
        else:
            try:
                lengths =  np.array(text_split_lengths)
                lengths = lengths[lengths < np.quantile(lengths, 0.9)]
                minlength = np.quantile(lengths, 0.8)-15
            except:
                minlength = np.float64(max(text_split_lengths)-15)



        df = []

        for i, value in enumerate(minlength <= text_split_lengths):
            df.append([i,value, text_split[i]])

        df = pd.DataFrame(df, columns=['lineno', 'pre_filtered', 'text'])
        df['next_text'] = df.text.shift(-1, fill_value='')

        Asfront_1 = df.apply(lambda row: re.fullmatch('[가-힣]+',row['text'].split()[-1]) if row['text'].split() else None , axis=1)
        Asfront_2 = df.apply(lambda row: re.fullmatch('[가-힣]+',row['next_text'].split()[0]) if row['next_text'].split() else None , axis=1)
        Asfront = df.pre_filtered & Asfront_1.astype('bool') & Asfront_2.astype('bool')


        df['Asfront0'] = Asfront_1.astype('bool') & df.apply(lambda row: re.fullmatch('[가-힣]+[,|.]?',row['next_text'].split()[0]) if row['next_text'].split() else None , axis=1).astype('bool')

        df['Asfront'] = (Asfront_1.apply(lambda x: x.group() if x else '')+Asfront_2.apply(lambda x: x.group() if x else ''))[Asfront].apply(lambda x: spellchecker(x).iscollect if x else False)
        df.Asfront = df.Asfront.fillna(False)

        task1 = list(df[df.Asfront].lineno)
        task2 = list(df[(~df.Asfront&df.pre_filtered&df.Asfront0)].lineno)
        task3 = list(df[~(df.Asfront|df.pre_filtered|~df.Asfront0)].lineno)

        text = ''.join([text+('' if i in task1 else (' ' if i in task2 else '\n')) for i, text in enumerate(text.split('\n'))]).rstrip('\n')
    else:
        text = ''

    doc = fitz.Document(file)
    imageno = 0

    for i in tqdm(range(len(doc)), desc="pages"):
        for img in tqdm(doc.get_page_images(i), desc="page_images"):
            imageno += 1
            xref = img[0]
            image = doc.extract_image(xref)
            pix = fitz.Pixmap(doc, xref)
            pix.save(os.path.join("./attachments_process", file_basename, f"Image{str(imageno).zfill(5)}.jpg"))

    files = glob.glob("./attachments_process/*")
    for files in glob.glob("./attachments_process/*"):
        for f in glob.glob(f"{files}/*"):
            if os.stat(f).st_size < 10000:
                os.remove(f)
    

    for imgfile in sorted(os.listdir(os.path.join("./attachments_process", file_basename))):
        path = os.path.join("./attachments_process", file_basename, imgfile)
        files = [('file', open(path,'rb'))]


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
        fulltext_join = ' '.join(fulltext)
        text = '\n'.join([text, fulltext_join])

    if not os.path.exists(os.path.join("./attachments", 'texts')):
        os.makedirs(os.path.join("./attachments", 'texts'))

    text = '\n'.join([i for i in text.split("\n") if len(set(i))>1])
    savetxt = os.path.join('./attachments','texts',f"{file_basename}.txt".split('/')[-1])
    f = open(savetxt,'w', encoding='utf-8')
    f.write(text)
    f.close()
        
    return