#!/usr/bin/python3

# loidor hack of mangadex-dl
#
# defaults to english
# downloads url given as arg
# retries 15 times if failing
# checks image integrity
# downloads main cover to title folder

import cloudscraper
import time, os, sys, re, json, html, random
from PIL import Image

A_VERSION = "X.X"

def pad_filename(str):
	digits = re.compile('(\\d+)')
	pos = digits.search(str)
	if pos:
		return str[1:pos.start()] + pos.group(1).zfill(3) + str[pos.end():]
	else:
		return str

def float_conversion(x):
	try:
		x = float(x)
	except ValueError: # empty string for oneshot
		x = 0
	return x

def zpad(num):
	if "." in num:
		parts = num.split('.')
		return "{}.{}".format(parts[0].zfill(3), parts[1])
	else:
		return num.zfill(3)

def dl(manga_id):
	# grab manga info json from api
	scraper = cloudscraper.create_scraper()
	try:
		r = scraper.get("https://api.mangadex.org/v2/manga/{}/?include=chapters".format(manga_id))
		jason = json.loads(r.text)
	except (json.decoder.JSONDecodeError, ValueError) as err:
		print("CloudFlare error: {}".format(err))
		exit(1)
	except:
		print("Error with URL.")
		exit(1)

	try:
		title = jason["data"]["manga"]["title"]
	except:
		print("Please enter a valid MangaDex manga (not chapter) URL or ID.")
	print("\nDownloading: {}".format(html.unescape(title)))

	# Create title folder, download cover image
	title = re.sub('[/<>:"/\\|?*]', '-', title)
	title_dir = os.path.join(os.getcwd(), "download", title)
	if not os.path.exists(title_dir):
		os.makedirs(title_dir)

	cover = jason["data"]["manga"]["mainCover"]
	cover_ext = cover[-3:]
	cover_path = title_dir+"/cover."+cover_ext
	cover_file = scraper.get(cover)

	if cover_file.status_code == 200:
		with open(cover_path, 'wb') as f:
			f.write(cover_file.content)

	# check available chapters
	chapters = []
	for i in jason["data"]["chapters"]:
		if i["language"] == "gb":
			chapters.append(i["chapter"])
	chapters.sort(key=float_conversion) # sort numerically by chapter #

	chapters = ["Oneshot" if x == "" else x for x in chapters]
	if len(chapters) == 0:
		print("No chapters available to download!")
		exit(0)

	# i/o for chapters to download
	requested_chapters = []
#	chap_list = chapters[0]+"-"+chapters[-1]
	chap_list = "155"
	chap_list = [s for s in chap_list.split(',')]
	for s in chap_list:
		s = s.strip()
		if "-" in s:
			split = s.split('-')
			lower_bound = split[0]
			upper_bound = split[1]
			try:
				lower_bound_i = chapters.index(lower_bound)
			except ValueError:
				print("Chapter {} does not exist. Skipping {}.".format(lower_bound, s))
				continue # go to next iteration of loop
			try:
				upper_bound_i = chapters.index(upper_bound)
			except ValueError:
				print("Chapter {} does not exist. Skipping {}.".format(upper_bound, s))
				continue
			s = chapters[lower_bound_i:upper_bound_i+1]
		elif s.lower() == "oneshot":
			if "Oneshot" in chapters:
				s = ["Oneshot"]
			else:
				print("Chapter {} does not exist. Skipping.".format(s))
		else:
			try:
				s = [chapters[chapters.index(s)]]
			except ValueError:
				print("Chapter {} does not exist. Skipping.".format(s))
				continue
		requested_chapters.extend(s)

	# find out which are availble to dl
	chaps_to_dl = []
	chapter_num = None
	for i in jason["data"]["chapters"]:
		try:
			chapter_num = str(float(i["chapter"]))
			chapter_num = re.sub('.0$', '', chapter_num) # only replace at end (not chapter #s with decimals)
		except: # oneshot
			if "Oneshot" in requested_chapters and i["language"] == "gb":
				chaps_to_dl.append(("Oneshot", i["id"]))
		if chapter_num in requested_chapters and i["language"] == "gb":
			chaps_to_dl.append((str(chapter_num), i["id"]))
	chaps_to_dl.sort(key = lambda x: float_conversion(x[0]))

	# get chapter(s) json
	print()
	for chapter_info in chaps_to_dl:

		r = scraper.get("https://api.mangadex.org/v2/chapter/{}/".format(chapter_info[1]))
		chapter = json.loads(r.text)

		# Get metadata
		metadata_volume = chapter["data"]["volume"]
		metadata_chapter = chapter["data"]["chapter"]
		metadata_title = chapter["data"]["title"]

		print("Downloading Vol. {}, Ch. {} - {}...".format(metadata_volume,metadata_chapter,metadata_title))

		# get url list
		images = []
		server = chapter["data"]["server"]
		if "mangadex." not in server:
			server = chapter["data"]["serverFallback"] # https://s2.mangadex.org/data/
		hashcode = chapter["data"]["hash"]
		for page in chapter["data"]["pages"]:
			images.append("{}{}/{}".format(server, hashcode, page))

		# download images
		for pagenum, url in enumerate(images, 1):
			filename = os.path.basename(url)
			ext = os.path.splitext(filename)[1]

			title = re.sub('[/<>:"/\\|?*]', '-', title)
			dest_folder = os.path.join(os.getcwd(), "download", title, "Vol. {}, Ch. {} - {}".format(metadata_volume, metadata_chapter, metadata_title))
			if not os.path.exists(dest_folder):
				os.makedirs(dest_folder)
			dest_filename = pad_filename("{}{}".format(pagenum, ext))
			outfile = os.path.join(dest_folder, dest_filename)

			verify_check = 0

			while verify_check == 0:
				r = scraper.get(url)
				if r.status_code == 200:
					with open(outfile, 'wb') as f:
						f.write(r.content)
						# verify downloaded file
						testpage = Image.open(outfile)
						try:
							testpage.verify()
							verify_check = 1
						except Exception:
							print("  File verification failed, trying again...")
							continue
						print(" Downloaded page {}.".format(pagenum))
				else:
					# silently try again 15 times
					counter=0

					while counter < 15:
						time.sleep(3)
						r = scraper.get(url)
						if r.status_code == 200:
							with open(outfile, 'wb') as f:
								f.write(r.content)
								testpage = Image.open(outfile)
								try:
									testpage.verify()
									verify_check = 1
								except Exception:
									print("  **COUGH! COUGH!**")
									continue
								print(" Downloaded page {}.".format(pagenum))
								break
						else:
							counter += 1
							print("  **HICCUP!**")
							continue
			time.sleep(1)

	print("Manga downloaded!")

if __name__ == "__main__":
	print("mangadex-dl v{}".format(A_VERSION))

	if len(sys.argv) > 1:
		url = sys.argv[1]
	else:
		url = ""
	while url == "":
		url = input("Enter manga URL or ID: ").strip()
	try:
		manga_id = re.search("[0-9]+", url).group(0)
		split_url = url.split("/")
		for segment in split_url:
			if "mangadex" in segment:
				url = segment.split('.')
	except:
		print("Error with URL.")
		exit(1)

	dl(manga_id)
