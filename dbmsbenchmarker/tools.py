"""
:Date: 2018-01-03
:Version: 0.9
:Authors: Patrick Erdelt

Helper classes and functions for benchmarking usage of JDBC.
"""
from statistics import *
import numpy as np
import jaydebeapi
from timeit import default_timer #as timer
import pandas as pd
import logging
import math
import re
import ast
from os import path



class timer():
	"""
	Container for storing benchmarks (times).
	This is a list (queries) of lists (connections) of lists (runs).
	Use this by
	- loop over queries q
	-- loop over connections c
	--- startTimer()
	--- making n benchmarks for q and c
	---- startTimerRun() and abortTimerRun() / finishTimerRun()
	--- abortTimer() or finishTimer()
	"""
	header_stats = ["DBMS [ms]", "n", "mean", "stdev", "cv %", "qcod %", "iqr", "median", "min", "max"]
	def __init__(self, name):
		"""
		Stores name of benchmark container (e.g. execution or data transfer)

		:param name: Name of benchmark times container
		:return: returns nothing
		"""
		self.name = name
		self.start = 0
		self.end = 0
		self.currentQuery = 0
		self.stackable = True # this timer will be considered in stacked bar charts (sums up parts of benchmarks times)
		self.perRun = True # this timer measures per run (respects warmup/cooldown)
		self.clearBenchmarks()
	def clearBenchmarks(self):
		"""
		Clears all benchmark related data

		:return: returns nothing
		"""
		self.times = []
		self.stats = []
	@staticmethod
	def getStats(data):
		"""
		Computes statistics to list of data.
		This is: mean, median, stdev, cv (coefficient of variation), qcod (Quartile coefficient of dispersion), iqr (Interquartile range), min and max.

		:param data: List of numbers
		:return: returns 6 statistical numbers as a list
		"""
		# remove zeros for some statistics
		data_no_zeros = list(filter((0.0).__ne__, data))
		if len(data_no_zeros) == 0:
			# we do not want to have an empty list
			data_no_zeros = data
		result = []
		t_mean = mean(data)
		numRun = len(data)
		#print("statistics for n runs: "+str(numRun))
		if numRun > 1:
			t_stdev = stdev(data)
		else:
			t_stdev = 0
		if t_mean > 0 and t_stdev > 0:
			t_cv = t_stdev / t_mean * 100.0
		else:
			t_cv = 0
		t_median = median(data_no_zeros)
		t_min = min(data_no_zeros)
		t_max = max(data_no_zeros)
		Q1 = np.percentile(data_no_zeros,25)
		Q3 = np.percentile(data_no_zeros,75)
		if Q3+Q1 > 0:
			t_qcod = 100.0*(Q3-Q1)/(Q3+Q1)
		else:
			t_qcod = 0
		if Q3-Q1 > 0:
			t_iqr = (Q3-Q1)
		else:
			t_iqr = 0
		result = [numRun, t_mean, t_stdev, t_cv, t_qcod, t_iqr, t_median, t_min, t_max]
		return result
	def startTimer(self, numQuery, query, nameConnection):
		"""
		Stores number of warmup runs and benchmark runs.
		Also clears data of current query.
		This is a dict (connections) of lists (benchmark runs)
		Starts benchmark of one single connection with fixed query.
		Clears list of numbers of runs of current connection.

		:param query: Query object
		:param numRun: Number of benchmarking runs
		:return: returns nothing
		"""
		self.nameConnection = nameConnection
		self.startTimerQuery(numQuery, query)#numWarmup, numRun)
		self.startTimerConnection()
		if len(self.times) <= self.currentQuery:
			self.times.append({})
			self.stats.append({})
		if len(self.times) >= self.currentQuery and self.nameConnection in self.times[self.currentQuery]:
			logging.debug("Benchmark "+self.name+" has already been done")
	def abortTimer(self):
		"""
		Augments list of benchmarks of current connection by filling missing values with 0.

		:return: returns nothing
		"""
		self.abortTimerConnection()
	def cancelTimer(self):
		"""
		All benchmarks are set to 0. Timer will be ignored

		:return: returns nothing
		"""
		self.cancelTimerConnection()
	def finishTimer(self):
		"""
		Appends completed benchmarks to storage.
		This is a list of benchmarks (runs).
		Appends completed benchmarks of one single query to storage.
		This is a dict (connections) of lists (benchmark runs).

		:return: returns nothing
		"""
		self.finishTimerConnection()
		self.finishTimerQuery()
		self.times[self.currentQuery][self.nameConnection] = self.time_c
		self.stats[self.currentQuery][self.nameConnection] = self.stat_c
		print("Benchmark "+self.name+" has been stored for "+self.nameConnection+" mean: "+str(self.stats[self.currentQuery][self.nameConnection][0]))
	def skipTimer(self, numQuery, query, nameConnection):
		self.nameConnection = nameConnection
		self.startTimerQuery(numQuery, query)#numWarmup, numRun)
		if len(self.times) <= self.currentQuery:
			self.times.append({})
			self.stats.append({})
		self.finishTimerQuery()
	def startTimerQuery(self, numQuery, query):# numWarmup, numRun):
		"""
		Stores number of warmup runs and benchmark runs.
		Also clears data of current query.
		This is a list (connections) of benchmarks (runs)

		:param numWarmup: Number of warmup runs
		:param numRun: Number of benchmarking runs
		:return: returns nothing
		"""
		self.currentQuery = numQuery-1
		self.query = query
	def finishTimerQuery(self):
		"""
		Appends completed benchmarks of one single query to storage.
		This is a list (connections) of benchmarks (runs).

		:return: returns nothing
		"""
		pass
	def startTimerConnection(self):
		"""
		Starts benchmark of one single connection with fixed query.
		Clears list of numbers of runs of current connection.

		:return: returns nothing
		"""
		self.time_c = []
		self.stat_c = []
	def abortTimerConnection(self):
		"""
		Augments list of benchmarks of current connection by filling missing values with 0.

		:return: returns nothing
		"""
		# fill missing runs with 0
		#self.time_c.extend([0]*(self.numWarmup+self.numRun-len(self.time_c)))
		self.time_c.extend([0]*(self.query.numRun-len(self.time_c)))
	def cancelTimerConnection(self):
		"""
		Augments list of benchmarks of current connection by filling missing values with 0.

		:return: returns nothing
		"""
		# fill missing runs with 0
		self.time_c = [0]*(self.query.numRun)
	def finishTimerConnection(self):
		"""
		Appends completed benchmarks to storage.
		This is a list of benchmarks (runs).

		:return: returns nothing
		"""
		# compute statistics, ignore warmup
		if self.perRun:
			self.stat_c = timer.getStats(self.time_c[self.query.numRunBegin:self.query.numRunEnd])
		else:
			self.stat_c = timer.getStats(self.time_c)
	def startTimerRun(self):
		"""
		Starts benchmark of one single run.
		This starts a timer.

		:return: returns nothing
		"""
		self.start = default_timer()
	def finishTimerRun(self):
		"""
		Ends benchmark of one single run.
		Benchmark is set to 0 due to error.

		:return: returns 0
		"""
		self.end = default_timer()
		duration = self.end - self.start
		self.time_c.append(1000.0*duration)
		return self.end - self.start
	def abortTimerRun(self):
		"""
		Ends benchmark of one single run.
		Benchmark is stored in list (fixed query, one connection)

		:return: returns duration of current benchmark
		"""
		# same as finishTimerRun(), but time is 0
		self.end = self.start
		duration = self.end - self.start
		self.time_c.append(1000.0*duration)
		return self.end - self.start
	def appendTimes(self, times, query):# numWarmup):
		"""
		Appends results of one single query.
		This is a list (connections) of benchmarks (runs).
		It also computes statistics and thereby ignores warmup runs.

		:param numWarmup: Number of warmup runs
		:return: returns nothing
		"""
		if len(times)>0:
			if self.perRun:
				stats = {k: timer.getStats(v[query.numRunBegin:query.numRunEnd]) for k,v in times.items()}
			else:
				stats = {k: timer.getStats(v) for k,v in times.items()}
			#stats = {k: self.getStats(v[numWarmup:]) for k,v in times.items()}
		else:
			stats = {}
		self.times.append(times)
		self.stats.append(stats)
	def checkForBenchmarks(self, numQuery, nameConnection = None):
		"""
		Checks if there is a list of benchmark runs for a given query and connection.

		:param numQuery: Number of query
		:param nameConnection: Name of connection
		:return: True if benchmark results are present
		"""
		if nameConnection is None:
			return (len(self.times) >= numQuery)
		else:
			return (len(self.times) >= numQuery and nameConnection in self.times[numQuery-1])
	def checkForSuccessfulBenchmarks(self, numQuery, nameConnection = None):
		"""
		Checks if there is a list of benchmark runs for a given query and connection and not all times are zero.

		:param numQuery: Number of query
		:param nameConnection: Name of connection
		:return: True if benchmark results are present
		"""
		existing = self.checkForBenchmarks(numQuery, nameConnection)
		if nameConnection is not None:
			return(existing and not all(v == 0 for v in self.times[numQuery-1][nameConnection]))
		else:
			return(existing and not all(v == 0 for k,c in self.times[numQuery-1].items() for v in c))
	def tolist(self, numQuery):
		"""
		Returns benchmarks of a given query as a list of lists.

		:param numQuery: Number of query
		:return: List of lists of benchmark times
		"""
		l = [v for k,v in self.times[numQuery-1].items()]
		return l
	def toDataFrame(self, numQuery):
		"""
		Returns benchmarks of a given query as a DataFrame (rows=dbms, cols=benchmarks).

		:param numQuery: Number of query
		:return: DataFrame of benchmark times
		"""
		data =list(zip([[k] for k,v in self.times[numQuery-1].items()],[v for k,v in self.times[numQuery-1].items()]))
		# correct nesting 
		data2 = [[item for item in sublist] for sublist in data]
		l = [[item for sublist2 in sublist for item in sublist2] for sublist in data2]
		# convert times to DataFrame
		df = pd.DataFrame.from_records(l)
		return df
	def statsToDataFrame(self, numQuery):
		"""
		Returns statistics of a given query as a DataFrame (rows=dbms, cols=statisticd).

		:param numQuery: Number of query
		:return: DataFrame of benchmark statistics
		"""
		data =list(zip([[k] for k,v in self.stats[numQuery-1].items()],[v for k,v in self.stats[numQuery-1].items()]))
		# correct nesting 
		data2 = [[item for item in sublist] for sublist in data]
		l = [[item for sublist2 in sublist for item in sublist2] for sublist in data2]
		# convert times to DataFrame
		df = pd.DataFrame.from_records(l)
		if df.empty:
			logging.debug("no values")
			return df
		# format times for output
		header = timer.header_stats.copy()
		df.columns = header
		return df




