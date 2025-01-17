# This script is designed to be run once an hour
# it searches for the given tags over a specified
# time period. For each result, the requester email
# is extracted and appended to a spreadsheet

from datetime import datetime, timedelta
from base64 import b64encode
import pandas as pd
import configparser
import requests
import logging
import smtplib
import json
import os

config = configparser.RawConfigParser()
config.read('../src/auth.ini')
OUTPUT_FILE = config['default']['EmailList'].strip('"')
DOMAIN = config['zendesk']['Domain'].strip('"')
AUTH = config['zendesk']['Credentials'].strip('"')
SENDER = config['email']['Sender'].strip('"')
PASS = config['email']['Password'].strip('"')
RECIPIENT = config['email']['Recipient'].strip('"')
TAGS = config['mods']['SearchTags'].strip('"')

def get_formatted_datetimes(t_delta):
  now = datetime.utcnow().replace(microsecond=0, second=0, minute=0)
  start_date = (now + timedelta(hours= -t_delta))
  #start date/time formatted for get request
  st0 = start_date.strftime("%Y-%m-%dT%H:%M:%SZ") 
  sub_start_date = (start_date + timedelta(hours= 1))
  #end date/time formatted for get request
  st1 = sub_start_date.strftime("%Y-%m-%dT%H:%M:%SZ") 
  #date/time separately formatted for excel
  xdst0, xtst0 = start_date.strftime("%Y-%m-%d"), start_date.strftime("%H") 
  xtst1 = now.strftime("%H")
  return st0, st1, xdst0, xtst0, xtst1

def get_reqid(dom, auth, st0, st1, tags):
  print(b64encode(auth.encode('utf-8'))[2:-1])
  header = {"Authorization": "Basic {}".format(str(b64encode(auth.encode('utf-8')))[2:-1])}
  url = f"https://{dom}.zendesk.com/api/v2/search.json?query=type:ticket+created>{st0}+created<{st1}+tags:{tags}"

  try:
    res = requests.get(url, headers=header)
    r = json.loads(res.text)
    return r
  except Exception as err: 
    print('Error making zendesk GET request:', str(err))
    exit()

def get_email_list(dom, auth, reqid):
  print(b64encode(auth.encode('utf-8'))[2:-1])
  header = {"Authorization": "Basic {}".format(str(b64encode(auth.encode('utf-8')))[2:-1])}
  url = f"https://{dom}.zendesk.com/api/v2/users/{reqid}"

  try:
    res = requests.get(url, headers=header)
    r = json.loads(res.text)
    return r['user']['email']
  except Exception as err: 
    print('Error making zendesk GET request:', str(err))
    exit()

def populator(dom, auth, OUTPUT_FILE, tags):
    
  columns = list(range(24))
  EmailList = pd.DataFrame(columns = columns)
  EmailList.to_csv(OUTPUT_FILE)

  try:
    for i in range(4): # (4380 HOURS IN HALF A YEAR)
      st0, st1, xdst0, xtst0, xtst1 = get_formatted_datetimes(i)

      lst = get_reqid(dom, auth, st0, st1, tags)
      print(lst)

      EmailList.at[str(xdst0), int(xtst0)] = str(lst["count"])
    EmailList.to_csv(OUTPUT_FILE)
  except Exception as e:
    print('Error populating database: {}'.format(str(e)))

if os.path.exists(OUTPUT_FILE) == False:
    populator(DOMAIN, AUTH, OUTPUT_FILE, TAGS)
else:
    pass

def main(logger):

    st0, st1, xdst0, xtst0, xtst1 = get_formatted_datetimes(1)
    ReqIDList = []
    EmailList = []
    TicketResults = get_reqid(DOMAIN, AUTH, st0, st1, TAGS)
    for ticket in TicketResults['results']:
        ReqIDList.append(ticket['requester_id'])
        #ReqIDList = ReqIDList.astype(int)
        # print(EmailList.shape)
    try:
        print(ReqIDList)
        pass 
    except Exception as e:
        logger.warning('Error saving file, {}'.format(str(e)))

    for i in ReqIDList:
        EmailList.append(get_email_list(DOMAIN, AUTH, i))
        
    try:
        print(EmailList)
        EmailList = pd.DataFrame
        logger.warning("Sending report to {}\n".format(RECIPIENT))
        # send_report(RECIPIENT, EmailList, tags, delta, (SENDER, PASS))
    except Exception as e:
        logger.exception('{}\nError sending the report!'.format(str(e)))
    logger.warning('SUCCESS')

        # EmailList = EmailList.append(pd.Series(ticket['user']['email']), ignore_index=True)


# takes the recipient email, hourly count, and frequent tags as arguments
# auth should be a tuple containing the sender email id and sender email id password
# builds a message and sends it to the recipient

def send_report(to, tags, xdst0, xtst0, xtst1, emaillist, auth = None, subject='Email List Update!'):
    try:
        # creates SMTP session
        email = smtplib.SMTP('smtp.gmail.com', 587)

        # start TLS for security
        email.starttls()

        # authentication
        email.login(auth[0], auth[1])

        # craft the message
        message = ("Greetings Crunchyroll Humans, on {}, between {} and {}, for the tag {}, the following emails were gathered: {}.").format(xdst0, xtst0, xtst1, tags, emaillist)
        message = 'Subject: {}\n\n{}'.format(subject, message).encode('utf-8')

        # send the email
        email.sendmail(auth[0], to, message)

        # terminate the session
        email.quit()
    except Exception as e:
        print('ERROR: ', str(e))
        exit()
    return 0




if __name__ =="__main__":
    # TODO: set logging level based on input
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    main(logger)