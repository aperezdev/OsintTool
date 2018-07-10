#!/usr/bin/python
import os,glob
import sys
from datetime import datetime
import time
from multiprocessing import Process, TimeoutError
import logging
import daemon
import signal
import argparse
from daemon import runner


class ModOSINT():
	def __init__(self):
		if executionMode == "daemon":
			self.stdin_path			= '/dev/null'
			self.stdout_path		= '/dev/tty'
			self.stderr_path		= os.path.join(os.path.split(config["logfile"])[0], os.path.split(config["logfile"])[1].split(".")[0]+"-debug.log")
			self.pidfile_path		= config["pidfile"]
			self.pidfile_timeout	= 5

	# Running core...
	def run(self):
		signal.signal(signal.SIGHUP, signalHandler)
		signal.signal(signal.SIGINT, signalHandler)
		signal.signal(signal.SIGUSR1, signalHandler)

		isWorking = startAnalyzers(OSINTRules, executionMode, config)
		if isWorking and executionMode == "daemon":
			while True:
				checkProcessAlive()
				time.sleep(10)

# helpers
def validateRule(osintRule, idList):
	isNotValid = False

	# rule start
	if osintRule[0:5] == "rule ":
		isNotValid = False
	elif osintRule[0:5] == "#rule":
		logger.info("commented rule (it wont be loaded): "+osintRule.strip())
		isNotValid = True
	elif osintRule[0:5] != "rule ":
		logger.error("invalid begin of rule: "+osintRule.strip())
		isNotValid = True

	# its posible to parse id attribute
	try:
		idAux = osintRule.split("id:")[1].split(";")[0].strip()
		if idAux in idList:
			logger.error("duplicated id rule: "+osintRule.strip())
			isNotValid = True
		else:
			idList.append(idAux)
	except:
		logger.error("parsing id rule: "+osintRule.strip())
		isNotValid = True

	# its posible to parse msg attribute
	try:
		msgAux = osintRule.split("msg:")[1].split(";")[0].strip()
	except:
		logger.error("parsing msg attribute: "+osintRule.strip())
		isNotValid = True

	# its posible to parse daterevision attribute and it is in correct date format
	try:
		dateAux = osintRule.split("daterevision:")[1].split(";")[0].strip()
		if dateAux != "":
			try:
				auxDateTime = datetime.strptime(dateAux, "%d/%m/%Y")
			except:
				logger.warning("parsing daterevision attribute, right date format? (dd/mm/YYYY), wrong daterevision will be ignored: "+osintRule.strip())
	except:
		logger.info("parsing daterevision attribute"+osintRule.strip())
		isNotValid = True

	# its posible to parse search expresion
	try:
		expresionListAux = osintRule.split("expr:(")[1].split(");")[0].strip().split(";")
		if len(expresionListAux) < 2:
			logger.error("invalid search expresion: "+osintRule.strip())
			isNotValid = True
		else:
			for expr in expresionListAux[:-1]:
				if ":" in expr:
					key = expr.split(":")[0].strip()
					value = expr.split(":")[1].strip()
					if key == "" or key == " " or value == "" or value == " ":
						logger.error("invalid search expresion: "+osintRule.strip())
						isNotValid = True
				else:
					logger.error("invalid search expresion: "+osintRule.strip())
					isNotValid = True
	except:
		logger.error("parsing search expresion: "+osintRule.strip())
		isNotValid = True

	#final condition
	if isNotValid == True:
		return False, []
	else:
		return True, idList

def parseRule(osintRule):
	idRule = osintRule.split("id:")[1].split(";")[0].strip()
	msgRule = osintRule.split("msg:")[1].split(";")[0].strip()
	dateRevisionRule = osintRule.split("daterevision:")[1].split(";")[0].strip()
	if dateRevisionRule != "":
		try:
			datetime.strptime(dateRevisionRule, "%d/%m/%Y")
		except:
			dateRevisionRule = ""
	expresionList = osintRule.split("expr:(")[1].split(");")[0].strip().split(";")

	metadata = {
		"id"			: idRule,
		"msg"			: msgRule,
		"daterevision"	: dateRevisionRule
	}
	osintRuleStruct = {
		"metadata"	: metadata
	}

	for expr in expresionList:
		if ":" in expr:
			key = expr.split(":")[0].strip()
			value = expr.split(":")[1].strip()
			if key not in osintRuleStruct.keys():
				newItem = []
				newItem.append(value)
				osintRuleStruct[key] = newItem
			else:
				osintRuleStruct[key].append(value)

	return osintRuleStruct

