import urllib.request
from bs4 import BeautifulSoup

def getBiggestMovers(quantity, url, type='gainers'):

        if type != "gainers" and type != "losers":
                return None

        movers = {}

        response = urllib.request.urlopen(url+type)

        if response.getcode() != 200:
                print("Can't contact {}".format(url))
                return

        soup = BeautifulSoup(response, 'lxml')

        table = soup.find_all("tbody", {"class" : "tv-data-table__tbody"})

        for t in table:

                entries = t.find_all("tr")

                for entry in entries[:quantity]:

                        items = entry.find_all("td")
                        symbol = items[0].find("div").find("a").getText()
                        percent = items[2].getText()

                        try:
                                if type == "gainers":
                                        percent = float(percent[:-1])
                                else:
                                        percent = -float(percent[1:-1])
                                movers[symbol] = percent

                        except Exception:
                                print(Exception)

        return movers
