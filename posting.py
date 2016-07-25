from telegramAPI import get,post,keyb
from resource import resource
import json
import sys
import psycopg2
import os
import urlparse
from os.path import exists
from os import makedirs

def postit(Resource): #function which sends the first resource management question
    #################################Setup Heroku Postgres#################################
    url = urlparse.urlparse(os.environ.get('DATABASE_URL'))
    db = "dbname=%s user=%s password=%s host=%s " % (url.path[1:], url.username, url.password, url.hostname)
    schema = "schema.sql"
    con = psycopg2.connect(db)
    cur = con.cursor()
    #######################################################################################

    for element in Resource: #loop through all resources in RAM
        post(element.user_id,"Hey! It's that time of the week again! Lets update your schedule:")
        cur.execute("UPDATE salesforce.resource__c SET awaiting_schedule_response__c = 'true' WHERE telegram_user_id__c = '%s'" % (element.user_id))
        con.commit()
        keyb(element.user_id, "Are you on a billable project?",[["Yes"],["No"]])
    con.close()
