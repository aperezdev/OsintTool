#!/usr/bin/python
import logging
import os
import time
import sys
import requests
import json
import numpy as np
import warnings
from wordcloud import WordCloud, STOPWORDS
from PIL import Image
from os import path
from bs4 import BeautifulSoup
from stop_words import get_stop_words
from os import path

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
		self.url_foro = "https://forocoches.com"
		self.dictionary = []
		self.t_end=0
		self.word=""
		self.executionMode = executionMode
		self.timeSearch = 60
		self.wcloud = ""
		self.currdir = "/home/centos/modosint-python3" + path.dirname(__file__)
		self.stop_words = get_stop_words('spanish')
		newStopWords = ["http","https","co","n'","'",'"','Cita','tOriginalmente','Escrito']
		self.stop_words.extend(newStopWords)			
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


	def searchForo(self):
		if (self.executionMode == "daemon"):
			self.timeSearch = 15
		else:
			self.timeSearch = 30
		try:
			self.t_end = time.time() + self.timeSearch
			r = requests.get(self.url_foro)
			if r.status_code == 200:  # Consulta web OK
				soup = BeautifulSoup(r.text, "html.parser")  # Parseo html ultimos pastes
				table = soup.find("table", class_="cajasnews")  # Obtengo table de enlaces a pastes
				fichero = open("/var/log/modosint/analyzer-forocoches/graylog.txt", "+a") 
				for tr in table.findAll("tr"):  # Obtengo elemento tr
					for td in tr.findAll("td"):  # Obtengo elemento td
						for a in td.findAll("a",href=True):  # Obtengo contenido de href
							foro_href = soup.findAll("a", class_="texto")
							for a in foro_href:
								urlForo=self.url_foro + (str(a["href"]))
								rr = requests.get(self.url_foro + str(a["href"]))  # Consulto paste de enlace obtenido
								if time.time()<self.t_end:
									if rr.status_code == 200:
										soup = BeautifulSoup(rr.text, "html.parser")
										title = str(soup)
										try:
											title = title.split('<!-- icon and title -->')[1].split('</div>')[0].strip()
											title = title.split('<div class="smallfont">')[1].strip()
											cleantitle = title.split('<strong>')[1].split('</strong>')[0].strip()
										except IndexError:
											pass
										x = 1
										y = 0
										usernames = []
										for a in soup.findAll("a",class_="bigusername"):
											usernames.append(str(a.text))
										for x in range(40):
											try:
												text = str(soup)
												text = text.split('style="word-wrap:break-word;"></div>')[x + 1].split('/div></div>')[0].strip()
												cleantext = BeautifulSoup(text, "lxml").text
												if self.filterSearch(cleantext):
													forodata = {
													"URL":   urlForo,
													"short_message":      cleantext,
													"full_message" :  "Paste matched with WORD: " + self.word,
													"username" : usernames[y],
													"title" : cleantitle
													}
													self.wcloud.write(cleantext+'\n')
													autoforo=json.dumps(forodata)
													fichero.write(autoforo +'\n')
													os.chmod("/var/log/modosint/analyzer-forocoches/graylog.txt",0o777)
													y=y+1
												else:
													y=y+1
											except IndexError:
												break
								else:
									self.alertLogger.info("Forocoches Analyzer Job Finished succesfully.")
									break
		except (ProcessLookupError,ConnectionError):
			error= True


	def create_wordcloud(self,text):
		mask = np.array(Image.open(path.join(self.currdir, "foro_mask.png")))
		# create wordcloud object
		wc = WordCloud(background_color="white",
					max_words=200, 
					mask=mask,
		       	stopwords=self.stop_words)
		try:
			# generate wordcloud
			wc.generate(text)
			# save wordcloud
			wc.to_file(path.join(self.currdir + "/WordCloud/Forocoches/", "wcForocoches" + ".png"))
			os.chmod(path.join(self.currdir + "/WordCloud/Forocoches/", "wcForocoches"+".png"),0o777)
		except ValueError as e:
			error=True

	
	# custom functionality
	def run(self):
		self.logger.info("working...")
		OSINTRules= self.rules
		for element in OSINTRules:
			self.wcloud = open("/var/log/modosint/analyzer-forocoches/wcForocoches"+".txt", "a+")
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
		self.searchForo()
		self.alertLogger.info("Forocoches Analyzer Job Finished succesfully.")
		if not os.path.exists(self.currdir + "/WordCloud"):
			os.makedirs(self.currdir + "/WordCloud/")
			os.chmod(self.currdir + "/WordCloud/",0o777)
		if not os.path.exists(self.currdir + "/WordCloud/Forocoches"):
			os.makedirs(self.currdir + "/WordCloud/Forocoches/")
			os.chmod(self.currdir + "/WordCloud/Forocoches/",0o777)
		file_content = open("/var/log/modosint/analyzer-forocoches/wcForocoches"+".txt", "r")
		file_content= file_content.readlines()
		self.create_wordcloud(str(file_content))
		self.alertLogger.info("Forocoches Analyzer Job Finished succesfully.")
