#!/usr/bin/python2.6 
# sqlite2googlepowermeter
# 	Reads and transmit sqlite data to Google PowerMeter.
# 	
#	based on worked found at
#	http://gitorious.org/pge-to-google-powermeter/
#
#	Copyright (C) 2010	Sebastien Person
#	 Copyright (C) 2010	Andrew Potter
#
#	 This program is free software: you can redistribute it and/or modify
#	 it under the terms of the GNU General Public License as published by
#	 the Free Software Foundation, either version 3 of the License, or
#	 (at your option) any later version.
#
#	 This program is distributed in the hope that it will be useful,
#	 but WITHOUT ANY WARRANTY; without even the implied warranty of
#	 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
#	 GNU General Public License for more details.
#
#	 You should have received a copy of the GNU General Public License
#	 along with this program.	If not, see <http://www.gnu.org/licenses/>.
#
#
# Sqlite stored data and uploads to
# Google PowerMeter using their Python API. The user of this script
# must:
# 
# 1) Download the Python API files from
# http://code.google.com/p/google-powermeter-api-client/downloads/list
# This script must be run from the same directory as google_meter.py
#
# 2) Follow the instructions at
# http://code.google.com/apis/powermeter/docs/powermeter_device_activation.html
# to get a "token" and "variable." Be sure to create a *Durational*
# variable (e.g. dvars=1). Note that on the final confirmation screen
# Google gives a "path" variable. The input to this script must be the variable.
# For example, Google says your path is "/user/1234/5678/variable/abcde"
# The variable is then									"/user/1234/5678/variable/abcde.d1"
#
# 3) Download your data files into a sqlite file
# 
# 4) Run this script. Note that Google doesn't
# like you to upload too quickly. Ideally you should upload 1 batch
# every 10 minutes. If you go faster, then eventually Google will
# block you for a while.
#
#
# Features: Directly uploads to Google PowerMeter. 
#							 

import os
import sys
from optparse import OptionParser
import google_meter
import ConfigParser as cp
import sqlite3
from google_meter import DurMeasurement
import units

programVersion = '0.1'
programName = 'sqlite2googlepowermeter'
config_filename = 'config'

def parseArguments():
	op = OptionParser('%prog [--token <token>] [--variable <variable>] Filename.db \n\n' + '''
arguments:
	Filename.db				The sqlite datafile (required)''', version="%s %s" % (programName, programVersion))
	op.add_option('', '--token', metavar='<token>',
								help='Google PowerMeter OAUTH Token'
										 ' (default: None)')
	op.add_option('', '--variable', metavar='<variable>',
								help='Google PowerMeter Variable'
										 ' (default: None)')
	op.add_option('', '--service', metavar='<URI>',
								help='URI prefix of the GData service to contact '
										 '(default: https://www.google.com/powermeter/feeds)')
	op.add_option('-f','--configFile', metavar='<configFile>', help="Path and filename of configuration file (default: ~/.local/%s/config)" % programName)

	op.set_defaults(service='https://www.google.com/powermeter/feeds',
									unit='kW h', uncertainty=0.001, time_uncertainty=1)

	# Parse and validate the command-line options.
	options, args = op.parse_args()

	# Check for config file, setup default otherwise
	if options.configFile == None:
		home = os.getenv('HOME')
		config_home = os.getenv('XDG_CONFIG_HOME',"%s/.local/" % home)
		config_dir = "%s%s" % (config_home,programName)
		filepath = "%s/%s" % (config_dir, config_filename)
		if os.path.exists(config_home):
			if os.path.exists(config_dir):
				if os.path.exists(filepath):
					options.configFile = filepath
	else:
		if not os.path.exists(options.configFile):
			print os.getcwd() + options.configFile
			if os.path.exists(os.getcwd() + options.configFile):
					options.configFile = os.getcwd() + options.configFile
			else:
					sys.stderr.write("Error: Can not find config file '%s'\n" % options.configFile)
					exit(2)
	
	if options.token == None:
		if checkConfigfile(options.configFile,'token'):
			options.token = getConfigfile(options.configFile,'token')
		else:
			sys.stderr.write('Error: Missing Google Power Meter OAuth token. \nToken must be supplied via --token or in the config file (token entry).\n')
			op.exit(2, op.format_help())
	if options.variable == None:
		if checkConfigfile(options.configFile,'variable'):
			options.variable = getConfigfile(options.configFile,'variable')
		else:
			sys.stderr.write('Error: Missing Google Power Meter variable.\nVariable must be supplied via --variable or in the config file (variable entry).\n')
			op.exit(2,op.format_help())

	if len(args) < 1:
		sys.stderr.write('Error: No input file specified.\n')
		op.exit(2, op.format_help())

	return (args, options)


