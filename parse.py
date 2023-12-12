import re
import zipfile
import plistlib
import os
import glob
import time
import json
import argparse
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Created by: @Lunascaped

# Add arguments to the script
parser = argparse.ArgumentParser()
parser.add_argument('-f', action='store_true', help='Use the iTunes API to get app store data if data is missing from the IPA')
parser.add_argument('-d', type=str, required=True , help='Directory for IPA files')
args = parser.parse_args()


# File Size Formatter taken from StackOverflow
def sizeof_fmt(num, suffix="B"):
	for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
		if abs(num) < 1024.0:
			return f"{num:3.1f}{unit}{suffix}"
		num /= 1024.0
	return f"{num:.1f}Yi{suffix}"

def get_ipa_info(ipa_path, use_appstore_data=args.f):
	# Open the IPA file and extract the Info.plist file
	with zipfile.ZipFile(ipa_path, 'r') as ipa_file:
		info_plist_filename = None
		for filename in ipa_file.namelist():
			match = re.match(r'^Payload/.*\.app/Info\.plist$', filename)
			if match:
				info_plist_filename = filename
				break
		if not info_plist_filename:
			raise ValueError('Info.plist file not found in IPA archive')
		info_plist_data = ipa_file.read(info_plist_filename)

	# Parse the Info.plist file to extract the desired values
		info_plist = plistlib.loads(info_plist_data)
		bundle_name = info_plist.get('CFBundleName', '')
		bundle_display_name = info_plist.get('CFBundleDisplayName', '')
		bundle_version = info_plist.get('CFBundleShortVersionString', '')
		bundle_identifier = info_plist.get('CFBundleIdentifier', '')
		app_category = info_plist.get('LSApplicationCategoryType', 'Unknown')
		app_description = "Empty"
		app_screenshots = "Empty"
		app_age = "Empty"
		app_languages = "Empty"

		if use_appstore_data:
			if app_category == 'Unknown':
				app_category = get_appstore_category(bundle_identifier)
			app_description = get_appstore_description(bundle_identifier)
			app_screenshots = get_appstore_screenshots(bundle_identifier)
			app_age = get_appstore_age(bundle_identifier)
			app_languages = get_appstore_languages(bundle_identifier)



		# Extract the app icon file
		app_icon_filename = None
		max_size = 0

		# Get app icon name from info.plist
		if info_plist:
			app_icon_name = None
			try:
				app_icon_name = info_plist.get('CFBundleIcons')['CFBundlePrimaryIcon']['CFBundleIconName']
			except Exception:
				app_icon_name = info_plist.get('CFBundleIconFiles')[0]
			for filename in ipa_file.namelist():
				if filename.endswith(f'{app_icon_name}.png'):
					size = ipa_file.getinfo(filename).file_size
					if size > max_size:
						app_icon_filename = filename
						max_size = size


		# Check if app icon name is in filename
		if not app_icon_filename:
			for filename in ipa_file.namelist():
				match = re.match(r'^Payload/.*\.app/.*[Ii]con.*\.png$', filename)
				if match:
					app_icon_filename = filename
					break
			if not app_icon_filename:
				raise ValueError('App icon file not found in IPA archive')
			app_icon_data = ipa_file.read(app_icon_filename)


		# Set app icon filename to "unknown" if not found
		if not app_icon_filename:
			app_icon_filename = "unknown"

		app_icon_data = None  # Set default value to None
		if app_icon_filename != "unknown":
			app_icon_data = ipa_file.read(app_icon_filename)  # Only read the file if the filename is valid

		# Save the app icon to a file with a name based on the IPA file name
		ipa_filename = os.path.basename(ipa_path)
		app_icon_filenamed = f'{os.path.splitext(ipa_filename)[0]}_app_icon.png'
		with open(app_icon_filenamed, 'wb') as app_icon_file:
			if app_icon_data:
				app_icon_file.write(app_icon_data)

	
		# Get the size of the original IPA file
		ipa_file_size = sizeof_fmt(os.path.getsize(ipa_path))

		# Get creation date of IPA file
		creation_time = os.path.getctime(ipa_path)
		creation_date = datetime.fromtimestamp(creation_time).strftime('%d-%m-%Y %H:%M:%S')
		
		# Return the extracted values
		return {
			"Bundle Name": bundle_name,
			"Bundle Display Name": bundle_display_name,
			"Bundle Version": bundle_version,
			"Bundle Identifier": bundle_identifier,
			"App Category": app_category,
			"App Icon Size": sizeof_fmt(len(app_icon_data)),
			"IPA File Size": ipa_file_size,
			"App Icon Filename": app_icon_filenamed,
			"App Description": app_description,
			"App Screenshots": app_screenshots,
			"Creation Date": creation_date,
			"App Age": app_age,
			"App Languages": app_languages
		}


