#!/usr/bin/env python3

"""

This script requires Python 3.2+.
Ref: http://stackoverflow.com/questions/12517451/python-automatically-creating-directories-with-file-output
"""

#from __future__ import absolute_import, division, print_function, unicode_literals

import re
import os
import sys
import json
import gzip
import fnmatch
import argparse
import queue
import os.path
import logging
import multiprocessing as mp
from urllib.parse import urlparse
#import threading

from trillian.utilities.files.fits import fitsmd_from_file, is_fits_file

# replaced with trillian.files.fits
# def is_fits_file(filename, read_compressed=False):
# 	'''
# 	Check if this is a FITS file. Not robust - only checks for extension.
# 	'''
# 	allowed_suffixes = [r'\.fits$', r'\.fts$']
# 	
# 	if read_compressed:
# 		allowed_suffixes = allowed_suffixes + [r'\.fits.gz$', r'\.fts.gz$', r'\.fits.bz2$', r'\.fts.bz2$']
# 
# 	return any([re.search(suffix, filename, re.IGNORECASE) for suffix in allowed_suffixes])
	
def worker_main(queue):
	done = False
	while True and not done:
		# TODO: Handle a "done" signal placed on queue
		filepath, output = queue.get(True)
		done = filepath is None
		if not done:
			extract_header(filepath, output)

def extract_header(filepath, output_filepath):
	'''
	Read FITS file at "filepath", extract header and write JSON file to "output_filepath".
	'''
	metadata = fitsmd_from_file(filepath) # in JSON format
	
	# create directories if needed
	os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
	
	if (args.gzip_output):
		with gzip.open(output_filepath+".gz", "wb") as out:
			out.write(bytes(metadata, 'UTF-8'))
	else:
		with open(output_filepath, 'w') as out:
			out.write(metadata)

