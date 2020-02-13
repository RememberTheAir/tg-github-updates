import requests

from lxml import html


def main():
    page_content = requests.get('https://rink.hockeyapp.net/apps/f972660267c948d2b5d04761f1c1a8f3')
    tree = html.fromstring(page_content.content)

    # /html/body/div[1]/div[2]/div/div[1]/div/div[3]/div[6]/h3
    # /html/body/div[1]/div[2]/div/div[1]/div/div[3]/div[6]/div[1]/a
    download_url = tree.xpath('/html/body/div[1]/div[2]/div/div[1]/div/div[3]/div[6]/div[1]/a')
    # print([print(dir(i)) for i in download_url])
    print(download_url[0].values()[1])

    # /html/body/div[1]/div[2]/div/div[1]/div/div[3]/div[6]/h3
    version = tree.xpath('/html/body/div[1]/div[2]/div/div[1]/div/div[3]/div[6]/h3')
    print(version[0].text)
    print('\n'.join(dir(version[0])))


if __name__ == '__main__':
    main()