class query():
	template = None
	"""
	Container for storing queries.
	This converts a dict read from json to an object.
	It also checks values and sets defaults.
	"""
	def __init__(self, querydict):
		"""
		Converts dict into object.

		:param query: Dict containing query infos - query, numRun, numParallel, withData, warmup, cooldown, title
		:return: returns nothing
		"""
		self.numRunStd = 5
		self.numRun = 0
		self.numParallel = 1
		self.warmup = 0
		self.cooldown = 0
		self.active = True
		self.title = ''
		self.DBMS = {}
		self.parameter = {}
		self.withData = False
		self.storeData = False
		self.result = False
		self.restrict_precision = None
		self.sorted = False
		self.storeResultSet = False
		self.storeResultSetFormat = []
		self.queryList = []
		self.withConnect = False
		self.timer = {}
		self.timer['connection'] = {}
		self.timer['connection']['active'] = False
		self.timer['datatransfer'] = {}
		self.timer['datatransfer']['active'] = False
		self.delay_connect = 0
		self.delay_run = 0
		# legacy naming
		#self.timer['transfer'] = {}
		#self.timer['transfer']['active'] = self.timer['datatransfer']['active']#False
		self.dictToObject(querydict)
		if query.template is not None:
			self.dictToObject(query.template)
		if self.numRun == 0:
			self.numRun = self.numRunStd
		self.numRunBegin = self.warmup
		self.numRunEnd = self.numRun-self.cooldown
		self.timer['run'] = {'active': True}
		self.timer['session'] = {'active': True}
	def dictToObject(self, query):
		if 'query' in query:
			self.query = query['query']
		if 'numRun' in query:
			self.numRun = int(query['numRun'])
		if 'numParallel' in query:
			self.numParallel = int(query['numParallel'])
		if 'active' in query:
			self.active = query['active']
		if 'numWarmup' in query:
			self.warmup = int(query['numWarmup'])
		if 'numCooldown' in query:
			self.cooldown = int(query['numCooldown'])
		if 'delay' in query:
			self.delay_run = float(query['delay'])
		if 'title' in query:
			self.title = query['title']
		if 'DBMS' in query:
			self.DBMS = query['DBMS']
		if 'parameter' in query:
			self.parameter = query['parameter']
		# timerExecution
		if 'timer' in query:
			self.timer = joinDicts(self.timer, query['timer'])
			self.timer['execution'] = {}
			self.timer['execution']['active'] = True
		# timerTransfer
		if 'datatransfer' in self.timer:
			if self.timer['datatransfer']['active']:
				self.withData = True
			#if 'store' in self.timer['datatransfer'] and self.timer['datatransfer']['store'] == True:
			#	self.storeData = True
			if 'compare' in self.timer['datatransfer'] and self.timer['datatransfer']['compare']:
				self.result = self.timer['datatransfer']['compare']
				self.storeData = True
			if 'precision' in self.timer['datatransfer']:
				self.restrict_precision = self.timer['datatransfer']['precision']
				self.storeData = True
			if 'sorted' in self.timer['datatransfer']:
				self.sorted = self.timer['datatransfer']['sorted']
				self.storeData = True
			if 'store' in self.timer['datatransfer'] and not self.timer['datatransfer']['store'] == False:
				self.storeResultSet = True
				self.storeData = True
				if not self.timer['datatransfer']['store'] == True:
					if isinstance(self.timer['datatransfer']['store'], str):
						self.storeResultSetFormat = [self.timer['datatransfer']['store']]
					else:
						self.storeResultSetFormat = self.timer['datatransfer']['store']
		# timerConnect
		if 'connection' in self.timer:
			if self.timer['connection']['active']:
				self.withConnect = True
			if 'delay' in self.timer['connection']:
				self.delay_connect = float(self.timer['connection']['delay'])
		# we do not have a query string, but a list of (other) queries
		if 'queryList' in query:
			self.queryList = query['queryList']



