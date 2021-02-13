#!/usr/bin/python3

# downloads manga from input url (mangadex) and spits out an epub

import cloudscraper
import os
import sys
import re
import json
import mangadex
import fileinput
import shutil

def meta(manga_id):
	# grab manga info json from api
	scraper = cloudscraper.create_scraper()

	r = scraper.get("https://api.mangadex.org/v2/manga/{}/".format(manga_id))

	jason = json.loads(r.text)

	try:
		author = jason["data"]["author"][0]
		title = jason["data"]["title"]
		title = re.sub('[/<>:"/\\|?*]', '-', title)

		return [author, title]

	except Exception:
		print("Something effed up :/")

if __name__ == "__main__":

	if len(sys.argv) > 1:
		url = sys.argv[1]

	manga_id = re.search("[0-9]+", url).group(0)

	data = meta(manga_id)
	author = data[0]
	title = data[1]
	dir = title.replace(" ", "\ ")

	mangadex.dl(manga_id)

	os.system("kcc-c2e -p KoAO -u -q download/%s"%dir)
	epub = title+".kepub.epub"
	epub_path = epub.replace(" ", "\ ")
	os.rename("download/%s"%epub, epub)

	os.system("unzip -j -qq %s OEBPS/content.opf -d OEBPS"%epub_path)
	os.system("sed -i \"s/<dc:creator>KCC<\/dc:creator>/<dc:creator>"+author+"<\/dc:creator>/\" OEBPS/content.opf")
	os.system("zip %s OEBPS/content.opf -q"%epub_path)

	shutil.rmtree("OEBPS")

	print ("Done!")
