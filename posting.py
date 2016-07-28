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

    ####################Prepare for fast sending of messages to Resources##################
    Engagement_Objects = []
    cur.execute("SELECT name, sfid FROM salesforce.engagement__c") #read in all engagement objects from salesforce
    rows = cur.fetchall()
    for row in rows:
        Engagement_Objects.append(row) #append these resources to an array

    for element in Resource: #loop through all resources in RAM to handle
        cur.execute("UPDATE salesforce.resource__c SET awaiting_schedule_response__c = 'true' WHERE telegram_user_id__c = '%s' AND test_resource__c = 'true'" % (element.user_id)) #set awaiting schedule response to true for resource in Salesforce
        con.commit()
        cur.execute("SELECT telegram_user_id__c, engagement__c, on_project__c FROM salesforce.resource__c WHERE telegram_user_id__c = '%s'" % (element.user_id)) #Read the telegram_user_id, engagement and on_project check boxes for resource from Salesforce
        query_result = cur.fetchone()
        if query_result[2] == True: #if resource is on a project
            element.on_project = True #set resource on_project equal to true
            for engagement in Engagement_Objects:
                if engagement[1] == query_result[1]:
                    element.project_name = engagement[0] #set resource project name
    #######################################################################################

    ########################Fast sending of messages to all resources######################
    for element in Resource: #loop through all resources in RAM
        if element.approved == 1:
            keybHide(element.user_id,"Hey! It's that time of the week again! Lets update your schedule:")
            if element.on_project == True: #if user is on a project
                keyb(element.user_id, "Are you still on %s?" % (element.project_name),[["Yes"],["No"]])
            else:
                keyb(element.user_id, "Are you on a billable project?",[["Yes"],["No"]])
    #######################################################################################
    con.close()