def formatDuration(ms):
	"""
	Formats duration given in ms to HH:ii:ss and using "," for 1000s

	:param ms: Time given in ms
	:return: returns formatted string
	"""
	# truncate version
	#seconds = int((ms/1000)%60)
	#minutes = int((ms/(1000*60))%60)
	#hours = int((ms/(1000*60*60))%24)
	#s = "{:,.2f}ms = {:0>2d}:{:0>2d}:{:0>2d}".format(ms,hours,minutes,seconds)
	# ceil() version:
	seconds = int(math.ceil(ms/1000)%60)
	minutes = int(math.ceil((ms-1000*seconds)/(1000*60))%60)
	hours = int(math.ceil((ms-1000*seconds-1000*60*minutes)/(1000*60*60)))#%24)
	s = "{:,.2f}ms = {:0>2d}:{:0>2d}:{:0>2d}".format(ms,hours,minutes,seconds)
	return s



class dbms():
	"""
	Container for storing queries.
	This converts a dict read from json to an object.
	It also checks values and sets defaults.
	"""
	jars = []
	currentAnonymChar = 65
	anonymizer = {}
	deanonymizer = {}
	def __init__(self, connectiondata, anonymous = False):
		"""
		Converts dict into object.
		Anonymizes dbms if activated.

		:param query: Dict containing query infos - query, numRun, withData, warmup, title
		:return: returns nothing
		"""
		self.connectiondata = connectiondata
		self.connection = None
		self.cursor = None
		if not connectiondata['JDBC']['jar'] in dbms.jars:
			dbms.jars.append(connectiondata['JDBC']['jar'])
		if not 'version' in self.connectiondata:
			self.connectiondata['version'] = "-"
		if not 'info' in self.connectiondata:
			self.connectiondata['info'] = ""
		if not 'active' in self.connectiondata:
			self.connectiondata['active'] = True
		self.anonymous = anonymous
		# anonymous dbms get ascending char as name
		if self.anonymous:
			if 'alias' in self.connectiondata and len(self.connectiondata['alias']) > 0:
				if self.connectiondata['alias'] in dbms.anonymizer.values():
					# rename first occurance of alias
					old_origin = dbms.deanonymizer[self.connectiondata['alias']]
					old_alias = self.connectiondata['alias']+" "+chr(dbms.currentAnonymChar)
					dbms.currentAnonymChar = dbms.currentAnonymChar + 1
					dbms.anonymizer[old_origin] = old_alias
					dbms.deanonymizer[old_alias] = old_origin
					print("Alias for "+old_origin+" became "+old_alias)
				if self.connectiondata['alias'] in dbms.anonymizer.values() or self.connectiondata['alias']+" A" in dbms.anonymizer.values():
					# rename this occurance
					self.name = self.connectiondata['alias']+" "+chr(dbms.currentAnonymChar)
					dbms.currentAnonymChar = dbms.currentAnonymChar + 1
				else:
					self.name = self.connectiondata['alias']
			else:
				self.name = "DBMS "+chr(dbms.currentAnonymChar)
				dbms.currentAnonymChar = dbms.currentAnonymChar + 1
			print("Alias for "+self.connectiondata['name']+" is "+self.name)
		else:
			self.name = self.connectiondata['name']
		dbms.anonymizer[self.connectiondata['name']] = self.name
		dbms.deanonymizer[self.name] = self.connectiondata['name']
		#print(dbms.anonymizer)
		# is there a limit for parallel processes?
		# =1 means: not parallel
		# =0 means: take global setting
		if not 'numProcesses' in self.connectiondata:
			self.connectiondata['numProcesses'] = 0
	def connect(self):
		"""
		Connects to one single dbms.
		Currently only JDBC is supported.

		:return: returns nothing
		"""
		if 'JDBC' in self.connectiondata:
			self.connection = jaydebeapi.connect(
				self.connectiondata['JDBC']['driver'],
				self.connectiondata['JDBC']['url'],
				self.connectiondata['JDBC']['auth'],
				dbms.jars,)
		else:
			raise ValueError('No connection data for '+self.getName())
	def openCursor(self):
		"""
		Opens cursor for current connection.

		:return: returns nothing
		"""
		if self.connection is not None:
			self.cursor = self.connection.cursor()
	def closeCursor(self):
		"""
		Closes cursor for current connection.

		:return: returns nothing
		"""
		if self.cursor is not None:
			self.cursor.close()
			self.cursor = None
	def executeQuery(self, queryString):
		"""
		Executes a query for current connection and cursor.

		:param queryString: SQL query to be executed
		:return: returns nothing
		"""
		if self.cursor is not None:
			self.cursor.execute(queryString)
	def fetchResult(self):
		"""
		Fetches result from current cursor.

		:param queryString: SQL query to be executed
		:return: returns nothing
		"""
		if self.cursor is not None:
			return self.cursor.fetchall()
		else:
			return []
	def disconnect(self):
		"""
		Disconnects from one single dbms.

		:return: returns nothing
		"""
		if self.connection is not None:
			self.connection.close()
			self.connection = None
	def getName(self):
		"""
		Returns name of dbms, or alias if anonymous.

		:return: returns nothing
		"""
		return self.name
	def hasHardwareMetrics(self):
		# should hardware metrics be fetched from grafana
		if 'monitoring' in self.connectiondata and 'grafanatoken' in self.connectiondata['monitoring'] and 'grafanaurl' in self.connectiondata['monitoring'] and self.connectiondata['monitoring']['grafanatoken'] and self.connectiondata['monitoring']['grafanaurl']:
			return True
		else:
			return False
	def isActive(self):
		return self.connection is not None and self.cursor is not None


