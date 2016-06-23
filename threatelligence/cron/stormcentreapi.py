#Copyright 2016 Graeme James McGibbney
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
'''
Script which acquires Microsoft security vulnerability patches
and determines whether internal systems are affected and 
potentially vulnerable. Affected systems are written into
Elasticsearch.
Microsoft publishes security patches on the second Tuesday 
of each month therefore this script should be run as a cron
job to suite the patch publication pattern.
In order for this script to run, a local sqlite3 DB named
'asset_base2.sqlite' must be within the same directory as this
script.
Finally, it is assumed that Elasticsearch is available at
http://127.0.0.1:9200 such that affected systems and the 
severity of the threat can be written into records for display
in Kibana.
'''
import sqlite3
import urllib
import json
import datetime
from elasticsearch import Elasticsearch,helpers

# Obtaining the date enables dynamic date variable 
# substitution whenever the script is run.
# TODO this could potentially be improved by checking
# for the second Tuesday of every month, however seeing
# as the script is being run as a cron job, we can simply
# invoke it only on the second Tuesday of each month hence
# guaranteeing the dates match perfectly.

#i = datetime.datetime.now()
#fHand = urllib.urlopen("http://isc.sans.edu/api/getmspatchday/%s-%s-%s?json" % (i.year, i.month, i.day))
fHand = urllib.urlopen('http://isc.sans.edu/api/getmspatchday/2016-01-12?json')

print fHand.getcode()

data = fHand.read()

js = json.loads(data)

print json.dumps(js, indent=4)

# The patchDict below will enable us to capture both 
# affected system(s) as well as the severity of each threat
patchDict = {}

# Populate the patchDict variable with Key Value pairs 
# representing the affected application and severity of 
# patch respectively.
for record in js["getmspatchday"]:
    affected = record["affected"]
    severity = record["severity"]
    patchDict[str(affected)] = str(severity)

print patchDict

# Make connection to internal asset database
conn = sqlite3.connect('asset_base2.sqlite')
cur = conn.cursor()

listOfThreats = []

# Need to create another data structure which results can be appended to.
# This will enable us to index the results in a batch oriented fashion.
for patch in patchDict:
    try:
        result = cur.execute("SELECT * FROM database_servers WHERE InstalledApplications='%s' UNION ALL "
                         "SELECT * FROM email_servers WHERE InstalledApplications='%s' UNION ALL "
                         "SELECT * FROM dev_servers WHERE InstalledApplications='%s' UNION ALL "
                         "SELECT * FROM domain_controllers WHERE InstalledApplications='%s' UNION ALL "
                         "SELECT * FROM exchange WHERE InstalledApplications='%s' UNION ALL "
                         "SELECT * FROM file_transfer WHERE InstalledApplications='%s' UNION ALL "
                         "SELECT * FROM huxley WHERE InstalledApplications='%s' UNION ALL "
                         "SELECT * FROM pas WHERE InstalledApplications = '%s'"
                         % (patch, patch, patch, patch, patch, patch, patch, patch))
        affectedSystem = []
        for system in result.fetchall():
            affectedSystem = (unicode(patch),unicode(patchDict[patch]),) + system
            listOfThreats.append(affectedSystem)
    except sqlite3.Error as e:
        print "An error occurred whilst querying the asset database:", e.args[0]
print listOfThreats
# Close connection to asset database
conn.close()

# We'll now build up a Python dictionary of our data set in a format that the 
# Python ES client can use. We are going to load the data by means of bulk 
# indexing. According to the Elasticsearch Bulk API docs, the body of the bulk 
# index request must consist of two lines for each operation: one specifying the 
# meta-data for the operation; and one specifying the actual data that it will 
# index. The code below will build a dictionary that meets these requirements 
# for our data:

bulk_data = [] 
systemList = ['Patch','Severity','Name','DeviceType','InstalledApplictions','ApplicationVersion',
              'Description','OperatingSystem','OperatingSystemVersion','Groups']
for threat in listOfThreats:
    data_dict = {}
    count = 0
    for item in threat:
        data_dict[unicode(systemList[count])] = item
        count += 1
    op_dict = {
        "index": {
            "_index": 'threatelligence', 
            "_type": 'VulnerableSystem', 
            #"_id": data_dict[ID_FIELD]
        }
    }
    bulk_data.append(op_dict)
    bulk_data.append(data_dict)

# Let's create our index using the Python ES client.
# By default we assume the aserver is running on http://localhost:9200
es = Elasticsearch(hosts=['localhost:9200'])
# bulk index the data
res = es.bulk(index = 'threatelligence', body = bulk_data, refresh = True)