# Find all IPA files in a directory (fill in your own path)
ipa_file_paths = glob.glob(f'{args.d}/*.ipa')

def get_appstore_category(bundle_id):

	url = f'https://itunes.apple.com/lookup?bundleId={bundle_id}'
	response = requests.get(url)

	if response.status_code == 200:
		json_data = response.json()
		if json_data['resultCount'] > 0:
			return json_data['results'][0]['primaryGenreName']
		else:
			return 'Unknown'
	else:
		return 'Request Error'

def get_appstore_description(bundle_id):
	
	url = f'https://itunes.apple.com/lookup?bundleId={bundle_id}'
	response = requests.get(url)

	if response.status_code == 200:
		json_data = response.json()
		if json_data['resultCount'] > 0:
			return json_data['results'][0]['description']
		else:
			return 'Unknown'
	else:
		return 'Request Error'

def get_appstore_screenshots(bundle_id):
	
	url = f'https://itunes.apple.com/lookup?bundleId={bundle_id}'
	response = requests.get(url)

	if response.status_code == 200:
		json_data = response.json()
		if json_data['resultCount'] > 0:
			return json_data['results'][0]['screenshotUrls']
		else:
			return 'Unknown'
	else:
		return 'Request Error'


def get_appstore_age(bundle_id):
	
	url = f'https://itunes.apple.com/lookup?bundleId={bundle_id}'
	response = requests.get(url)

	if response.status_code == 200:
		json_data = response.json()
		if json_data['resultCount'] > 0:
			return json_data['results'][0]['contentAdvisoryRating']
		else:
			return 'Unknown'
	else:
		return 'Request Error'

def get_appstore_languages(bundle_id):
	
	url = f'https://itunes.apple.com/lookup?bundleId={bundle_id}'
	response = requests.get(url)

	if response.status_code == 200:
		json_data = response.json()
		if json_data['resultCount'] > 0:
			return json_data['results'][0]['languageCodesISO2A']
		else:
			return 'Unknown'
	else:
		return 'Request Error'


# Define a function to process a single IPA file
def process_ipa_file(ipa_path):
	try:
		result = get_ipa_info(ipa_path)
		ipa_name = os.path.basename(ipa_path).replace('.ipa', '')
		ipa_info ={
			'name': ipa_name,
			'bundle_name': result['Bundle Name'],
			'bundle_display_name': result['Bundle Display Name'],
			'bundle_version': result['Bundle Version'],
			'bundle_identifier': result['Bundle Identifier'],
			'app_category': result['App Category'],
			'app_icon_size': result['App Icon Size'],
			'app_icon_filename': result['App Icon Filename'],
			'ipa_file_size': result['IPA File Size'],
			'app_description': result['App Description'],
			'app_screenshots': result['App Screenshots'],
			'creation_date': result['Creation Date'],
			'app_age': result['App Age'],
			'app_languages': result['App Languages']
		}

		# append the dictionary to the list
		output_list.append(ipa_info)

		print(f'{ipa_path}: Done')
	except Exception as e:
		print(f'{ipa_path}: Error: {str(e)}')


# Process all IPA files in parallel using a thread pool
output_list = []
start_time = time.monotonic()
with ThreadPoolExecutor() as executor:
	executor.map(process_ipa_file, ipa_file_paths)
end_time = time.monotonic()
total_files = len(ipa_file_paths)
total_time = end_time - start_time 
# write the list to the output file
with open(f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json', 'w') as output_file:
	json.dump(output_list, output_file, indent=4)

print(f'Processed {total_files} files in {total_time:.2f} second(s)')
