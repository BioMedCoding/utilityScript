import os
import shutil
import exifread
from tqdm import tqdm
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from tabulate import tabulate
from functools import lru_cache
import time

# Logging configuration
logging.basicConfig(filename="script.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# LRU Cache for EXIF data to minimize disk reads
@lru_cache(maxsize=None)
def get_creation_date(file_path):
    try:
        with open(file_path, 'rb') as f:
            tags = exifread.process_file(f)
            date_tag = 'EXIF DateTimeOriginal'
            if date_tag in tags:
                return datetime.strptime(str(tags[date_tag]), '%Y:%m:%d %H:%M:%S')
    except Exception as e:
        logging.error(f"Error reading metadata from {file_path}: {e}")
    return None

# Function to get the progressive number of the photo
def get_base_name(file_name):
    match = re.match(r'_DSC(\d{4})', file_name)
    if match:
        return match.group(1)
    return None

# Function to get user input with confirmation
def get_user_input(prompt, default_value=None):
    if default_value is not None:
        prompt += f" (default: {default_value}): "
    else:
        prompt += ": "
    print(".............................................................................")
    value = input(prompt)
    if default_value is not None and value.strip() == "":
        value = default_value
    confirmation = input(f"You entered: '{value}'. Confirm? (y/n): ")
    while confirmation.lower() != 'y':
        value = input(prompt)
        if default_value is not None and value.strip() == "":
            value = default_value
        confirmation = input(f"You entered: '{value}'. Confirm? (y/n): ")
    return value

# Function to find .arw files in SD card folders
# CHECK IT AGAIN
def find_arw_files(sd_folder):
    arw_files = {}
    for root, _, files in os.walk(sd_folder):
        for file in files:
            if file.lower().endswith('.arw'):
                arw_path = os.path.join(root, file)
                creation_date = get_creation_date(arw_path)
                base_name = get_base_name(file)
                if creation_date and base_name: # Check that both are note None
                    if base_name not in arw_files:
                        arw_files[base_name] = []   # Initialize a new key
                    arw_files[base_name].append((arw_path, creation_date))
    return arw_files

# Function to find files with similar metadata
def find_similar_files(target_date, arw_file_list,max_time_difference):
    similar_files = []
    time_threshold = timedelta(seconds=max_time_difference)
    for arw_path, creation_date in arw_file_list:
        time_difference = abs(creation_date - target_date)
        if time_difference <= time_threshold:
            similar_files.append((arw_path, creation_date, time_difference.total_seconds()))
    similar_files.sort(key=lambda x: x[2])  # Sort by time difference
    return similar_files

def get_user_confirmation(original_file, similar_files):
    print(f"\nOriginal file: {original_file['name']}, Path: {original_file['path']}, Shooting time: {original_file['time']}\n")
    print("Multiple similar files found:")

    table_data = [
        [idx + 1, os.path.basename(sim_path), sim_path, sim_date, f"{time_diff:.2f} seconds"]
        for idx, (sim_path, sim_date, time_diff) in enumerate(similar_files)
    ]
    print(tabulate(table_data, headers=["Option", "Name", "Path", "Shooting Time", "Time Difference"]))

    choice = input("\nEnter the number of the correct file (or '0' to enter manually): ")
    if choice.isdigit() and 1 <= int(choice) <= len(similar_files):
        return similar_files[int(choice) - 1][0]
    elif choice == '0':
        manual_file = input("Enter the full path to the correct file: ")
        if os.path.exists(manual_file):
            return manual_file
        else:
            print("File does not exist. Please try again.")
            return get_user_confirmation(original_file, similar_files)
    else:
        print("Invalid choice. Please try again.")
        return get_user_confirmation(original_file, similar_files)

def process_jpg_file(jpg_file, selected_jpg_folder, arw_files, output_folder, log_file, unmatched_files):
    jpg_path = os.path.join(selected_jpg_folder, jpg_file)
    jpg_creation_date = get_creation_date(jpg_path)
    base_name = get_base_name(jpg_file)

    if base_name in arw_files:
        arw_file_list = arw_files[base_name]
        if len(arw_file_list) == 1:
            arw_path = arw_file_list[0][0]
            output_path = os.path.join(output_folder, os.path.basename(arw_path))
            try:
                shutil.copy2(arw_path, output_path)
                logging.info(f"Copied {arw_path} to {output_path}")
            except Exception as e:
                log_message = f"Error copying {arw_path} to {output_path}: {e}\n"
                log_file.write(log_message)
                logging.error(log_message)
        else:
            similar_files = find_similar_files(jpg_creation_date, arw_file_list)
            if similar_files:
                unmatched_files.append((jpg_file, jpg_path, jpg_creation_date, similar_files))
            else:
                log_message = f"No similar .arw files found for {jpg_file}\n"
                print(log_message)
                log_file.write(log_message)
                logging.warning(log_message)
    else:
        log_message = f".arw file not found for {jpg_file} with creation date {jpg_creation_date}\n"
        log_file.write(log_message)
        logging.warning(log_message)

def handle_unmatched_files(unmatched_files, output_folder, log_file):
    for jpg_file, jpg_path, jpg_creation_date, similar_files in unmatched_files:
        original_file = {
            'name': jpg_file,
            'path': jpg_path,
            'time': jpg_creation_date
        }
        arw_path = get_user_confirmation(original_file, similar_files)
        if arw_path:
            output_path = os.path.join(output_folder, os.path.basename(arw_path))
            try:
                shutil.copy2(arw_path, output_path)
                logging.info(f"Copied {arw_path} to {output_path} after user confirmation")
            except Exception as e:
                log_message = f"Error copying {arw_path} to {output_path}: {e}\n"
                log_file.write(log_message)
                logging.error(log_message)
        else:
            log_message = f"No valid .arw file found for {jpg_file} after user confirmation\n"
            log_file.write(log_message)
            logging.error(log_message)

def main():
    num_workers = int(get_user_input("\nEnter the number of workers to use for parallel processing", default_value="8"))

    selected_jpg_folder = os.path.abspath(get_user_input("\nEnter the path to the folder containing the selected .jpg files"))
    sd_card_folders = [os.path.abspath(path) for path in get_user_input("\nEnter the paths to the SD card folders (separated by space)").split()]
    output_folder = os.path.abspath(get_user_input("\nEnter the path to the output folder for .arw files"))

    print("\nSummary of choices:")
    sd_folders_summary = "\n".join([f"{i + 1}. {folder}" for i, folder in enumerate(sd_card_folders)])
    summary_table = [
        ["Folder containing selected .jpg files", selected_jpg_folder],
        ["SD card folders", sd_folders_summary],
        ["Output folder for .arw files", output_folder],
        ["Number of workers", num_workers]
    ]

    print(tabulate(summary_table, tablefmt="grid"))

    final_confirmation = input("\nDo you confirm these choices? (y/n): ")
    if final_confirmation.lower() != 'y':
        print("Operation cancelled.")
        return

    start_time = time.time()

    # Create output folder if it does not exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Preload metadata for all .arw files using multiple threads
    print("\nPreloading metadata for .arw files...")
    arw_files = {}
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(find_arw_files, folder) for folder in sd_card_folders]
        for future in tqdm(as_completed(futures), total=len(futures), desc="Preloading metadata", unit="folder"):
            result = future.result()
            for key, value in result.items():
                if key not in arw_files:
                    arw_files[key] = []
                arw_files[key].extend(value)

    # Get the list of selected .jpg files
    selected_jpg_files = [f for f in os.listdir(selected_jpg_folder) if f.lower().endswith('.jpg')]
    total_files = len(selected_jpg_files)

    unmatched_files = []

    # Create a log file for .arw files not found
    log_file_path = os.path.join(output_folder, "log.txt")
    with open(log_file_path, "w") as log_file:
        log_file.write("Log of missing .arw files:\n\n")
        print("\nCopying corresponding .arw files to the output folder...")

        # Process files using the pool of workers
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(process_jpg_file, jpg_file, selected_jpg_folder, arw_files, output_folder, log_file, unmatched_files)
                       for jpg_file in selected_jpg_files]
            for future in tqdm(as_completed(futures), total=len(futures), desc="Copying .arw files", unit="file"):
                future.result()

    total_elapsed_time = time.time() - start_time
    completion_message = f"Automatic part completed in {total_elapsed_time:.2f} seconds. Check the log file for any issues. Eventual exceptions will now be processed"
    print(completion_message)
    logging.info(completion_message)

    # Handle unmatched files after initial processing
    handle_unmatched_files(unmatched_files, output_folder, log_file)

if __name__ == "__main__":
    main()