class dataframehelper():
	"""
	Class for some handy DataFrame manipulations
	"""
	@staticmethod
	def addFactor(dataframe, factor):
		"""
		Adds factor column to DataFrame of benchmark statistics.
		This is a normalized version of the mean or median column.
		Also moves first column (dbms) to index.

		:param dataframe: Report data given as a pandas DataFrame
		:param factor: Column to take as basis for factor
		:return: returns converted dataframe
		"""
		if dataframe.empty:
			return dataframe
		# select column 0 = connections
		connections = dataframe.iloc[0:,0].values.tolist()
		# only consider not 0, starting after dbms and n
		dataframe_non_zero = dataframe[(dataframe.T[3:] != 0).any()]
		# select column for factor and find minimum in cleaned dataframe
		factorlist = dataframe[factor]
		minimum = dataframe_non_zero[factor].min()
		# norm list to mean = 1
		if minimum > 0:
			mean_list_normed = [round(float(item/minimum),2) for item in factorlist]
		else:
			#print(dataframe_non_zero)
			mean_list_normed = [round(float(item),2) for item in factorlist]
		# transpose for conversion to dict
		dft = dataframe.transpose()
		# set column names
		dft.columns = dft.iloc[0]
		# remove first row
		df_transposed = dft[1:]
		# transform to dict
		d = df_transposed.to_dict(orient="list")
		# correct nesting, (format numbers?)
		stats_output = {k: [sublist for sublist in [stat_q]] for k,stat_q in d.items()}
		# convert times to DataFrame
		data = []
		for c in connections:
			if c in stats_output:
				l = list([c])
				l.extend(*stats_output[c])
				data.append(l)
		dataframe = pd.DataFrame.from_records(data)
		header = timer.header_stats.copy()
		dataframe.columns = header
		# insert factor column
		dataframe.insert(loc=1, column='factor', value=mean_list_normed)
		# sort by factor
		dataframe = dataframe.sort_values(dataframe.columns[1], ascending = True)
		# replace float by string
		dataframe = dataframe.replace(0.00, "0.00")
		# drop rows of only 0 (starting after factor and n)
		dataframe = dataframe[(dataframe.T[3:] != "0.00").any()]
		# replace string by float
		dataframe = dataframe.replace("0.00", 0.00)
		# anonymize dbms
		dataframe.iloc[0:,0] = dataframe.iloc[0:,0].map(dbms.anonymizer)
		dataframe = dataframe.set_index(dataframe.columns[0])
		return dataframe
	@staticmethod
	def sumPerTimer(benchmarker, numQuery, timer):
		"""
		Generates a dataframe (for bar charts) of the time series of a benchmarker.
		Rows=dbms, cols=timer, values=sum of times
		Anonymizes dbms if activated.

		:param numQuery: Number of query to generate dataframe of (None means all)
		:param timer: Timer containing benchmark results
		:return: returns nothing
		"""
		sums = list(range(0,len(timer)))
		timerNames = [t.name for t in timer]
		bValuesFound = False
		numQueriesEvaluated = 0
		numBenchmarks = 0
		validQueries = findSuccessfulQueriesAllDBMS(benchmarker, numQuery, timer)
		for numTimer,t in enumerate(timer):
			numFactors = 0
			logging.debug("sumPerTimer: Check timer "+t.name)
			sums[numTimer] = {}
			if not t.stackable:
				logging.debug(t.name+" is not stackable")
				continue
			# are there benchmarks for this query?
			for i,q in enumerate(t.times):
				# does this timer contribute?
				if not i in validQueries[numTimer]:
					continue
				logging.debug("timer "+str(numTimer)+" is valid for query Q"+str(i+1))
				df = benchmarker.statsToDataFrame(i+1, t)
				#print(df)
				queryObject = query(benchmarker.queries[i])
				# no active dbms missing for this timer and query
				numQueriesEvaluated = numQueriesEvaluated + 1
				if numQuery is None:
					logging.debug(str(numQueriesEvaluated)+"=Q"+str(i+1)+" in total bar chart of timer "+t.name+" - all active dbms contribute")
				bValuesFound = True
				numFactors = numFactors + 1
				for c,values in q.items():
					if benchmarker.dbms[c].connectiondata['active']:
						dbmsname = benchmarker.dbms[c].getName()
						if dbmsname in df.index:
							value_to_add = float(df.loc[dbmsname].loc[benchmarker.queryconfig['factor']])
							numBenchmarks += len(values[queryObject.numRunBegin:queryObject.numRunEnd])
							logging.debug("Added "+dbmsname+": "+str(value_to_add))
							if dbmsname in sums[numTimer]:
								sums[numTimer][dbmsname] = sums[numTimer][dbmsname] + value_to_add
							else:
								sums[numTimer][dbmsname] = value_to_add
			sums[numTimer] = {c: x/numFactors for c,x in sums[numTimer].items()}
		if not bValuesFound:
			return None, ''
		df = pd.DataFrame(sums, index=timerNames)
		df=df.fillna(0.0)
		# remove zero rows (timer missing)
		df = df[(df.T[0:] != 0).any()]
		d = df.transpose()
		# anonymize dbms
		#d.index = d.index.map(dbms.anonymizer)
		# add column total timer
		d['total']=d.sum(axis=1)
		# remove zero rows (dbms missing)
		d = d[(d.T[0:] != 0).any()]
		# remove zero columns (timer missing)
		d = d.loc[:, (d != 0).any(axis=0)]
		if d.empty:
			logging.debug("no values")
			return None, ''
		# sort by total
		d = d.sort_values('total', ascending = True)
		# drop total
		d = d.drop('total',axis=1)
		# add unit to columns
		d.columns = d.columns.map(lambda s: s+' [ms]')
		# label chart
		if benchmarker.queryconfig['factor'] == 'mean':
			chartlabel = 'Arithmetic mean of mean times'
		elif benchmarker.queryconfig['factor'] == 'median':
			chartlabel = 'Arithmetic mean of median times'
		if numQuery is None:
			title = chartlabel+" in "+str(numQueriesEvaluated)+" benchmarks ("+str(numBenchmarks)+" measurements) [ms]"
		else:
			title = "Q"+str(numQuery)+": "+chartlabel+" [ms] in "+str(queryObject.numRun-queryObject.warmup-queryObject.cooldown)+" benchmark test runs"
		return d, title
	@staticmethod
	def multiplyPerTimer(benchmarker, numQuery, timer):
		"""
		Generates a dataframe (for bar charts) of the time series of a benchmarker.
		Rows=dbms, cols=timer, values=sum of times
		Anonymizes dbms if activated.

		:param numQuery: Number of query to generate dataframe of (None means all)
		:param timer: Timer containing benchmark results
		:return: returns nothing
		"""
		sums = list(range(0,len(timer)))
		timerNames = [t.name for t in timer]
		bValuesFound = False
		numQueriesEvaluated = 0
		numBenchmarks = 0
		validQueries = findSuccessfulQueriesAllDBMS(benchmarker, numQuery, timer)
		for numTimer,t in enumerate(timer):
			# factors per dbms
			numFactors = {}
			logging.debug("multiplyPerTimer: Check timer "+t.name)
			sums[numTimer] = {}
			# we want to keep not stackable for table chart
			#if not t.stackable:
			#	logging.debug(t.name+" is not stackable")
			#	continue
			# are there benchmarks for this query?
			for i,q in enumerate(t.times):
				# does this timer contribute?
				if not i in validQueries[numTimer]:
					continue
				logging.debug("timer "+str(numTimer)+" is valid for query Q"+str(i+1))
				df = benchmarker.statsToDataFrame(i+1, t)
				queryObject = query(benchmarker.queries[i])
				# no active dbms missing for this timer and query
				numQueriesEvaluated = numQueriesEvaluated + 1
				if numQuery is None:
					logging.debug(str(numQueriesEvaluated)+"=Q"+str(i+1)+" in total bar chart of timer "+t.name+" - all active dbms contribute")
				bValuesFound = True
				# at least one DBMS does not contribute (because of zero value)
				bMissingFound = False
				# mean value (i.e. sum of all values)
				for c,values in q.items():
					if benchmarker.dbms[c].connectiondata['active']:
						dbmsname = benchmarker.dbms[c].getName()
						if dbmsname in df.index:
							value_to_multiply = float(df.loc[dbmsname].loc['factor'])
							if value_to_multiply == 0:
								# we have some values, but none counting because of warmup
								bMissingFound = True
								break
				if bMissingFound:
					numQueriesEvaluated = numQueriesEvaluated - 1
					continue
				for c,values in q.items():
					if benchmarker.dbms[c].connectiondata['active']:
						dbmsname = benchmarker.dbms[c].getName()
						if dbmsname in df.index:
							value_to_multiply = float(df.loc[dbmsname].loc['factor'])
							if value_to_multiply == 0:
								# we have some values, but none counting because of warmup
								# this should not happen here
								# bMissingFound = True
								continue
							if t.perRun:
								numBenchmarks += len(values[queryObject.numRunBegin:queryObject.numRunEnd])
							if not dbmsname in numFactors:
								numFactors[dbmsname] = 0
							numFactors[dbmsname] = numFactors[dbmsname] + 1
							logging.debug("Multiplied "+dbmsname+": "+str(value_to_multiply))
							if dbmsname in sums[numTimer]:
								sums[numTimer][dbmsname] = sums[numTimer][dbmsname] * value_to_multiply
							else:
								sums[numTimer][dbmsname] = value_to_multiply
			#logging.debug(str(numFactors[dbmsname])+" factors")
			sums[numTimer] = {c: x ** (1/numFactors[c]) for c,x in sums[numTimer].items()}
		if not bValuesFound:
			return None, ''
		df = pd.DataFrame(sums, index=timerNames)
		df=df.fillna(0.0)
		# remove zero rows (timer missing)
		df = df[(df.T[0:] != 0).any()]
		d = df.transpose()
		# anonymize dbms
		#d.index = d.index.map(dbms.anonymizer)
		# add column total timer
		d['total']=d.sum(axis=1)
		# remove zero rows (dbms missing)
		d = d[(d.T[0:] != 0).any()]
		# remove zero columns (timer missing)
		d = d.loc[:, (d != 0).any(axis=0)]
		if d.empty:
			logging.debug("no values")
			return None, ''
		# sort by total
		d = d.sort_values('total', ascending = True)
		# drop total
		d = d.drop('total',axis=1)
		# label chart
		if benchmarker.queryconfig['factor'] == 'mean':
			chartlabel = 'Geometric mean of factors of mean times'
		elif benchmarker.queryconfig['factor'] == 'median':
			chartlabel = 'Geometric mean of factors of median times'
		if numQuery is None:
			title = chartlabel+" in "+str(numQueriesEvaluated)+" benchmarks"# ("+str(numBenchmarks)+" runs)"
		else:
			title = "Q"+str(numQuery)+": "+chartlabel+" in "+str(queryObject.numRun-queryObject.warmup-queryObject.cooldown)+" benchmark test runs"
		return d, title
	@staticmethod
	def totalTimes(benchmarker):
		# find position of execution timer
		e = [i for i,t in enumerate(benchmarker.timers) if t.name=="execution"]
		# list of active queries for timer e[0] = execution
		qs = findSuccessfulQueriesAllDBMS(benchmarker, None, benchmarker.timers)[e[0]]
		if len(qs) == 0:
			return None, ""
		# list of active dbms
		cs = [i for i,q in benchmarker.dbms.items() if q.connectiondata['active']]
		times1 = dict.fromkeys(cs, list())
		times = {c:[] for c,l in times1.items()}
		for i in range(len(qs)):
			for q,c in enumerate(cs):
				if c in benchmarker.protocol['query'][str(qs[i]+1)]['durations']:
					times[c].append(benchmarker.protocol['query'][str(qs[i]+1)]['durations'][c])
				else:
					times[c].append(0.0)
		dataframe = pd.DataFrame.from_records(times)
		dataframe.index = qs
		dataframe.index = dataframe.index.map(lambda r: "Q"+str(r+1))
		dataframe.columns = dataframe.columns.map(dbms.anonymizer)
		title = 'Total times of '+str(len(times[c]))+" queries"
		return dataframe, title
	@staticmethod
	def timesToStatsDataFrame(times):
		l = timer.getStats(times)
		# convert statistics to DataFrame
		df = pd.DataFrame.from_records([l])
		header = timer.header_stats.copy()
		df.columns = header[1:]
		return df
	@staticmethod
	def resultsetToDataFrame(data):
		df = pd.DataFrame.from_records(data)
		# set column names
		df.columns = df.iloc[0]
		# remove first row
		df = df[1:]
		return df
	@staticmethod
	def evaluateHardwareToDataFrame(evaluation):
		df1=pd.DataFrame.from_dict({c:d['hardwaremetrics'] for c,d in evaluation['dbms'].items()}).transpose()
		df2=pd.DataFrame.from_dict({c:d['hostsystem'] for c,d in evaluation['dbms'].items()}).transpose()
		if 'CUDA' in df2.columns:
			df2 = df2.drop(['CUDA'],axis=1)
		if 'node' in df2.columns:
			df2 = df2.drop(['node'],axis=1)
		df = df1.merge(df2,left_index=True,right_index=True).drop(['host','CPU','GPU','instance','RAM','Cores'],axis=1)
		#df3=df1.merge(df2,left_index=True,right_index=True).drop(['CUDA','host','CPU','GPU','instance','RAM','Cores'],axis=1)
		df = df.astype(float)
		df.index = df.index.map(dbms.anonymizer)
		df = dataframehelper.addStatistics(df)
		df = df.applymap(lambda x: x if not np.isnan(x) else 0.0)
		return df
	@staticmethod
	def addStatistics(df):
		#print(df)
		#with_nan = False
		#print(df)
		if df.isnull().any().any():
			#print("Missing!")
			with_nan = True
			df = df.dropna()
		stat_mean = df.mean()
		#print(stat_mean)
		stat_std = df.std()
		stat_q1 = df.quantile(0.25)
		stat_q2 = df.quantile(0.5)
		stat_q3 = df.quantile(0.75)
		#print(stat_q1)
		#print(stat_q3)
		df.loc['Mean']= stat_mean
		df.loc['Std Dev']= stat_std
		df.loc['Std Dev'] = stat_std.map(lambda x: x if not np.isnan(x) else 0.0)
		df.loc['cv [%]']= df.loc['Std Dev']/df.loc['Mean']*100.0
		df.loc['Median']= stat_q2
		df.loc['iqr']=stat_q3-stat_q1
		df.loc['qcod [%]']=(stat_q3-stat_q1)/(stat_q3+stat_q1)*100.0
		#if with_nan:
		#	print(df)
		return df
	@staticmethod
	def evaluateMonitoringToDataFrame(evaluation):
		df = pd.DataFrame.from_dict({c:d['hardwaremetrics'] for c,d in evaluation['dbms'].items()}).transpose()
		df.index = df.index.map(dbms.anonymizer)
		#df = pd.DataFrame.from_dict({c:d['hardwaremetrics'] if 'hardwaremetrics' in d else [] for c,d in evaluation['dbms'].items()}).transpose()
		df = df.astype(float)
		df = dataframehelper.addStatistics(df)
		df = df.applymap(lambda x: x if not np.isnan(x) else 0.0)
		return df
	def evaluateHostToDataFrame(evaluation):
		df1 = pd.DataFrame.from_dict({c:d['hostsystem'] for c,d in evaluation['dbms'].items()}).transpose()
		#print({c:d['prices']['benchmark_usd'] for c,d in evaluation['dbms'].items()})
		df2 = pd.DataFrame.from_dict({c:{'benchmark_usd':d['prices']['benchmark_usd'],'benchmark_time_s':d['times']['benchmark_ms']/1000.0,'total_time_s':(d['times']['load_ms']+d['times']['benchmark_ms'])/1000.0} for c,d in evaluation['dbms'].items()}).transpose()
		df = df1.merge(df2,left_index=True,right_index=True)
		df.index = df.index.map(dbms.anonymizer)
		if 'CUDA' in df.columns:
			df = df.drop(['CUDA'],axis=1)
		if 'node' in df.columns:
			df = df.drop(['node'],axis=1)
		if 'instance' in df.columns:
			df = df.drop(['instance'],axis=1)
		if 'GPUIDs' in df.columns:
			df = df.drop(['GPUIDs'],axis=1)
		df = df.drop(['host','CPU','GPU'],axis=1)#,'RAM','Cores'
		df = df.astype(float)
		if 'RAM' in df:
			df['RAM'] = df['RAM']/1024/1024
		if 'disk' in df:
			df['disk'] = df['disk']/1024
		if 'datadisk' in df:
			df['datadisk'] = df['datadisk']/1024
		df = dataframehelper.addStatistics(df)
		df = df.applymap(lambda x: x if not np.isnan(x) else 0.0)
		return df
	@staticmethod
	def evaluateTimerfactorsToDataFrame(evaluation, timer):
		#l=e.evaluation['query'][1]['benchmarks']['execution']['statistics']
		factors = {}
		rows = []
		#print(timer.name)
		connections = [c for c, v in evaluation['dbms'].items()]
		#print(connections)
		for i,q in evaluation['query'].items():
			#print(q)
			if q['config']['active']:
				#print(i)
				rows.append('Q'+str(i))
				if 'benchmarks' in q and 'statistics' in q['benchmarks'][timer.name]:
					# there are (some) results for this query
					stats = q['benchmarks'][timer.name]['statistics']
					for j, c in enumerate(connections):
						if not c in factors:
							factors[c] = []
						if c in stats:
							factors[c].append(stats[c]['factor'])
						elif c in dbms.anonymizer and dbms.anonymizer[c] in stats:
							factors[c].append(stats[dbms.anonymizer[c]]['factor'])
						else:
							factors[c].append(None)
				else:
					# there are no results for this (active) query
					for j, c in enumerate(connections):
						if not c in factors:
							factors[c] = []
						else:
							factors[c].append(None)
		#l={c:len(k) for c,k in factors.items()}
		#print(l)
		df = pd.DataFrame(factors)
		df = df.reindex(sorted(df.columns), axis=1)
		df.columns = df.columns.map(dbms.anonymizer)
		df.index = rows
		#print(df)
		return df
	@staticmethod
	def evaluateTPSToDataFrame(evaluation):
		factors = {}
		rows = []
		for i,q in evaluation['query'].items():
			if q['config']['active']:
				rows.append('Q'+str(i))
				for c,d in q['dbms'].items():
					if not c in factors:
						factors[c] = []
					if 'metrics' in d and 'throughput_run_mean_ps' in d['metrics']:
						factors[c].append(d['metrics']['throughput_run_mean_ps'])
					else:
						factors[c].append(None)
					#print(c)
					#print(d['factor'])
		#print(factors)
		df = pd.DataFrame(factors)
		df = df.reindex(sorted(df.columns), axis=1)
		df.columns = df.columns.map(dbms.anonymizer)
		#df.index = df.index.map(lambda x: 'Q'+str(x+1))
		df.index = rows
		#print(df)
		return df
	@staticmethod
	def evaluateLatToDataFrame(evaluation):
		factors = {}
		rows = []
		for i,q in evaluation['query'].items():
			if q['config']['active']:
				#print(q)
				rows.append('Q'+str(i))
				for c,d in q['dbms'].items():
					if 'metrics' in d and 'latency_run_mean_ms' in d['metrics']:
						if not c in factors:
							factors[c] = []
						factors[c].append(d['metrics']['latency_run_mean_ms']/1000.0)
						#print(c)
						#print(d['factor'])
					else:
						if not c in factors:
							factors[c] = []
						factors[c].append(None)
						#print(i)
						#print(c)
		#print(factors)
		df = pd.DataFrame(factors)
		df = df.reindex(sorted(df.columns), axis=1)
		df.columns = df.columns.map(dbms.anonymizer)
		#df.index = df.index.map(lambda x: 'Q'+str(x+1))
		df.index = rows
		#print(df)
		return df
	@staticmethod
	def getWorkflow(benchmarker):
		print("getWorkflow")
		filename = benchmarker.path+'/experiments.config'
		if path.isfile(filename):
			print("config found")
			with open(filename, 'r') as f:
				d = ast.literal_eval(f.read())
			workflow = {}
			instance = ''
			volume = ''
			docker = ''
			script = ''
			clients = ''
			rpc = ''
			for i,step in enumerate(d):
				if 'connection' in step:
					connection = step['connection']
				else:
					connection = ''
				if 'delay' in step:
					delay = step['delay']
				else:
					delay = ''
				if 'instance' in step:
					instance = step['instance']
				if 'docker' in step:
					dbms = [k for k,d in step['docker'].items()]
					docker = dbms[0]
				if 'initscript' in step:
					scripts = [k for k,s in step['initscript'].items()]
					script = scripts[0]
				if 'volume' in step:
					volume = step['volume']
				if 'connectionmanagement' in step:
					if 'numProcesses' in step['connectionmanagement']:
						clients = step['connectionmanagement']['numProcesses']
					if 'runsPerConnection' in step['connectionmanagement']:
						rpc = step['connectionmanagement']['runsPerConnection']
				workflow[i] = [step['step'], instance, volume, docker, script, connection, delay, clients, rpc]
			df = pd.DataFrame.from_dict(workflow, orient='index', columns=['step', 'instance', 'volume', 'dbms', 'script', 'connection', 'delay', 'clients', 'rpc'])
			#print(df)
			return df
		else:
			return None


