#!/usr/bin/python
import logging
import os
import time
import sys

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

	# custom functionality
	def run(self):
		self.logger.info("working...")
		self.alertLogger.info("{'alert':'True', 'rule':'match'}")