def checkConfigfile(filename,var):
	# if no configfile, the answer is always false !
	if filename == None:
		return False
	
	with open(filename) as f:
		parser = cp.SafeConfigParser()
		try:
			parser.readfp(f)
			hasVar = parser.has_option('main',var)
			return hasVar
		except cp.MissingSectionHeaderError:
			sys.stderr.write("Error: Config file seems to be invalid (Missing Section 'main')\n")
			exit(1)
	return False

def getConfigfile(filename,var):
	with open(filename) as f:
		parser = cp.SafeConfigParser()
		parser.readfp(f)
		return parser.get('main',var)
	return None
						
if __name__ == '__main__':

	# parse cmd line and options	
	(filenames, options) = parseArguments()
	token = options.token
	variable = options.variable

	# open sqlite file 
	db_file = filenames[0] # need only first arg wich is the db filename 
	con = sqlite3.connect(db_file)
	con.row_factory = sqlite3.Row # be able to access by row name ...
	
	# fetch all records ...
	measures = list()
	rows = con.execute("select date, kwatt from consumption order by date asc")
	start = None
	for row in rows:
		
		# skip first record
		if start == None:
			start = row['date']
			continue
	
		#print str(row["date"]) + ' > ' + str(row["kwatt"])
		#measures.append({'date': row["date"], 'kwatt': row["kwatt"]})
		measures.append(DurMeasurement(variable, start, row['date'], row['kwatt'] * units.KILOWATT_HOUR, options.time_uncertainty, options.time_uncertainty, options.uncertainty * units.KILOWATT_HOUR))
		
		start = row['date'] # store end date as start date for next record...
		
	#print len(measures)
	#print measures
		
		
	# init google load ...
	log = google_meter.Log(1)
	service = google_meter.Service(token, options.service, log=log)
	#service = google_meter.BatchAdapter(service)
	service.BatchPostEvents(measures) 

	#service.Flush()
	#meter = google_meter.Meter(
	#						   service, variable, options.uncertainty * units.KILOWATT_HOUR,
	#						   options.time_uncertainty, True)

	# for i in range(len(readings)/1000 + 1):
		# if len(readings) > 1000:
			# for j in range(1000):
				# reading = readings.pop()
				# start = rfc3339.FromTimestamp(reading.dStart.isoformat())
				# end = rfc3339.FromTimestamp(reading.dEnd.isoformat())
				# meter.PostDur(start,end,reading.energy * units.KILOWATT_HOUR,reading.uncertainty * units.KILOWATT_HOUR)
		# else:
			# for reading in readings:
				# start = rfc3339.FromTimestamp(reading.dStart.isoformat())
				# end = rfc3339.FromTimestamp(reading.dEnd.isoformat())
				# meter.PostDur(start,end,reading.energy * units.KILOWATT_HOUR,reading.uncertainty * units.KILOWATT_HOUR)
			# service.Flush()
			# break
		# service.Flush()
		# print "There remains %d measurements to upload." % len(readings)
		# for k in range(10):
			# print "Sleeping for %d minutes." % (10-k)
			# sleeptime.sleep(60)

	#
		# if len(times) <= 0:
			# sys.stderr.write('Error: Read input file, but never read the time header.\n')
			# sys.stderr.write("Ignoring file '%s'\n" % filename)
			# continue
		# if len(days) <= 0:
			# sys.stderr.write('Error: Read input file, but never parsed any electricity usage data.\n')
			# sys.stderr.write("Ignoring file '%s'\n" % filename)
			# continue

		# readings.extend(parseToReadings(times, days))
	
			
	# print "Info: Processed %d durational readings. Now attempting to upload to Google." % len(readings)

	