def findSuccessfulQueriesAllDBMS(benchmarker, numQuery, timer):
	"""
	Find all queries where all dbms retrieved results successfully for a given list of timers.
	These may be taken into account for comparisons and a total bar chart.
	Anonymizes dbms if activated.

	:param numQuery: Number of query to inspect (optional)
	:param timer: Timer containing benchmark results
	:return: returns list of successful queries per timer
	"""
	validQueries = list(range(0,len(timer)))
	for numTimer,t in enumerate(timer):
		logging.debug("Bar chart: Check timer "+t.name)
		validQueries[numTimer] = []
		# are there benchmarks for this query?
		if numQuery is not None and not t.checkForBenchmarks(numQuery):
			continue
		for i,q in enumerate(t.times):
			# does this timer contribute?
			if not t.checkForBenchmarks(i+1):
				continue
			queryObject = query(benchmarker.queries[i])
			# is timer active for this query?
			if not queryObject.timer[t.name]['active']:
				continue
			bIgnoreQuery = False
			if numQuery is None or (numQuery > 0 and numQuery-1 == i):
				# use all queries (total) or this query is requested
				if numQuery is None:
					for connectionname, c in benchmarker.dbms.items():
						# ignore queries not active
						if not queryObject.active:
							logging.debug("Total bar: Ignore query "+str(i+1)+" - query inactive")
							bIgnoreQuery = True
						# for total: only consider queries completed by all active dbms
						elif not connectionname in q and c.connectiondata['active']:
							logging.debug("Total bar: Ignore query "+str(i+1)+" - missing dbms "+connectionname)
							bIgnoreQuery = True
						# for total: only consider active dbms without error
						elif c.connectiondata['active'] and all(v == 0 for v in q[connectionname]):
							logging.debug("Total bar: Ignore query "+str(i+1)+" - data 0")
							bIgnoreQuery = True
						if bIgnoreQuery:
							break
				if not bIgnoreQuery:
					# no active dbms missing for this timer and query
					validQueries[numTimer].append(i)
	return validQueries



