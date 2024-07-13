# utilityScript
This repository is intended to store different scripts made for different purposes

# arwFinder
This Python script is designed to help photographers efficiently retrieve the .arw (RAW) image corresponding to a specific .jpg file created by a Sony camera when using the double-saving mode (both .jpg and .arw).

## Overview
When a Sony camera saves both .jpg and .arw files simultaneously, the filenames and shooting metadata (like shooting time) can be used to match the files. This script automates the matching process, making it easier and faster to manage and organize your photos.

## Features
Filename Matching: The script first tries to match the files based on their filenames.
Metadata Matching: If filenames do not lead to a unique solution, the script uses metadata, specifically the shooting time, to find the correct .arw file.
User Interaction: The script interacts with the user to:
Specify the paths for the images.
Confirm parameters before starting the automatic matching process.
Manually select the correct file when multiple candidates are found.

## Usage
Initial Setup: The user provides the paths for the .jpg and .arw image directories.
Parameter Confirmation: The user confirms the input paths and other parameters before the script begins the automatic matching process.
Automatic Matching: The script attempts to automatically match .jpg and .arw files based on filenames and metadata.
User Interaction for Ambiguities: If a clear match is not found, the user is prompted to either accept the suggested image or provide the path to the correct .arw file.

## Requirements
Python 3.x

Libraries: os, exifread or piexif

## License
This project is licensed under the MIT License. See the LICENSE file for details.