def loadRules():
	rulesFilesList = []
	OSINTRules = []
	idList = []
	for rf in os.listdir(config["rulespath"]):
		if os.path.isfile(os.path.join(config["rulespath"], rf)):
			if ".rules" == str(rf[-6:]):
				rulesFilesList.append(rf)
	
	for rulesfile in rulesFilesList:
		rfo = open(os.path.join(config["rulespath"], rulesfile), 'r')
		fullLines = rfo.readlines()
		rfo.close()

		for line in fullLines:
			isValid, idList = validateRule(line.strip(), idList)
			if isValid:
				OSINTRules.append(parseRule(line.strip()))

	return OSINTRules

def importAnalyzer(analyzerName):
	module = __import__(analyzerName.strip(".py"))
	return module

def checkProcessAlive():
	processDiedListAux = []
	for i in range(len(processList)):
		if processList[i].is_alive() == False:
			processDiedListAux.append(processList[i])
			logger.error(processList[i].name+" analyzer is dead... its possible that an error occurred... see 'modosint-debug.log' for more details")
	# update process list
	for processDied in processDiedListAux:
		moduleIndex = processList.index(processDied)
		processList.remove(processDied)
		del modulesList[moduleIndex]
	# check if there are some process alive
	if len(processList) == 0:
		logger.info("there are not any analyzer living... exiting...")
		stopAnalyzers(processList)

def startAnalyzers(rules, execMode, config):
	logger.info("starting analyzers...")
	analyzersList = []
	for an in os.listdir(os.path.join(os.path.split(config["configfile"])[0], "analyzers")):
		if os.path.isfile(os.path.join(os.path.join(os.path.split(config["configfile"])[0], "analyzers"), an)):
			if ".py" == str(an[-3:]):
				analyzersList.append(an)

	for analyzer in analyzersList:
		# dont load analyzer example (analyzer base for build our custom analyzers)
		if analyzer != "analyzer-base.py":
			module = importAnalyzer(analyzer)

			if module != None:
				analyzerObject = module.Analyzer(config, execMode, rules)
				#p = Process(name=analyzer.strip(".py"), target=module.run, args=(rules,execMode,config,))
				p = Process(name=analyzer.strip(".py"), target=analyzerObject.run)
				p.start()
				processList.append(p)
				modulesList.append(module)
				logger.info(analyzer + " analyzer running...")

	if len(processList) == 0:
		return False
	return True

def reloadAnalyzersRules(processList, modulesList, execMode, config):
	if executionMode == "daemon":
		logger.info("reloading OSINT rules...")
		OSINTRules = loadRules()
		if len(OSINTRules) == 0:
			logger.warning("no rules to load (0 valid rules)")
			stopAnalyzers(processList)
		else:
			logger.info(str(len(OSINTRules))+" rules loaded successfully")
			for i in range(len(processList)):
				analyzerObject = modulesList[i].Analyzer(config, execMode, OSINTRules)
				processList[i].terminate()
				os.kill(int(processList[i].pid), signal.SIGKILL)
				processList[i] = Process(name=processList[i].name, target=analyzerObject.run)
				processList[i].start()
				logger.info(processList[i].name + ".py analyzer continues running...")
	return processList

def stopAnalyzers(processList):
	logger.info("stop signal received")
	for p in processList:
		try:
			logger.info("stopping "+str(p.name)+" analyzer...")
			p.terminate()
			os.kill(int(p.pid), signal.SIGKILL)
		except ProcessLookupError:
			logger.error("Process Lookup Error when stopped analyzer")	
	#delete caches and wcloud archives
	try:
		os.remove("/var/log/modosint/analyzer-twitter/cache.txt")
		os.remove("/var/log/modosint/analyzer-telegram/cache.txt")
		for filename in glob.glob("/var/log/modosint/analyzer-telegram/wcloud*"):
			os.remove(filename)
		for filename in glob.glob("/var/log/modosint/analyzer-twitter/wcloud*"):
			os.remove(filename)
		for filename in glob.glob("/var/log/modosint/analyzer-forocoches/wc*"):
			os.remove(filename)
	except FileNotFoundError:
		logger.error("Cache archives already deleted")	
	modulesList = []
	processList = []
	logger.info("ModOSINT exiting...")
	sys.exit()