import ast
def convertToFloat(var):
	"""
	Converts variable to float.

	:param var: Some variable
	:return: returns float converted variable
	"""
	try:
		return type(ast.literal_eval(var))
	except Exception:
		return str



def sizeof_fmt(num, suffix='B'):
	"""
	Formats data size into human readable format.
	https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size

	:param num: Data size
	:param suffix: 'B'
	:return: returns human readable data size
	"""
	for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
		if abs(num) < 1024.0:
			return "%3.1f %s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f %s%s" % (num, 'Yi', suffix)



def tex_escape(text):
	"""
	Escapes string so it's latex compatible.
	https://stackoverflow.com/questions/16259923/how-can-i-escape-latex-special-characters-inside-django-templates

	:param text: a plain text message
	:return: the message escaped to appear correctly in LaTeX
	"""
	conv = {
		'&': r'\&',
		'%': r'\%',
		'$': r'\$',
		'#': r'\#',
		'_': r'\_',
		'{': r'\{',
		'}': r'\}',
		'~': r'\textasciitilde{}',
		'^': r'\^{}',
		'\\': r'\textbackslash{}',
		'<': r'\textless{}',
		'>': r'\textgreater{}',
	}
	regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key = lambda item: - len(item))))
	return regex.sub(lambda match: conv[match.group()], text)


def joinDicts(d1, d2):
	result = d1.copy()
	for k, v in d2.items():
		if (k in d1 and isinstance(d1[k], dict)):
			result[k] = joinDicts(d1[k], d2[k])
		else:
			result[k] = d2[k]
	return result
