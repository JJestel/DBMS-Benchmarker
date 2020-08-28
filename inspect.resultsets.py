"""
    Small demo how to inspect result sets of the Python Package DBMS Benchmarker.
    This prints the first difference in result sets for each query in the latest benchmark in the current folder.
    TODO: Improve usability and flexibility
    Copyright (C) 2020  Patrick Erdelt

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from dbmsbenchmarker import *
import pandas as pd

#import logging
#logging.basicConfig(level=logging.DEBUG)

###################
##### general properties
###################

# path of folder containing experiment results
resultfolder = "./"

# create evaluation object for result folder
evaluate = inspector.inspector(resultfolder)

# list of all experiments in folder
evaluate.list_experiments

# dataframe of experiments
evaluate.get_experiments_preview()

# pick last experiment
code = evaluate.list_experiments[len(evaluate.list_experiments)-1]

# load it
evaluate.load_experiment(code)

from operator import itemgetter

list_connections = evaluate.get_experiment_list_connections()
list_queries = evaluate.get_experiment_list_queries()
#list_queries = [1]

for numQuery in list_queries:
    list_warnings = evaluate.get_warning(numQuery)
    #print("Q"+str(numQuery))
    #print(list_warnings)
    numRun=0
    df = evaluate.get_datastorage_df(numQuery, numRun)
    data = df.values
    if len(data) > 0 and sum([len(v) for k,v in list_warnings.items()]) > 0:
        print("===Q{}===".format(numQuery))
        print(list_warnings)
        df = pd.DataFrame(sorted(data, key=itemgetter(*list(range(0,len(data[0]))))), columns=df.columns)
        for c in list_connections:
            if c in list_warnings and len(list_warnings[c])>0:
                s = evaluate.benchmarks.protocol['query'][str(numQuery)]['dataStorage']
                r = evaluate.benchmarks.protocol['query'][str(numQuery)]['resultSets']
                for numRun, result in enumerate(s):
                    df2={}
                    data_stored = s[numRun]
                    print("numRun: "+str(numRun))
                    #print(data)
                    for c, result_diff in r.items():
                        if len(result_diff) > 0 and r[c][numRun] != data_stored:
                             df_tmp = evaluate.get_resultset_df(numQuery, c, numRun)
                             data = df_tmp.values
                             df2[c] = pd.DataFrame(sorted(data, key=itemgetter(*list(range(0,len(data[0]))))), columns=df_tmp.columns)
                    for c,d in df2.items():
                        print("Storage has more than {}:".format(c))
                        print(inspector.getDifference12(d,df))
                        print(c+" has more than storage")
                        print(inspector.getDifference12(df,d))
                    if len(df2) > 0:
                        break

