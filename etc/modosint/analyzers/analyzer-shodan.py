#!/usr/bin/python
import logging
import os
import time
import sys
import shodan
import json



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
		analyzerProcess = AnalyzerProcess(self.config, self.logger, self.alertLogger, self.rules)
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

	def __init__(self, config, loggerObject, alerLoggerObject, rules):
		self.logger = loggerObject
		self.alertLogger = alerLoggerObject
		self.rules = rules
		self.config = config
		self.SHODAN_API_KEY = "insert here Shodan API KEY"
		self.api = shodan.Shodan(self.SHODAN_API_KEY)
		self.idRule=0
		self.string=""
		self.hostname=""
		self.net=""
		self.os=""
		self.country=""
		self.query=""
				
	def searchShodan(self,rule,IdRule):
		self.query=""
		self.hostname=""
		self.net=""
		self.string=""
		# Wrap the request in a try/ except block to catch errors
		try:
			try:
				self.string=(' '.join(rule['_string']))
			except KeyError:
				pass
			try:
				self.hostname=(' '.join(rule['_hostname']))
			except KeyError:
				pass
			try:
				self.net=(' '.join(rule['_net']))
			except KeyError:
				pass
			# Search Shodan
			if self.hostname is not "":
				self.query=self.query + ' hostname:'+self.hostname
			if self.net is not "":
				self.query= self.query + ' net:'+self.net
			if self.string is not "":
				self.query= self.query + ' '+ self.string
			results = self.api.search(self.query)
			for result in results['matches']:
				shodandata = {
					"TotalResults": results['total'],
					"IP": result['ip_str'],
					"short_message": result['data'],
					"hostname": result['hostnames'],
					"SO": result['os'],
					"port": result['port'],
					"DateTime": result['timestamp'],
					"Rule": IdRule,
					"full_message": "Shodan Query: " + self.query
				}
				fichero = open("/var/log/modosint/analyzer-shodan/graylog.txt", "+a")
				autoshodan= json.dumps(shodandata)
				fichero.write(autoshodan + '\n')
				os.chmod("/var/log/modosint/analyzer-shodan/graylog.txt",0o777)
		except shodan.APIError as e:
			self.alertLogger.info('Error: {}'.format(e))

	
	# custom functionality
	def run(self):
		self.logger.info("working...")
		OSINTRules= self.rules
		lista= list(OSINTRules)
		x=0
		for i in range(len(lista)):
			self.idRule = lista[x]['metadata']['id']
			lista[x].pop('metadata')
			self.searchShodan(lista[x],self.idRule)
			x=x+1
		self.alertLogger.info("Shodan Analyzer Job Finished succesfully.")