if __name__ == '__main__':
	# parse arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("-D", "--daemon", help="exec tool as a daemon service")
	parser.add_argument("-c", "--config", help="config file path for normal exec tool")
	args = parser.parse_args()

	# global variables
	processList = []
	modulesList = []
	OSINTRules = []
	executionMode = ""
	config = {
		"configfile": "",
		"pidfile"	: "",
		"logfile"	: "",
		"rulespath"	: ""
	}

	# daemon signal handler
	def signalHandler(sig, frame):
		if sig == signal.SIGHUP:
			reloadAnalyzersRules(processList, modulesList, executionMode, config)
		elif sig == signal.SIGINT or sig == signal.SIGUSR1:
			stopAnalyzers(processList)

	# parse config file
	def readConfiguration(execMode, configPath):
		config["configfile"] = configPath
		configFile = open(configPath, "r")
		configLines = configFile.readlines()
		configFile.close()

		# read options
		for line in configLines:
			if "pidfile:" in line:
				config["pidfile"] = line.split(":")[1].strip()
			if "logfile:" in line:
				config["logfile"] = line.split(":")[1].strip()
			if "rulespath:" in line:
				config["rulespath"] = line.split(":")[1].strip()

		# exec mode can be daemon or not-daemon
		# if exec mode is not daemon, wont be neccessary pidfile attribute 
		if execMode == "daemon":
			if config["pidfile"] == "":
				print ("FATAL ERROR in configuration file. Where is the pidfile path? (its a mandatory attribute with daemon option)")
				return False
		if config["logfile"] == "":
			print ("FATAL ERROR in configuration file. Where is the logfile path?")
			return False
		if config["rulespath"] == "":
			print ("FATAL ERROR in configuration file. Where is the rules path?")
			return False

		# check if files and directories exists
		if os.path.exists(config["rulespath"]) == False:
			print ("FATAL ERROR in configuration file. Rules path dont exist.")
			return False
		if os.path.exists(str(os.path.split(config["logfile"])[0])) == False:
			print ("FATAL ERROR in configuration file. Logfile path dont exist.")
			return False
		if os.path.exists(str(os.path.split(config["pidfile"])[0])) == False and execMode == "daemon":
			print ("FATAL ERROR in configuration file. Pidfile path dont exist.")
			return False

		# configuration is correct
		return True


	if args.daemon and args.config:
		if args.daemon == "start" and readConfiguration("daemon", args.config):
			# check if daemon is already running
			if os.path.exists(config["pidfile"]) or os.path.exists(config["pidfile"]+".lock"):
				print ("FATAL ERROR daemon is already running.")
				sys.exit()
			# sys.argv modify its needed for invoke daemon-python
			# ex: script.py start
			executionMode = "daemon"
			sys.path.append(os.path.join(os.path.split(config["configfile"])[0], "analyzers"))
			sys.argv = [sys.argv[0], args.daemon]
			modosint = ModOSINT()
			logger = logging.getLogger("ModOSINT-Core")
			logger.setLevel(logging.INFO)
			handler = logging.FileHandler(config["logfile"])
			formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
			logger.addHandler(handler)
			handler.setFormatter(formatter)
			serv = runner.DaemonRunner(modosint)
			serv.daemon_context.files_preserve=[handler.stream]

			logger.info("loading OSINT rules...")
			OSINTRules = loadRules()
			if len(OSINTRules) == 0:
				logger.warning("no rules to load (0 valid rules)")
			else:
				logger.info(str(len(OSINTRules))+" rules loaded successfully")

			serv.do_action()

	elif args.config:
		if readConfiguration("not-daemon", args.config):
			executionMode = "not-daemon"
			sys.path.append(os.path.join(os.path.split(config["configfile"])[0], "analyzers"))
			modosint = ModOSINT()
			logger = logging.getLogger("ModOSINT-Core-SimpleExecution")
			logger.setLevel(logging.INFO)
			handler = logging.FileHandler(config["logfile"])
			formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
			logger.addHandler(handler)
			handler.setFormatter(formatter)

			logger.info("loading OSINT rules...")
			OSINTRules = loadRules()
			if len(OSINTRules) == 0:
				logger.warning("no rules to load (0 valid rules)")
			else:
				logger.info(str(len(OSINTRules))+" rules loaded successfully")

			modosint.run()

	else:
		print("""
                        _           _       _                     _ 
           ___    ___  (_)  _ __   | |_    | |_    ___     ___   | |
          / _ \  / __| | | | '_ \  | __|   | __|  / _ \   / _ \  | |
         | (_) | \__ \ | | | | | | | |_    | |_  | (_) | | (_) | | |
          \___/  |___/ |_| |_| |_|  \__|    \__|  \___/   \___/  |_| """)

		print("/*-------------------------------------------------------------------------*\\")
		print("| 			--   Osint Tool --              		    |")
		print("|            Collecting Data from public available sources                  |")
		print("|                                                                           |")
		print("|     Actually working with Twitter,Telegram,Pastebin,Forocoches and Shodan |")
		print("|                                                                           |")
		print("| 			Author: @AlvaroPerez_2                              |")
		print("\*-------------------------------------------------------------------------*/\n")
		print("simple execution usage: python3.6 modosint.py -c /etc/modosint/modosint.conf")
		print("daemon execution usage: python3.6 modosint.py -c /etc/modosint/modosint.conf -D start")
