################EXTERNAL LIBRARY IMPORTS################
from celery import Celery
import requests
from telegramAPI import get,post,keyb,keybHide
import apiai
import json
from resource import resource
from posting import postit
import schedule
import time
import signal
import sys
import psycopg2
import os
import urlparse
from os.path import exists
from os import makedirs
########################################################

##############Defining a celery worker app##############
app = Celery()
app.config_from_object("celery_settings")
########################################################

##############Safely handling dyno restarts#############
def handler(signum, frame):
    sys.exit(1)
########################################################

##############Defining a celery worker task#############
@app.task
def botprogram():
    ############Defining date variables to handle capturing the project roll off date user experience###############
    day = [['1'],['2'],['3'],['4'],['5'],['6'],['7'],['8'],['9'],['10'],['11'],['12'],['13'],['14'],['15'],['16'],['17'],['18'],['19'],['20'],['21'],['22'],['23'],['24'],['25'],['26'],['27'],['28'],['29'],['30'],['31']]
    month = [['January'],['February'],['March'],['April'],['May'],['June'],['July'],['August'],['September'],['October'],['November'],['December']]
    year = [['2016'],['2017'],['2018'],['2019'],['2020']]
    ################################################################################################################

    telegram_result = "" #Empty variable for storing a received telegram message
    Resource = [] #Array to store all resource objects which are instantiated
    index = -1 #Variable to represent the index value of the resource within the Resource array
    offset = 0 #Variable to store the index value of the received message

    #######################API.AI setup#########################
    Resource_ACCESS_TOKEN = 'd15e157632014d57951ff2ec164ed4f1'
    ai = apiai.ApiAI(Resource_ACCESS_TOKEN)
    ############################################################

    #######################Heroku Postgres setup#########################
    url = urlparse.urlparse(os.environ.get('DATABASE_URL'))
    db = "dbname=%s user=%s password=%s host=%s " % (url.path[1:], url.username, url.password, url.hostname)
    schema = "schema.sql"
    con = psycopg2.connect(db)
    cur = con.cursor()
    #####################################################################

    schedule.every().thursday.at("13:44").do(postit,Resource) #Schedule library function to run postit function at friday at 10am (8am GMT). The Resource array is passed as a parameter to the postit function.

    cur.execute("SELECT telegram_user_id__c, name,test_resource__c FROM salesforce.resource__c WHERE test_resource__c = 'true'") #Read resource information from Salesforce
    rows = cur.fetchall()
    for row in rows:
        Resource.append(resource(row[0],row[1])) #Instantiating resource objects using the Salesforce data and appending these objects to the Resource array.
        print str('adding ' + row[1] + ' to RAM')

    while True: #'Runtime infinite loop'
        while True: #'Receive message loop'
            cur.execute("SELECT telegram_user_id__c, name,test_resource__c FROM salesforce.resource__c WHERE test_resource__c = 'true'") #Read resource information from Salesforce
            rows = cur.fetchall()
            for row in rows: #loop through resources from Salesforce
                found = 0
                for element in Resource: #loop through resources in the Resources array (RAM)
                    if str(element.user_id) == str(row[0]): #if resource is in both Salesforce and the Resources array, do nothing.
                        found = 1
                        if element.approved == 0:
                            element.approved = 1
                            print str (row[1] + ' has been approved on Salesforce')
                if found == 0: # if the resource was added on Salesforce but has not yet been added to the Resources array, add it to the Resources array.
                    Resource.append(resource(row[0],row[1]))
                    print str (row[1] + ' has been approved on Salesforce')
                    print str('adding ' + row[1] + ' to RAM')

            schedule.run_pending() #Check to see if it is the right day and time for the Schedule library function to run the postit function
            telegram_response = get(offset) #wait to receive telegram response
            for result in telegram_response['result']: #if the telegram response contains a 'result' component, then a message has been received.
                telegram_result = result
                break #break out of the 'Recieve message loop'
            if not telegram_result == "": #if the telegram_result is equal to something, then a message has been received.
                break #break out of the 'Recieve message loop'
            #if no message has been received then loop back to the 'Recieve message loop' and wait to receive a message again.

        try: #check to see if the result component of the telegram_response contains an update_id
            update_id = result['update_id']
            print 'message received'
        except KeyError: #except the error so the program doesn't crash
            pass
        try: #check to see if the result component of the telegram_response contains text
            text = result['message']['text']
        except KeyError: #except the error so the program doesn't crash
            pass
        try: #check to see if the result component of the telegram_response contains a first and last name
            first_name = result['message']['from']['first_name']
            last_name = result['message']['from']['last_name']
            name = str(first_name + " " + last_name)
        except KeyError: #except the error so the program doesn't crash
            pass
        try: #check to see if the result component of the telegram_response contains a user id
            user_id = result['message']['from']['id']
        except KeyError: #except the error so the program doesn't crash
            pass
        try: #check to see if the result component of the telegram_response contains a chat id
            chat_id = result['message']['chat']['id']
        except KeyError: #except the error so the program doesn't crash
            pass

        if len(Resource) > 0: #if there are resource objects in the Resource array
            for i in range (0,len(Resource)): #loop through the Resource array
                if str(Resource[i].user_id) == str(user_id): #if the user id of the resource from the Resource array is equal to the user id of the current telegram user
                    index = i #set the index variable equal the index of the resource in the Resource array
                    print 'from old user'
                elif str(Resource[i].name) == str(name): #if the name of the resource from the Resource array is equal to the name of the current telegram user (User's name was loaded from Salesforce but not their Telegram I.D)
                    index = i #set the index variable equal the index of the resource in the Resource array
                    Resource[i].user_id = user_id #set the resource user id equal the user id of the current telegram user
                    cur.execute("UPDATE salesforce.resource__c SET telegram_user_id__c = '%s' WHERE name = '%s'" % (user_id, name)) #update Salesforce to include the resource's telegram id on their record
                    con.commit() #commit the previous SQL query to the Postgres database
                    print 'from old user with no telegram id'
                    print 'telegram id updated in Salesforce'

        if index == -1: #if the telegram user does not have an associated resource object in the Resource array, their index is defaulted to -1
            try:
                cur.execute("SELECT telegram_user_id__c FROM salesforce.resource__c WHERE telegram_user_id__c = '%s'" % (user_id))
                query_result = cur.fetchone()
                if query_result[0] == str(user_id):
                    Resource.append(resource(user_id,name))
                    index = len(Resource)-1
                    Resource[index].approved = 0
                    print 'from user who is on Salesforce but has not been approved yet'
                    print str('adding ' + str(Resource[index].name) + ' to RAM')
            except TypeError:
                Resource.append(resource(user_id,name)) #a new resource object is created and appended to the Resource array
                index = len(Resource)-1 #The index variable is set to the index of the new resource in the Resourece array
                Resource[index].approved = 0
                cur.execute("INSERT INTO salesforce.resource__c (telegram_user_id__c,name,Employee_Status__c) VALUES ('%s', '%s','Active')" % (user_id, name)) #A new resource record is created on Salesforce
                con.commit()
                print 'from new user'
                print str('adding ' + str(Resource[index].name) + ' to RAM')


        cur.execute("SELECT telegram_user_id__c, awaiting_schedule_response__c, on_project__c FROM salesforce.resource__c WHERE telegram_user_id__c = '%s'" % (Resource[index].user_id)) #Read the telegram_user_id, awaiting_schedule_response check box and on_project check box for the current telegram user from Salesforce
        query_result = cur.fetchone()
        try: #if there is no result (the telegram user was deleted off Salesforce at some point), this will cause an error
            if query_result[1] == True and Resource[index].approved: #if the awaiting_schedule_response checkbox is checked
                if Resource[index].phase == 0: #if the resource phase attribute is 0
                    if text in ['Yes','No']: #if the telegram_response text is yes or no
                        if query_result[2] == True: #if the user was on a project
                            if text == 'Yes': #if the user is still on that project
                                keybHide(Resource[index].user_id,'Thank you for your time. Keep up the good work!')
                                cur.execute("UPDATE salesforce.resource__c SET awaiting_schedule_response__c = 'false' WHERE telegram_user_id__c = '%s'" % (user_id))
                                con.commit()
                            else: #if the user is no longer on that project
                                keyb(element.user_id, "Are you on a billable project?",[["Yes"],["No"]])
                                cur.execute("UPDATE salesforce.resource__c SET on_project__c = 'false', engagement_roll_off_date__c = NULL, engagement__c = '' WHERE telegram_user_id__c = '%s'" % (user_id)) #refresh resource object so that new scheduled data can be recorded
                                con.commit()
                        else:
                            if text == 'No':
                                keybHide(Resource[index].user_id,'Thank you for your time. Hopefully you will be billable next time we speak!')
                                cur.execute("UPDATE salesforce.resource__c SET on_project__c = 'false', awaiting_schedule_response__c = 'false', engagement_roll_off_date__c = NULL, engagement__c = '' WHERE telegram_user_id__c = '%s'" % (user_id))
                                con.commit()
                            else:
                                cur.execute("UPDATE salesforce.resource__c SET on_project__c = 'true' WHERE telegram_user_id__c = '%s'" % (user_id))
                                con.commit()
                                ########################Processing the list of Engagements from Salesforce###########################
                                Engagement_Names = []
                                Engagement_Objects = []
                                cur.execute("SELECT name, sfid, project_status__c FROM salesforce.engagement__c WHERE project_status__c = 'In Progress'")
                                rows = cur.fetchall()
                                for row in rows:
                                    Engagement_Names.append([row[0]])
                                    Engagement_Objects.append([row])
                                keyb (Resource[index].user_id,"Which project are you currently on?", Engagement_Names)
                                Resource[index].phase = 1 #set the resource phase attribute to 1 - next phase of the conversation
                                ######################################################################################################

                    else: #if the telegram_response is not yes or no
                        post (Resource[index].user_id, 'Invalid response. Try again.')

                elif Resource[index].phase == 1: #if the resource phase is 1
                    if [text] in Engagement_Names: #check the telegram user's response was one of the options on the list
                        for element in Engagement_Objects: #loop through the engagement objects
                            if text in element[0]: #if telegram response text is an element of the an engagement object
                                cur.execute("UPDATE salesforce.resource__c SET engagement__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(element[0][1]),user_id)) #set engagement__c = engagement id of Engagment object
                                con.commit()
                        post(chat_id,"What date will you be rolling off?")
                        keyb(chat_id,"Enter the day (dd/mm/yyyy):",day)
                        Resource[index].phase = 2 #set the resource phase attribute to 2 - next phase of the conversation
                    else: #if telegram user's response was not an option on the list
                        post (Resource[index].user_id, 'Invalid response. Try again.')

                elif Resource[index].phase == 2:
                    if [text] in day:
                        Resource[index].date = str(Resource[index].date) + text
                        keyb(chat_id,"Enter the month:",month)
                        Resource[index].phase =3
                    else:
                        post(Resource[index].user_id,'Invalid response. Try again.')

                elif Resource[index].phase == 3:
                    if [text] in month:
                        month_num = ['January','February','March','April','May','June','July','August','September','October','November','December'].index(text)+1
                        Resource[index].date = str(month_num) +  '-'+str(Resource[index].date)
                        keyb(chat_id,"Enter the year:",year)
                        Resource[index].phase =4
                    else:
                        post(Resource[index].user_id,'Invalid response. Try again.')

                elif Resource[index].phase == 4:
                    if [text] in year:
                        Resource[index].date = text + '-'+str(Resource[index].date)
                        keybHide(Resource[index].user_id,'Thank you for you time. Keep up the good work!')
                        Resource[index].phase = 0
                        cur.execute("UPDATE salesforce.resource__c SET engagement_roll_off_date__c = '%s', awaiting_schedule_response__c = 'false' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].date),user_id))
                        con.commit()
                    else:
                        post(Resource[index].user_id,'Invalid response. Try again.')

            else: #if the awaiting_schedule_response checkbox is unchecked
                request = ai.text_request() #initiate Api.ai text request object
                request.query = text
                response = request.getresponse() #post text to the api.ai engine store the response a response object.
                API_AI_Response = response.read() #read the contents of the response object
                if '"intentName": "Greeting"' in API_AI_Response: #if the response contains the term 'greeting'
                        post(Resource[index].user_id,"Hello, I am DeloitteScheduleBot. I am currently still a noob as I've still got lots to learn. \n\nMy job is to help schedule resources. Ask me who is on the bench or who is on a project.")
                elif '"intentName": "System Query"' in API_AI_Response and Resource[index].approved: #if the response contains the term 'system query'
                    if '"SystemObject": "Bench"' in API_AI_Response: #if the response contains the term 'bench'
                        temp_string = "Here's a list of employees on the bench:\n\n"
                        cur.execute("SELECT name, on_project__c FROM salesforce.resource__c WHERE on_project__c = 'false' AND Employee_Status__c = 'Active'")
                        rows = cur.fetchall()
                        for row in rows:
                            temp_string = temp_string + str(row[0]) + '\n'
                        post(Resource[index].user_id,temp_string)
                    elif '"SystemObject": "Project"' in API_AI_Response: #if the response contains the term 'project'
                        temp_string = "Here's a list of employees who are on billable projects:\n\n"
                        cur.execute("SELECT name, on_project__c FROM salesforce.resource__c WHERE on_project__c = 'true' AND Employee_Status__c = 'Active'")
                        rows = cur.fetchall()
                        for row in rows:
                            temp_string = temp_string + str(row[0]) + '\n'
                        post(Resource[index].user_id,temp_string)
                elif Resource[index].approved: #if the response does not contain any known terms
                    post(Resource[index].user_id,"I didn't quite understand that. I will be posting this to my database to learn from at a later stage.")
                    cur.execute("INSERT INTO salesforce.new__c (New_Headline__c,News_Text__c) VALUES ('%s', '%s')" % (str('Unrecognised post by: ' + name),text.replace("'", "")))
                    con.commit()
                else:
                    post(Resource[index].user_id,"Your access to the DeloitteScheduleBot is waiting for approval. Once approved, you will be able to interact with this bot. For now, you can enjoy some small talk with the bot.")

        except TypeError: #if an error is caused, delete the telegram user from the Resources object and then loop back to the 'Receive message loop'. Don't increment the offset variable so the previously received message is recieved again so that a new resource record can be created for the user in RAM and on Salesforce.
            print str(Resource[index].user_id + " " + Resource[index].name)
            del Resource[index]
            print 'deleting old resource'
            break

        offset = update_id + 1 #increment the offset variable to receive the next message
        telegram_result = "" #refresh the telegram_result variable
        index = -1 #refresh the index variable
########################################################
