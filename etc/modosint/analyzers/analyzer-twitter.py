#!/usr/bin/python
import logging
import os
import io
import time
import tempfile
import sys
import self
import twitter
import json
import re
import emoji
import graypy
import matplotlib.pyplot as plt
import numpy as np
import datetime
import pandas as pd
import itertools
import seaborn as sns
from stop_words import get_stop_words
from dateutil import parser
from wordcloud import WordCloud, STOPWORDS
from PIL import Image
from os import path
from datetime import timedelta
from twarc import Twarc
from googletrans import Translator
from emoji.unicode_codes import UNICODE_EMOJI



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
		self.executionMode = executionMode
		self.access_token = "insert Twitter API access token"
		self.access_token_secret = "insert Twitter API token secret"
		self.consumer_key = "insert Twitter API consumer key"
		self.consumer_secret = "insert Twitter API consumer secret"
		self.twarc = Twarc(self.consumer_key, self.consumer_secret, self.access_token, self.access_token_secret)
		self.currdir = "/home/centos/modosint-python3" + path.dirname(__file__)
		self.wcloud = ""
		self.stop_words = get_stop_words('spanish')
		newStopWords = ["http","https","co","n'","'",'"']
		self.stop_words.extend(newStopWords)

    	#Search Tweets that contais term in different Language
	def searchDifLanguage(self, text, language, ruleId):
		fichero = open("/var/log/modosint/analyzer-twitter/graylog.txt", "+a",encoding='utf8')
		with io.open("/var/log/modosint/analyzer-twitter/cache.txt", 'a+') as f:
			os.chmod("/var/log/modosint/analyzer-twitter/cache.txt",0o777)
			traductor = Translator()
			translatedText = traductor.translate(text, dest=language)
			repeated=False
			if self.executionMode == "daemon":	
				searchDif = self.twarc.search(translatedText.text)
				for tweet in searchDif:
					tweetTime = parser.parse(''.join(tweet['created_at']))
					timeFormed = time.strptime(str(tweetTime.time()).split(',')[0], '%H:%M:%S')
					createdAtSeconds= datetime.timedelta(hours=timeFormed.tm_hour,minutes=timeFormed.tm_min,seconds=timeFormed.tm_sec).total_seconds()
					nowTimeUtc = datetime.datetime.utcnow().time()
					nowTimeFormed = time.strptime(str(nowTimeUtc).split('.')[0], '%H:%M:%S')
					nowTimeSeconds = datetime.timedelta(hours=nowTimeFormed.tm_hour, minutes=nowTimeFormed.tm_min, seconds=nowTimeFormed.tm_sec).total_seconds()
					if (nowTimeSeconds - createdAtSeconds < 300): #time in 5 minutes	
						if 'retweeted_status' not in tweet: #avoid RT
							f.seek(0) #read temporary file (cache)		
							content = f.readlines()
							content = [x.strip('\n').strip('u') for x in content]
							for i in range(len(content)):
								if tweet['id_str'] in content:
									repeated=True
								else:
									repeated=False
							if repeated == False:
								f.seek(0, 2) #write temporary file (cache)
								f.write(tweet['id_str'])
								f.write('\n')
						
								texto = tweet['full_text']

								for c in texto:
									if c in emoji.UNICODE_EMOJI: 
										texto=texto.replace(c,"")
								texto = u'' + texto
								try:
									emoji_pattern = re.compile(
										u"(\ud83d[\ude00-\ude4f])|"  # emoticons
										u"(\ud83c[\udf00-\uffff])|"  # symbols & pictographs (1 of 2)
										u"(\ud83d[\u0000-\uddff])|"  # symbols & pictographs (2 of 2)
										u"(\ud83d[\ude80-\udeff])|"  # transport & map symbols
										u"(\U0001F1E0-\U0001F1FF])|"
										u"(\U0001F600-\U0001F64F])|"  # emoticons 2
										u"(\U0001F300-\U0001F5FF])|"  # symbols & pictographs
										u"(\U0001F680-\U0001F6FF])|"
										u"(\u2600-\u26FF])|"
										u"(\U0001F1F2\U0001F1F4)|"       # Macau flag
										u"([\U0001F1E6-\U0001F1FF]{2})|" # flags
										u"([\U0001F600-\U0001F64F])"    # emoticons 3		
										u"(\ud83c[\udde0-\uddff])"  # flags (iOS)
										"+", flags=re.UNICODE)
									resultesp = traductor.translate(emoji_pattern.sub(r'', texto), dest='es')
								except ValueError:
									self.my_logger.debug('[Emoji Error] Tweet can not be translated. Unrecognized emoji in tweet.')
								tweetdata = {
									"CreatedTime":   tweet['created_at'],
									"short_message":      tweet['full_text'],
									"TranslatedTweet":	resultesp.text,
									"Author" :      tweet['user']['screen_name'],
									"Retweets" :    tweet['retweet_count'],
									"Likes" :       tweet['favorite_count'],
									"Location" :    tweet['user']['location'],
									"Rule" : 	ruleId,
									"full_message" :  "Tweet matched with RULE: " + ruleId
								}
								autotweet=json.dumps(tweetdata)
								fichero.write(autotweet +'\n')
								self.wcloud.write(resultesp.text+'\n')
								os.chmod("/var/log/modosint/analyzer-twitter/wcloudRule"+ruleId+".txt",0o777)
								os.chmod("/var/log/modosint/analyzer-twitter/graylog.txt",0o777)
					else:
						break

			else:	
				searchDif = self.twarc.search(translatedText.text)
				for tweet in searchDif:
					tweetTime = ''.join(tweet['created_at'])
					datetweet = parser.parse(tweetTime )
					if(datetweet.date()== datetime.datetime.now().date() or datetweet.date()== (datetime.datetime.now().date()-timedelta(1))):
						if 'retweeted_status' not in tweet: #avoid RT
							f.seek(0) #read temporary file (cache)
							content = f.readlines()
							content = [x.strip('\n').strip('u') for x in content]
							for i in range(len(content)):
								if tweet['id_str'] in content:
									repeated=True
								else:
									repeated=False
							if repeated == False:
								f.seek(0, 2) #write temporary file (cache)
								f.write(tweet['id_str'])
								f.write('\n')
						
								texto = tweet['full_text']

								for c in texto:
									if c in emoji.UNICODE_EMOJI: 
										texto=texto.replace(c,"")
								texto = u'' + texto
								try:
									emoji_pattern = re.compile(
										u"(\ud83d[\ude00-\ude4f])|"  # emoticons
										u"(\ud83c[\udf00-\uffff])|"  # symbols & pictographs (1 of 2)
										u"(\ud83d[\u0000-\uddff])|"  # symbols & pictographs (2 of 2)
										u"(\ud83d[\ude80-\udeff])|"  # transport & map symbols
										u"(\U0001F1E0-\U0001F1FF])|"
										u"(\U0001F600-\U0001F64F])|"  # emoticons 2
										u"(\U0001F300-\U0001F5FF])|"  # symbols & pictographs
										u"(\U0001F680-\U0001F6FF])|"
										u"(\u2600-\u26FF])|"
										u"(\U0001F1F2\U0001F1F4)|"       # Macau flag
										u"([\U0001F1E6-\U0001F1FF]{2})|" # flags
										u"([\U0001F600-\U0001F64F])"    # emoticons 3		
										u"(\ud83c[\udde0-\uddff])"  # flags (iOS)
										"+", flags=re.UNICODE)
									resultesp = traductor.translate(emoji_pattern.sub(r'', texto), dest='es')
								except ValueError:
									self.my_logger.debug('[Emoji Error] Tweet can not be translated. Unrecognized emoji in tweet.')
								tweetdata = {
									"CreatedTime":   tweet['created_at'],
									"short_message":      tweet['full_text'],
									"TranslatedTweet":	resultesp.text,
									"Author" :      tweet['user']['screen_name'],
									"Retweets" :    tweet['retweet_count'],
									"Likes" :       tweet['favorite_count'],
									"Location" :    tweet['user']['location'],
									"Rule" : 	ruleId,
									"full_message" :  "Tweet matched with RULE: " + ruleId
								}
								autotweet=json.dumps(tweetdata)
								fichero.write(autotweet +'\n')
								self.wcloud.write(resultesp.text+'\n')
								os.chmod("/var/log/modosint/analyzer-twitter/wcloudRule"+ruleId+".txt",0o777)
								os.chmod("/var/log/modosint/analyzer-twitter/graylog.txt",0o777)
					else:
						break			

    	#Search Tweets that contains term or Hashtag
	def searchTweetOrHashtag(self, text, ruleId):
		fichero = open("/var/log/modosint/analyzer-twitter/graylog.txt", "+a", encoding='utf8') 
		with io.open("/var/log/modosint/analyzer-twitter/cache.txt", 'a+') as f:
			os.chmod("/var/log/modosint/analyzer-twitter/cache.txt",0o777)
			repeated=False
			if self.executionMode == "daemon":
				tweets=self.twarc.search(text)
				for tweet in tweets:
					tweetTime = parser.parse(''.join(tweet['created_at']))
					timeFormed = time.strptime(str(tweetTime.time()).split(',')[0], '%H:%M:%S')
					createdAtSeconds= datetime.timedelta(hours=timeFormed.tm_hour,minutes=timeFormed.tm_min,seconds=timeFormed.tm_sec).total_seconds()
					nowTimeUtc = datetime.datetime.utcnow().time()
					nowTimeFormed = time.strptime(str(nowTimeUtc).split('.')[0], '%H:%M:%S')
					nowTimeSeconds = datetime.timedelta(hours=nowTimeFormed.tm_hour, minutes=nowTimeFormed.tm_min, seconds=nowTimeFormed.tm_sec).total_seconds()
					if (nowTimeSeconds - createdAtSeconds < 300): #time in 5 minutes			
						if 'retweeted_status' not in tweet: #avoid RT
							f.seek(0) #read temporary file (cache)
							content = f.readlines()
							content = [x.strip('\n').strip('u') for x in content]
							for i in range(len(content)):
								if tweet['id_str'] in content:
									repeated=True
								else:
									repeated=False
							if repeated == False:
								f.seek(0, 2) #write temporary file (cache)
								f.write(tweet['id_str']+'\n')
								tweetdata = {
									"CreatedTime":   tweet['created_at'],
									"short_message":      tweet['full_text'],
									"Author" :      tweet['user']['screen_name'],
									"Retweets" :    tweet['retweet_count'],
									"Likes" :       tweet['favorite_count'],
									"Location" :    tweet['user']['location'],
									"Rule" : 	ruleId,
									"full_message" :  "Tweet matched with RULE: " + ruleId
								}
								autotweet=json.dumps(tweetdata)
								fichero.write(autotweet +'\n')
								self.wcloud.write(tweet['full_text']+'\n')
								os.chmod("/var/log/modosint/analyzer-twitter/wcloudRule"+ruleId+".txt",0o777)
								os.chmod("/var/log/modosint/analyzer-twitter/graylog.txt",0o777)
					else:
						break

			else:
				tweets=self.twarc.search(text)
				for tweet in tweets: #no daemon(tweets in this day and yesterday)
					tweetTime = ''.join(tweet['created_at'])
					datetweet = parser.parse(tweetTime )
					if(datetweet.date()== datetime.datetime.now().date() or datetweet.date()== (datetime.datetime.now().date()-timedelta(1))):
						if 'retweeted_status' not in tweet: #avoid RT
							f.seek(0) #read temporary file (cache)
							content = f.readlines()
							content = [x.strip('\n').strip('u') for x in content]
							for i in range(len(content)):
								if tweet['id_str'] in content:
									repeated=True
								else:
									repeated=False
							if repeated == False:
								f.seek(0, 2) #write temporary file (cache)
								f.write(tweet['id_str']+'\n')
								tweetdata = {
									"CreatedTime":   tweet['created_at'],
									"short_message":      tweet['full_text'],
									"Author" :      tweet['user']['screen_name'],
									"Retweets" :    tweet['retweet_count'],
									"Likes" :       tweet['favorite_count'],
									"Location" :    tweet['user']['location'],
									"Rule" : 	ruleId,
									"full_message" :  "Tweet matched with RULE: " + ruleId
								}
								autotweet=json.dumps(tweetdata)
								fichero.write(autotweet +'\n')
								self.wcloud.write(tweet['full_text']+'\n')
								os.chmod("/var/log/modosint/analyzer-twitter/wcloudRule"+ruleId+".txt",0o777)
								os.chmod("/var/log/modosint/analyzer-twitter/graylog.txt",0o777)
					else:
						break

				
	#Search All Tweets or timeline from @user
	def searchUserTweets(self, user, ruleId, fullstring):
		fichero = open("/var/log/modosint/analyzer-twitter/graylog.txt", "+a", encoding='utf8')              
		with io.open("/var/log/modosint/analyzer-twitter/cache.txt", 'a+') as f:
			os.chmod("/var/log/modosint/analyzer-twitter/cache.txt",0o777)
			tweets=self.twarc.timeline(None,user,None,None)
			repeated=False
			t_end = time.time() + 30
			for tweet in tweets:
				if time.time() < t_end:
					for text in fullstring:
						if text in tweet['full_text']:
							f.seek(0) #read temporary file (cache)		
							content = f.readlines()
							content = [x.strip('\n').strip('u') for x in content]
							for i in range(len(content)):
								if tweet['id_str'] in content:
									repeated=True
								else:
									repeated=False
							if repeated == False:
								f.seek(0, 2) #write temporary file (cache)
								f.write(tweet['id_str'])
								f.write('\n')
								tweetdata = {
									"CreatedTime":   tweet['created_at'],
									"short_message":      tweet['full_text'],
									"Author" :      tweet['user']['screen_name'],
									"Retweets" :    tweet['retweet_count'],
									"Likes" :       tweet['favorite_count'],
									"Location" :    tweet['user']['location'],
									"Rule" : 	ruleId,
									"full_message" :  "Tweet matched with RULE: " + ruleId
								}
								autotweet=json.dumps(tweetdata)
								fichero.write(autotweet +'\n')
								self.wcloud.write(tweet['full_text']+'\n')
								os.chmod("/var/log/modosint/analyzer-twitter/wcloudRule"+ruleId+".txt",0o777)
								os.chmod("/var/log/modosint/analyzer-twitter/graylog.txt",0o777)
				else:
					break

	def create_wordcloud(self,text,ruleId):
		mask = np.array(Image.open(path.join(self.currdir, "twitter_mask.png")))
		# create wordcloud object
		wc = WordCloud(background_color="white",
					max_words=200, 
					mask=mask,
		       	stopwords=self.stop_words)
		try:
			# generate wordcloud
			wc.generate(text)
			# save wordcloud
			wc.to_file(path.join(self.currdir + "/WordCloud/Twitter/", "wcTwitterRule" +ruleId + ".png"))
			os.chmod(path.join(self.currdir + "/WordCloud/Twitter/", "wcTwitterRule" +ruleId + ".png"),0o777)
		except ValueError as e:
			error=True
		

	# custom functionality
	def run(self):
		self.logger.info("working...")
		OSINTRules= self.rules
		for element in OSINTRules:
			ruleId = element.get('metadata', False).get('id',False)
			self.wcloud = open("/var/log/modosint/analyzer-twitter/wcloudRule"+ruleId+".txt", "a+")
			checkUsername=element.get('_username', False)
			checkString=element.get('_string', False)
			if checkUsername:
				user = ('' .join(element['_username']))
			if checkString:
				string = (',' .join(element['_string']))
				fullstring = element['_string']
				checkLanguage=element.get('_language', False)
				if checkLanguage:
					language = ('' .join(element['_language']))
					self.searchDifLanguage(string,language, ruleId)
				else:
					self.searchTweetOrHashtag(string, ruleId)
				if checkUsername:
					self.searchUserTweets(user,ruleId,fullstring)
		if not os.path.exists(self.currdir + "/WordCloud"):
			os.makedirs(self.currdir + "/WordCloud/")
			os.chmod(self.currdir + "/WordCloud/",0o777)
		if not os.path.exists(self.currdir + "/WordCloud/Twitter"):
			os.makedirs(self.currdir + "/WordCloud/Twitter/")
			os.chmod(self.currdir + "/WordCloud/Twitter/",0o777)
		for element in OSINTRules:
			ruleId = element.get('metadata', False).get('id',False)
			file_content = open("/var/log/modosint/analyzer-twitter/wcloudRule"+ruleId+".txt", "r")
			file_content= file_content.readlines()
			self.create_wordcloud(str(file_content),ruleId)
		self.createPlotMentions()
		self.createPlotHashtag()
		self.alertLogger.info("Twitter Analyzer Job Finished succesfully.")

	def exportReferenceHashtag(self,mensaje):
		lista = re.findall(r'#\w+',mensaje)
		return lista if lista!=[] else np.NaN
	
	def exportReferenceMentions(self,mensaje):
		lista = re.findall(r'@\w+',mensaje)
		return lista if lista!=[] else np.NaN
	
	def createPlotMentions(self):
		with io.open('/var/log/modosint/analyzer-twitter/graylog.txt', 'r') as f:
			dataMentions = f.readlines()
			data_json = json.dumps(list(map(lambda entry: eval(entry[:-1]), dataMentions)))
			data_twitter = pd.read_json(data_json)
			referenceMentions = data_twitter.short_message.map(self.exportReferenceMentions)
			referenceMentions.dropna(inplace=True)
			referenceMentions.head()
			referenceMentions = list(referenceMentions)
			referenceMentions_list = list(itertools.chain(*referenceMentions))
			count_referenceMentions = pd.Series(referenceMentions_list).value_counts()
			fig = plt.figure(figsize=(12,8))
			sns.barplot(y=count_referenceMentions.iloc[:20].index, x=count_referenceMentions.iloc[:20].values)
			fig.savefig(self.currdir+ 'mentionsPlot.png')
			os.chmod(self.currdir+ 'mentionsPlot.png',0o777)

	def createPlotHashtag(self):
		with io.open('/var/log/modosint/analyzer-twitter/graylog.txt', 'r') as f:
			dataHashtag = f.readlines()
			data_json = json.dumps(list(map(lambda entry: eval(entry[:-1]), dataHashtag)))
			data_twitter = pd.read_json(data_json)
			referenceHash = data_twitter.short_message.map(self.exportReferenceHashtag)
			referenceHash.dropna(inplace=True)
			referenceHash.head()
			referenceHash = list(referenceHash)
			referenceHash_list = list(itertools.chain(*referenceHash))
			count_referenceHash = pd.Series(referenceHash_list).value_counts()
			fig = plt.figure(figsize=(12,8))
			sns.barplot(y=count_referenceHash.iloc[:20].index, x=count_referenceHash.iloc[:20].values)
			fig.savefig(self.currdir+ 'mentionsHashtag.png')
			os.chmod(self.currdir+ 'mentionsHashtag.png',0o777)



		
		
