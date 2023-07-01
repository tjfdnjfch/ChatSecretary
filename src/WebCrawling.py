class WebCrawling:
    def __init__(self, url):
        if 'bizinfo.go.kr' not in url:
            print('url을 확인해주세요.')
            return
        import requests
        from bs4 import BeautifulSoup
        self.url = url

        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')
        self.soup = soup

        # 분류
        self.category = soup.find('div', "title_area").find('span', "c-blue").getText()

        # 공고 제목
        self.title = soup.find('div', "title_area").find('h2', "title").getText()

        # 태그
        self.tags = [i.getText() for i in soup.find('div', "tag_list").find_all('span')]


    def infos(self, key = None):
        import re

        pageinfo = self.soup.find('div', "view_cont").find('ul')
        keys = [i.getText() for i in pageinfo.find_all('span', "s_title")]
        temp = [i.find_all('div', "txt",recursive=False) for i in pageinfo.find_all('li')]
        values = [re.sub(' +', ' ', i[0].getText("\n").strip().replace('\r\n', '')) for i in temp if i]

        
        if len(keys) != len(values):
            raise RuntimeError('something wrong')
        infos = {key:value for key,value in zip(keys, values)}
        if key in keys:
            return infos[key]
        elif key == None:
            return infos
        else:
            raise RuntimeError(f'{self.title} 페이지에서 {key} 속성을 찾지 못하였습니다.')

    def attachment(self, download=True, folder=None):
        from urllib.request import urlretrieve
        soup = self.soup
        url = self.url
        file_names=[i.getText() for i in soup.find('div', "attached_file_list").find_all('div', "file_name")]
        file_links=[i.get('href') for i in soup.find('div', "attached_file_list").find_all('a', target="_blank")]
        if len(file_names) != len(file_links):
            raise RuntimeError('something wrong')
        if download:
            for name, link in zip(file_names, file_links):
                a = f"{url[-6:]}_{name}"
                b = 'https://www.bizinfo.go.kr'+link
                if folder:
                    import os
                    a = os.path.join(folder, a)

                print(f'download : {a[:20]}...', end=' ')
                urlretrieve(b, a)
                print(': complete')
            return
        else:
            return dict({key:value for key,value in zip(file_names, file_links)})