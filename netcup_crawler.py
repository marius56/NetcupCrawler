#!/usr/bin/env python3
import requests
import re
import os
import time
import urllib
import argparse
import apprise

##############################| Settings |##############################
search_for_offer = "VPS Ostern L"  # specify a offer to search for
amount_msgs = 2  # amount of message you will receive if your offer is found

telegram_use = False
telegram_bot_token = "123123:AAAABBBCCC..."
telegram_chat_id = "123456"

matrix_use = False
matrix_server = "example.com"
matrix_room_id = "!IfRoFlDuvAxOwyDljT"
matrix_user = "username"
matrix_password = "password"

# _____________________________| Settings |______________________________

# Create apprise notification object
apobj = apprise.Apprise()

new_urls = ["https://www.netcup.de"]
scanned_urls = []

url_re = re.compile(
    r"https?:\/\/(?!forum\.)[-_a-zA-Z0-9]*\.?netcup\.de[-a-zA-Z0-9@:%&._+~#=\/?]*"
)
exclude_files__re = re.compile(r"(\.js|\.css)\??")


def send_msg(message):  # send a message via a telegram bot
    if telegram_use:
        apobj.add(f"tgram://{telegram_bot_token}/{telegram_chat_id}", tag="telegram")
        apobj.notify(body=f"{message}", tag="telegram")

    if matrix_use:
        apobj.add(
            f"matrixs://{matrix_user}:{matrix_password}@{matrix_server}/{matrix_room_id}",
            tag="matrix",
        )
        apobj.notify(body=f"{message}", tag="matrix")


def parse_response(response, url_file):
    global new_urls
    global scanned_urls

    urls_found = url_re.findall(response.text)

    for url in urls_found:
        if "/wp-json/oembed/" in url:  # skipping requests to the api
            continue

        if url.endswith("?"):
            url = url[:-1]  # remove a tailing ?

        if url.endswith("/"):
            url = url[:-1]  # remove a tailing /

        if url not in new_urls and url not in scanned_urls:
            if (
                exclude_files__re.search(url) != None
                or "product.php" in url
                or "warenkorb_add.php" in url
            ):  # skip .js and .css files
                # print(f"Skipping url: {url}")
                continue
            else:
                print(f"Found new url: {url}")
                url_file.write(f"{url}\n")
                new_urls.append(url)


def crawl_urls():
    with open("./urls.txt", "w") as url_file:
        while len(new_urls) > 0:
            temp_new_urls = new_urls  # new urls will be added to new_urls. To prevent changes to the list while iterating
            # a temp variable is used
            for url in temp_new_urls:
                try:
                    response = requests.get(url)
                except Exception as e:
                    print(f"Error: {e}")

                parse_response(response, url_file)

                new_urls.remove(url)
                scanned_urls.append(url)


def check_pages():
    with open("./urls.txt", "r") as url_file:
        with open("./offers.csv", "w") as offer_file:
            offer_file.write("Titel,Price,URL") # add the column titels for the .csv file

            for url in url_file.readlines():
                url = url[:-1].replace(
                    "https://www.netcup.de/", ""
                )  # remove \n at the end
                response = requests.post(
                    "https://www.netcup.de/api/eggs", files={"requrl": (None, url)}
                )

                json_resp = response.json()

                if "eggs" in json_resp:
                    if json_resp["eggs"] == False:  # no egg found
                        continue

                    for egg in json_resp["eggs"]:
                        offer_file.write(
                            f"\n\"{egg['title']}\",\"{egg['price'].replace(',', '.').replace('&euro;', '€')} {egg['price_text']}\",https://www.netcup.de/bestellen/produkt.php?produkt={egg['product_id']}&hiddenkey={egg['product_key']}"
                        )
                        print(
                            f"{egg['title']} ({egg['price'].replace(',', '.').replace('&euro;', '€')} {egg['price_text']}): https://www.netcup.de/bestellen/produkt.php?produkt={egg['product_id']}&hiddenkey={egg['product_key']}"
                        )

                        # If you are looking for something, specify the name and you will get a telegram message when its found
                        if (
                            search_for_offer in egg["title"]
                        ):  # e.g. --> if "VPS Ostern L" in egg["title"]:
                            offer_url = f"https://www.netcup.de/bestellen/produkt.php?produkt={egg['product_id']}&hiddenkey={egg['product_key']}"
                            response = requests.get(offer_url)

                            if (
                                "Produkt nicht verf" not in response.text
                            ):  # check if the product is still available
                                if telegram_use or matrix_use:
                                    for x in range(amount_msgs):
                                        send_msg(
                                            f" > {egg['title']}< found!\nUrl: {offer_url}"
                                        )  #
                                        time.sleep(1)

                                print("Found what you were looking for!")
                                return True
                            else:
                                print(
                                    "Found what you were looking for, but its out of stock. But it might be available again later."
                                )
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-s",
        "--skip-crawling",
        action="store_true",
        dest="skip_crawling",
        help="Skipping the crawling phase",
    )
    args = parser.parse_args()
    skip_crawling = args.skip_crawling
    try:
        if skip_crawling == False:
            if os.path.isfile("./urls.txt"):
                overwrite = input("Urls.txt exists, skip url crawling? [Y/n]: ")

                if overwrite.lower() == "y" or overwrite == "":
                    print("Skipping crawl phase\n")
                    skip_crawling = True

            if skip_crawling == False:
                print("Start crawling for urls....")
                crawl_urls()
                print("Crawling finished.")

        found = False
        while not found:
            print("Checking the pages for easter eggs")
            found = check_pages()
            print("Checked all available pages. Sleeping for 60 seconds")
            time.sleep(60)

    except Exception as e:
        print(f"Error: {e}")
