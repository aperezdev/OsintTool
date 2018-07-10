#!/usr/bin/python
import logging
import os
import time
import sys
import multiprocessing as mp
import graypy
import json
import datetime
import numpy as np
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
from PIL import Image
from os import path
from stop_words import get_stop_words
from telethon import TelegramClient
from telethon.tl.functions.messages import SearchRequest, GetFullChatRequest
from telethon.tl.types import InputMessagesFilterEmpty
from multiprocessing import Process



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
		self.api_id = "insert Telegram API ID"
		self.api_hash = "insert Telegram API HASH"
		self.phone_number = "insert phone number"
		self.num=30
		self.client= 'telegramClient'	
		self.currdir = "/home/centos/modosint-python3" + path.dirname(__file__)
		self.wcloud = ""
		self.executionMode = executionMode
		self.stop_words = get_stop_words('english')
		newStopWords = ["http","https","co","n'","'",'"',"Telegram","matched","with","word"]
		self.stop_words.extend(newStopWords)		

	
	def initTelegram(self):
		if(self.executionMode == "daemon"):
			try:
				self.client = TelegramClient('telegramOsint', self.api_id, self.api_hash).start()	
			except EOFError:
				sys.stdin = open(0)
				self.code = sys.stdin.read(1) #ask security code for start api
				self.client = TelegramClient('telegramOsint', self.api_id, self.api_hash).start(self.phone_number,self.code)
			except RuntimeError:
				sys.stdin = open(0)
				self.code = sys.stdin.read(1) #ask security code for start api
				self.client = TelegramClient('telegramOsint', self.api_id, self.api_hash).start(self.phone_number,self.code)
		else:
			self.client = TelegramClient('telegramOsint', self.api_id, self.api_hash).start()

	def searchTelegram(self,ruleId,string):
		f=open("/var/log/modosint/analyzer-telegram/cache.txt", 'a+')
		repeated = False
		filter = InputMessagesFilterEmpty()
		try:
			result = self.client(SearchRequest(
				    peer=self.chat,  # On which chat/conversation
				    q=self.search,  # What to search for
				    filter=filter,  # Filter to use (maybe filter for media)
				    min_date=None,  # Minimum date
				    max_date=None,  # Maximum date
				    offset_id=0,  # ID of the message to use as offset
				    add_offset=0,  # Additional offset
				    limit=int(self.num),  # How many results
				    max_id=0,  # Maximum message ID
				    min_id=0  # Minimum message ID
				))
		except ValueError:
			print('Search do not match with rule... Continue working...')
		archivo1 = open("/var/log/modosint/analyzer-telegram/result.txt", "w" , encoding='utf8')
		os.chmod("/var/log/modosint/analyzer-telegram/result.txt",0o777)
		archivo1.write(str(result).replace('"', "'"))
		archivo1.close()
		archivo=open("/var/log/modosint/analyzer-telegram/result.txt", "r" , encoding='utf8')
		resultMessages=archivo.readlines()
		archivo.close()
		y=1
		for x in range(0,50):
			try:
				try:
					messageid = resultMessages[0].split("Message(id=")[x+1].split(", ")[0].strip()
				except Exception as e:
					messageid = resultMessages[0].split("True, id=")[x+1].split(", ")[0].strip()
				f.seek(0) #read temporary file correctly			
				content = f.readlines()
				content = [x.strip('\n').strip('u') for x in content]
				for i in range(len(content)):
					if messageid in content:
						repeated=True
					else:
						repeated=False
				if repeated==False:
					title = resultMessages[0].split("title='")[x+1].split("', ")[0]
					try:
					    body = resultMessages[0].split("description='")[x+1].split("', ")[0]
					except IndexError:
					    body =  None
					try:
					    url = resultMessages[0].split("display_url='")[x+1].split("', ")[0]
					    url = "http://" + url
					except IndexError:
					    url =  None
					try:
					    created = resultMessages[0].split("date=datetime.utcfromtimestamp")[y].split(", ")[0]
					    y = y + 2
					    created = created.split("(")[1].split(")")[0]
					    created = datetime.datetime.fromtimestamp(int(created)).strftime('%Y-%m-%d %H:%M:%S')
					except IndexError:
					    created = None
					views = resultMessages[0].split("views=")[x+1].split(", ")[0]		
					try:
					    sitename= resultMessages[0].split("site_name=")[x+1].split(", ")[0]
					except IndexError:
					    sitename = None
					f.seek(0, 2) #write temporary file correctly
					f.write(messageid + '\n')
					telegramdata = {
					    "MessageId": messageid,
					    "TitleMessage": title,
					    "URL": url,
					    "CreatedTime": created,
					    "MessageViews": views,
					    "SiteName": sitename,
					    "short_message": body,
					    "Chat": self.chat,
					    "full_message": "Telegram matched with WORD: " + self.search
					}
					fichero = open("/var/log/modosint/analyzer-telegram/graylog.txt", "+a")
					autotelegram = json.dumps(telegramdata)
					fichero.write(autotelegram + '\n')
					os.chmod("/var/log/modosint/analyzer-telegram/graylog.txt",0o777)
					self.wcloud.write(str(telegramdata['short_message'])+'\n')
					os.chmod("/var/log/modosint/analyzer-telegram/wcloudRule"+ruleId+"-"+self.search+".txt",0o777)
			except IndexError:
				error=True

	def create_wordcloud(self,text,ruleId,string):
		mask = np.array(Image.open(path.join(self.currdir, "telegram_mask.png")))
		# create wordcloud object
		wc = WordCloud(background_color="white",
					max_words=200, 
					mask=mask,
		       	stopwords=self.stop_words)
		try:
			# generate wordcloud
			wc.generate(text)
			# save wordcloud
			wc.to_file(path.join(self.currdir + "/WordCloud/Telegram/", "wcTelegramRule" +ruleId +"-"+string+ ".png"))
			os.chmod(path.join(self.currdir + "/WordCloud/Telegram/", "wcTelegramRule" +ruleId +"-"+string+ ".png"),0o777)
		except ValueError as e:
			error=True
		

	# custom functionality
	def run(self):
		self.logger.info("working...")
		self.initTelegram()
		OSINTRules= self.rules
		for element in OSINTRules:
			checkChat=element.get('_chat', False)
			checkString=element.get('_string', False)
			if checkChat:
				self.chat = ('' .join(element['_chat']))
			if checkString and checkChat:
				for _string in element['_string']:
					string = ('' .join(_string))
					self.search=string
					ruleId = element.get('metadata', False).get('id',False)
					self.wcloud = open("/var/log/modosint/analyzer-telegram/wcloudRule"+ruleId+"-"+string+".txt", "+a")
					self.searchTelegram(ruleId,string)
					if not os.path.exists(self.currdir + "/WordCloud"):
						os.makedirs(self.currdir + "/WordCloud/")
						os.chmod(self.currdir + "/WordCloud/",0o777)
					if not os.path.exists(self.currdir + "/WordCloud/Telegram"):
						os.makedirs(self.currdir + "/WordCloud/Telegram/")
						os.chmod(self.currdir + "/WordCloud/Telegram/",0o777)
					file_content = open("/var/log/modosint/analyzer-telegram/wcloudRule"+ruleId+"-"+string+".txt", "r")
					file_content= file_content.readlines()
					self.create_wordcloud(str(file_content),ruleId,string)
					self.alertLogger.info("Telegram Analyzer Job Finished succesfully.")