def producer(files):
	for filename in files:
		if is_fits_file(filepath=filename, read_compressed=args.compressed) == False:
			continue

		#print("Adding file to queue: {0}".format(os.path.basename(filename)))
		filepath = os.path.join(root, filename)
		output_filepath = os.path.join(output_dir, relative_directory, filename.rstrip(".gz")+".fitsmd")
		queue.put((filepath, output_filepath))
		if args.limit:
			file_count = file_count + 1
			if file_count > args.limit:
				sys.exit(1)

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description="A script to create a FITS metadata file (.fitsmd) from a FITS file. Accepts local files or files on a web server.")
	parser.add_argument("-d", "--directory",
						help="root directory to search for FITS files",
						dest="source_directory",
						default=".")
	parser.add_argument("-r", "--recursive",
						help="search source directory recursively",
						action="store_true")
	parser.add_argument("-o", "--output",
						help="output directory",
						dest="output_directory",
						default=".")
	parser.add_argument("-c", "--compressed",
						help="read compressed (gzip or bzip2) FITS files if found",
						dest="compressed",
						action="store_true",
						default=True)
	parser.add_argument("-g", "--gzip",
						help="gzip output files (individually)",
						dest="gzip_output",
						action="store_true")
	parser.add_argument("-l", "--limit",
						help="limit to n files",
						dest="limit",
						type=int,
						default=None)
	parser.add_argument("-p", "--processes",
						help="use multiprocessing with n processes (0 = no of cores, default)",
						dest="consumer_count",
						type=int,
						default=0)
	parser.add_argument("-i", "--input_list",
						help="use input file that contains a list of files to read (local or URL)",
						dest="input_list",
						default=None)
	parser.add_argument("-f", "--files",
						help="only process files specified on command line",
						dest="files",
						nargs="+",
						default=None)
	parser.add_argument("--regex",
						help="only process filenames that match this regex pattern",
						dest="filename_regex",
						default=None)
	parser.add_argument("--verbose",
						help="verbose output",
						dest="verbose",
						action="store_true",
						default=False)
	
	# Print help if no arguments are provided
	if len(sys.argv) < 2:
		parser.print_help()
		parser.exit(1)

	args = parser.parse_args()

	# set up logging
	#    options: DEBUG, INFO, WARNING, ERROR, CRITICAL
	#
	if args.verbose:
		logging.basicConfig(level=logging.DEBUG)
	else:
		logging.basicConfig(level=logging.ERROR)
		
	source_dir = args.source_directory
	output_dir = args.output_directory

	# ----------------------------------
	# get processor count & set up queue
	# ----------------------------------
	if args.consumer_count == 0: #  0 = number of cores available
		n_processes = os.cpu_count()
		if n_processes == None: # can't determine number of cores
			n_processes = 1
	elif args.consumer_count < 1:
		print("An invalid number of processes was specified ({0}).".format(args.consumer_count))
	else:
		n_processes = args.consumer_count

	queue = mp.Queue(maxsize=10)
	#n_processes = args.consumer_count
	pool = mp.Pool(processes=n_processes, initializer=worker_main, initargs=(queue,))
	
	file_count = 0
	# ----------------------------------

	if args.files:
		# only process the files provided on the command line
		for resource in args.files:
			if resource.startswith("http:"):
				u = urlparse(resource)
				filename = os.path.basename(u.path)
				output_filepath = os.path.join(output_dir, filename+".fitsmd")
			else:
				# treat as local file
				(path, filename) = os.path.split(resource)
				output_filepath = os.path.join(output_dir, filename.rstrip(".gz")+".fitsmd")
			queue.put((resource, output_filepath))

	elif args.input_file:
		# Read from the files listed in given file.
		# If the path starts with a "/", read it as a full path,
		# otherwise assume the paths are relative to the directory specified in the "-d" argument.

		with open(args.input_file) as input_file:
			for nextpath in input_file:
				trimmed_path=nextpath
				trimmed_path=trimmed_path.strip()
				if trimmed_path[0] == '/':
					filepath = trimmed_path
					output_filepath = os.path.join(output_dir, filepath.rstrip(".gz")+".fitsmd")
				else:
					filepath = os.path.join(source_dir, trimmed_path)
					output_filepath = os.path.join(output_dir, filepath.rstrip(".gz")+".fitsmd")
				queue.put((filepath, output_filepath))
	
	elif args.recursive:
		for root, subdirs, files in os.walk(top=source_dir, followlinks=True): # todo: make symlink command line param
			# root: current path
			# subdirs: list of directories in current path
			# files: list of files in current path
		
			relative_directory = os.path.relpath(root, source_dir)
		
			for filename in files:
				# "is FITS" check is based on filename alone
				if is_fits_file(filepath=filename, read_compressed=args.compressed) == False:
					continue
			
				#print("Adding file to queue: {0}".format(os.path.basename(filename)))
				filepath = os.path.join(root, filename)
				output_filepath = os.path.join(output_dir, relative_directory, filename.rstrip(".gz")+".fitsmd")
				if os.path.isfile(output_filepath) == False:
					queue.put((filepath, output_filepath))
			
				if args.limit:
					file_count = file_count + 1
					if file_count > args.limit:
						sys.exit(1)
							
	else:
		for filename in os.listdir(source_dir):
			if is_fits_file(filepath=filename, read_compressed=args.compressed) == False:
				continue
			
			filepath = os.path.join(source_dir, filename)
			output_filepath = os.path.join(output_dir, filename.rstrip(".gz")+".fitsmd")
			if os.path.isfile(output_filepath) == False:
			
				if args.filename_regex:
					m = re.search(args.filename_regex, filepath)
					if m is None:
						logging.debug("Skipping filepath that doesn't match regexp: {0}".format(filepath))
						continue
				#extract_header(filepath, output_filepath) # use for debugging INSTEAD of next line
				queue.put((filepath, output_filepath))

	for i in range(n_processes):
		# An empty tuple signals we are done, one per worker.
		queue.put((None, None))

	# wait for all of the consumer threads to finish
	# ----------------------------------------------
	pool.close()
	pool.join()
	
