
#!/usr/bin/python
import logging
import os
import time
import sys
import requests
import json
from bs4 import BeautifulSoup
import warnings



class Analyzer():
	def __init__(self, config, executionMode, rules):
		self.config = config
		self.executionMode = executionMode
		self.rules = rules
		self.logger = self.getLogger()
		self.alertLogger = self.getAlertLogger()

	def getLogger(self):
		logger = None
		if self.executionMode == "daemon":
			logger = logging.getLogger("ModOSINT-Analyzer-"+str(__name__))
		else:
			logger = logging.getLogger("ModOSINT-Analyzer-SimpleExecution-"+str(__name__))
		logger.setLevel(logging.INFO)
		logAnalyzerPath = os.path.join(str(os.path.split(self.config["logfile"])[0]), str(__name__))

		# create analyzer log path if dont exist (first step)
		if not os.path.exists(logAnalyzerPath):
			os.makedirs(logAnalyzerPath)
			if sys.version_info[0] == 2:
				# directory permission python2
				os.chmod(logAnalyzerPath, 0o755)
			if sys.version_info[0] == 3:
			# directory permission python3
				os.chmod(logAnalyzerPath, 0o755)

		handler = logging.FileHandler(os.path.join(logAnalyzerPath, str(__name__)+".log"))
		formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
		logger.addHandler(handler)
		handler.setFormatter(formatter)
		return logger

	def getAlertLogger(self):
		logger = None
		if self.executionMode == "daemon":
			logger = logging.getLogger("AlertLogger-"+str(__name__))
		else:
			logger = logging.getLogger("AlertLogger-SimpleExecution-"+str(__name__))
		logger.setLevel(logging.INFO)
		handler = logging.FileHandler(os.path.join(str(os.path.split(self.config["logfile"])[0]), str(__name__), str(__name__)+".alert"))
		logger.addHandler(handler)
		return logger


	def run(self):
		analyzerProcess = AnalyzerProcess(self.config, self.logger, self.alertLogger, self.rules, self.executionMode)
		# daemon execution (dont terminate process)
		if self.executionMode == "daemon":
			while True:
				# time interval to check
				time.sleep(5)
				analyzerProcess.run()
		# single execution
		if self.executionMode == "not-daemon":
			analyzerProcess.run()



class AnalyzerProcess():

	def __init__(self, config, loggerObject, alerLoggerObject, rules, executionMode):
		self.logger = loggerObject
		self.alertLogger = alerLoggerObject
		self.rules = rules
		self.config = config
		self.archive_pastebin = "https://pastebin.com/archive"
		self.url_pastebin = "https://pastebin.com"
		self.dictionary = []
		self.t_end=0
		self.word=""
		self.timeSearch = 30
		self.executionMode = executionMode
		warnings.filterwarnings("ignore", category=UserWarning, module='bs4')



	def createDictionary(self, string):
		for element in string:
			self.dictionary.append(element)
		return self.dictionary


	def filterSearch(self, rawText):
		for string in (self.dictionary):
			soup = BeautifulSoup(rawText, "html.parser")
			if string in soup.text:
				self.word= string
				return True
		return False


	def searchPastebin(self):
		if (self.executionMode == "daemon"):
			self.timeSearch = 15
		else:
			self.timeSearch = 30
		try:
			self.t_end = time.time() + self.timeSearch
			r = requests.get(self.archive_pastebin)
			if r.status_code == 200:  # request web OK
				soup = BeautifulSoup(r.text, "html.parser")  # Parse html last pastes
				table = soup.find("table", class_="maintable")  # get href to pastes
				fichero = open("/var/log/modosint/analyzer-pastebin/graylog.txt", "+a") 
				for tr in table.findAll("tr"):  # get element tr
					for td in tr.findAll("td"):  # get elementtd
						for a in td.findAll("a", href=True):  # get href content
							if "/archive" not in a["href"] and time.time()<self.t_end:  #only href from paste
								rr = requests.get(self.url_pastebin + str(a["href"]))  # request to paste
								if rr.status_code == 200:
									soup = BeautifulSoup(rr.text, "html.parser")
									raw_paste = soup.find("textarea", class_="paste_code")  # get content of textarea
									urlPaste = (self.url_pastebin + str(a["href"]))
									if self.filterSearch(raw_paste.text):
										pastebindata = {
											"URL":   urlPaste,
											"short_message":      raw_paste.text,
											"full_message" :  "Paste matched with WORD: " + self.word
										}
										autotweet=json.dumps(pastebindata)
										fichero.write(autotweet +'\n')
										os.chmod("/var/log/modosint/analyzer-pastebin/graylog.txt",0o777)
							else:
								self.alertLogger.info("Pastebin Analyzer Job Finished succesfully.")
								break
		except IndexError:
			error=True				
				


	
	# custom functionality
	def run(self):
		self.logger.info("working...")
		OSINTRules= self.rules
		for element in OSINTRules:
			try:
				self.createDictionary(element['_string'])
			except KeyError as e:
				pass
			try:
				self.createDictionary(element['_username'])
			except KeyError as e:
				pass
			try:
				self.createDictionary(element['_chat'])
			except KeyError as e:
				pass
			try:
				self.createDictionary(element['_hostname'])
			except KeyError as e:
				pass
			try:
				self.createDictionary(element['_net'])
			except KeyError as e:
				pass
		self.searchPastebin()
		self.alertLogger.info("Pastebin Analyzer Job Finished succesfully.")
