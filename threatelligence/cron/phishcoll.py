# Call the phishtank api using the api key, print out the length of the data
# run a for loop to go through each line parsing for the relevant information which then gets added into the database
# The changes to the database will then be committed outside of the loop.

import sqlite3
import urllib
import json
import sys


#Prepare database
conn = sqlite3.connect('phishcoll.sqlite')
cur = conn.cursor()

cur.execute('''
DROP TABLE IF EXISTS Phishing_Campaigns''')

cur.execute('''
CREATE TABLE Phishing_Campaigns (Url TEXT, Country TEXT, Target TEXT, Phishtank_submission TEXT, Verification_time TEXT)''')

#Open connection to the phishtank url to retrieve the file and read into memory
#fhand = open("verified_online.json")
fhand = urllib.urlopen('http://data.phishtank.com/data/75dad665719988230016dcb581a4df31ff627134d170109fc16947af583b3eda/online-valid.json')
if (fhand.getcode() == 200):
    data = fhand.read()
else:
    print('Received an error from server, cannot retrieve results ' + str(fhand.getcode()))
try:
    js = json.loads(data)
except:
    js = None

#run a for loop to run through file and parse out each key value pair within the file in this order:
    #URL, Country, Target, Phishtank_submission, Verification_time
count = 0
    
for line in js:
    url = js[count]["url"]
    country = js[count]["details"][0]["country"]
    target = js[count]["target"]
    phishsubm = js[count]["submission_time"]
    verification = js[count]["verification_time"]

    cur.execute('''INSERT INTO Phishing_Campaigns (Url, Country, Target,
    Phishtank_submission, Verification_time)
    VALUES (?, ?, ?, ?, ?)''', (url, country, target, phishsubm, verification))

    count = count + 1

    if count > len(data):
        break
conn.commit()


