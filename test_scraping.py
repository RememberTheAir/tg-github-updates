import requests
from html import escape
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options
from lxml import html

URL = 'https://install.appcenter.ms/users/drklo-2kb-ghpo/apps/telegram-beta-2/distribution_groups/all-users-of-telegram-beta-2'


def old():
    page_content = requests.get(URL)

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


def main(selected_webdriver='pjs'):
    # AppCenter requires JS enabled so we have to use selenium and simulate a browser request

    version_xpath_ff = '/html/body/div[2]/div/div/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/div[2]/div/div/div[1]/div[1]'
    version_xpath_chromium = '//*[@id="app"]/div/div/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/div[2]/div/div/div[1]/div[1]/text()[2]'
    version_xpath_chromium_full = '/html/body/div[2]/div/div/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/div[2]/div/div/div[1]/div[1]'
    version_class_name = '_1qjHBJYex _19ynaVUpx _634PiScnx _1vGSY6Fax l1LdMrFBx _74rbA585x _1id30tvgx'

    if selected_webdriver == 'ff':
        print('FIREFOX DRIVER')

        # https://stackoverflow.com/a/40931903
        firefox_capabilities = DesiredCapabilities.FIREFOX
        firefox_capabilities['marionette'] = True

        # https://towardsdatascience.com/data-science-skills-web-scraping-javascript-using-python-97a29738353f
        chrome_options = Options()
        chrome_options.headless = True

        # https://stackoverflow.com/a/42122284
        driver = webdriver.Firefox(executable_path=r'./geckodriver.exe', capabilities=firefox_capabilities, firefox_options=chrome_options)
    elif selected_webdriver == 'chr':
        print('CHROME DRIVER')

        # https://selenium-python.readthedocs.io/api.html#module-selenium.webdriver.chrome.webdriver
        chrome_options = webdriver.ChromeOptions()
        chrome_options.headless = True
        driver = webdriver.Chrome(executable_path='./chromedriver.exe', chrome_options=chrome_options)
    else:  # pjs: phantomJS
        # phantomJS is deprecated, but it works (headless firefox doesn't)
        print('PHANTOMJS DRIVER')

        # https://towardsdatascience.com/data-science-skills-web-scraping-javascript-using-python-97a29738353f
        driver = webdriver.PhantomJS(executable_path='./phantomjs.exe')

    driver.get(URL)

    by_xpath = driver.find_elements_by_xpath(version_xpath_chromium)
    print('by xpath:\n', by_xpath)

    by_tag_name = driver.find_elements_by_tag_name('div')
    print('by tag name:\n', by_tag_name)
    print('\n'.join(dir(by_tag_name[0])))
    print([e.text for e in by_tag_name])

    by_class = driver.find_elements_by_class_name(version_class_name)
    print('by class:\n', by_class)

    # page_html = driver.page_source
    # soup = BeautifulSoup(page_html, features='html.parser')
    # print(soup.prettify())

    # _1qjHBJYex _19ynaVUpx _634PiScnx _1vGSY6Fax l1LdMrFBx _74rbA585x _1id30tvgx

    # matches = soup.find_all("div")
    # print(matches)

    # /html/body/div[1]/div[2]/div/div[1]/div/div[3]/div[6]/h3
    # /html/body/div[1]/div[2]/div/div[1]/div/div[3]/div[6]/div[1]/a

    # download_url = tree.xpath('/html/body/div[2]/div/div/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/div[2]/div/div/div[1]/div[1]')
    # print([print(dir(i)) for i in download_url])
    # print(download_url[0].values()[1])

    # /html/body/div[2]/div/div/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/div[2]/div/div/div[1]/div[1]


if __name__ == '__main__':
    main()
