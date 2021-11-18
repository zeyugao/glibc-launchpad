import requests
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor
import logging

codenames = ['trusty', 'xenial', 'bionic', 'focal']
archs = ['amd64', 'i386']

pattern = re.compile('([0-9.]+)-([0-9]+)ubuntu([0-9.]+)')


def get_proxy():
    return requests.get("http://127.0.0.1:5010/get/").json()


def delete_proxy(proxy):
    requests.get("http://127.0.0.1:5010/delete/?proxy={}".format(proxy))


def get_resp(url):
    proxy = get_proxy().get("proxy")
    retry_count = 5
    while retry_count > 0:
        try:
            resp = requests.get(url,
                                proxies={
                                    "http": f"http://{proxy}",
                                    "https": f"http://{proxy}",
                                }, timeout=3)

            return resp
        except Exception:
            retry_count -= 1
    delete_proxy(proxy)
    return None


def always_retry(url):
    while True:
        resp = get_resp(url)
        if resp is None:
            logging.error('retry')
        else:
            return resp


def get_downloadable_file(url):
    url = 'https://launchpad.net' + url
    r = always_retry(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    link = soup.find('div', {'id': 'downloadable-files'}).find('a')
    print(link.text, link.get('href'))
    filename = link.text
    filelink = link.get('href')
    return filename, filelink


def download(codename, arch):
    version = {}

    try:
        for pkg in ['libc6', 'libc6-dbg']:
            print(codename, arch, pkg)
            url = f'https://launchpad.net/ubuntu/{codename}/{arch}/{pkg}'
            content = always_retry(url).text

            soup = BeautifulSoup(content, 'html.parser')
            table = soup.find(
                'table', {'class': 'listing', 'id': 'publishing-summary'})
            tbody = table.find('tbody')

            all_link = tbody.find_all('a')
            for link in all_link:
                match = pattern.match(link.text)
                if match:
                    print(link.text)
                    filename, link = get_downloadable_file(
                        link.get('href'))
                    version[filename] = link
    except Exception as e:
        print(codename, arch, e)

    print(codename, arch, 'end')
    with open(f'list-{codename}-{arch}', 'w') as f:
        for k, v in version.items():
            f.write(f'{k} {v}\n')


with ThreadPoolExecutor(max_workers=len(codenames) * len(archs)) as executor:
    for codename in codenames:
        for arch in archs:
            executor.submit(download, codename, arch)
