import requests, urllib3, datetime, time, smtplib, ssl, email, json
from email.mime.multipart import MIMEMultipart
from email.mime import text

### Used to disable Insecure warning despite using https...
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

basicAuth = requests.auth.HTTPBasicAuth('[SPLUNK USER]', '[SPLUNK PASS]')
gmailUser = { 'username': '[GMAIL EMAIL]', 'password': "[GMAIL PASSWORD]" }

recipientEmail = "[RECIPIENT EMAIL]"

splunkHost = "[SPLUNK ADDRESS]"
splunkPort = "[SPLUNK PORT]"

emailPercent = 70
disablePercent = 90
workingDir = "/opt/splunk_scripts/splMonitor/"

### Splunk Search for usage data.
search = """host=splunk index=_internal group="per_host_thruput" NOT series="splunk" earliest=@d | eval mb=kb/1024 | stats sum(mb) as totalToday by series | eventstats sum(totalToday) as Total | sort - totalToday | head 1 | eval percent=round(((totalToday/500) * 100), 2) | where percent>={} | eval percent=percent . " %" | eval hostpercent=round(((totalToday/Total) * 100), 2) . " %" | eval totalToday=round(totalToday, 2) . " Mb" | eval Total=round(Total, 2) . " Mb" | table series totalToday hostpercent Total percent | rename series as "Top Host", totalToday as "Host Data Ingested", Total as "Total Data Ingested Today", hostpercent as "Percentage of Total from Host", percent as "Percentage of License Used" """.format(emailPercent)

### Used to build the html table from the splunk object returned
returnTable = ''
isDisabling = False
### Base Functions:

## print to screen with timestamp - looks cleaner in code this way
def log(message):
    print("[{}] (splMonitor) {}".format(getTimeStamp(), message))

## Get the current Time stamp for logging purpose.
def getTimeStamp():
    return datetime.datetime.now()

## Send the actual email.
def sendEmail():
    message = MIMEMultipart("alernative")
    message["Subject"] = "Splunk License Usage Alert"
    message["From"] = "Spunk Server <{}>".format(gmailUser['username'])
    message["To"] = recipientEmail

    html = ''
    with open( workingDir+'email_header.html', 'r') as file:
        html += file.read().replace("%%percent%%", str(emailPercent))

    html += returnTable
    if (isDisabling):
        html += "<p>Due to the usage percentage reaching {}%, All data inputs have been disabled to prevent a license violation. The endpoints will be re-enabled when the daily value is less than {}% or you could manually re-enable the endpoints. If this threshold is too low, modify the splMonitor value 'disablePercent'.</p>".format(disablePercent, emailPercent)
    with open(workingDir+'email_footer.html', 'r') as file:
        html += file.read()
    message.attach(email.mime.text.MIMEText(html, 'html'))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(gmailUser['username'], gmailUser['password'])
        server.sendmail(gmailUser['username'], recipientEmail, message.as_string())

### create job to get sid
response = requests.post("https://{}:{}/services/search/jobs/".format(splunkHost, splunkPort), {"auth": basicAuth,"search": "search {}".format(search), "output_mode":"json"}, verify=False)

### Will be used if an email is sent or not
### Contains three fields "lastEmailTime": EpochTime, "inputsDisabled": Boolean, "lastUsage": float
with open( workingDir+'status.json', 'r') as file:
    status = json.load(file)


### This is to prevent errors if no data is returned
if (response.status_code == 201):
    sid = response.json()['sid']
    log('[INFO] SID Received :: ' + sid)

    searchDone = False
    while (not searchDone):
        log("[INFO] Checking SID :: {}".format(sid))
        ### Check if Job is done - Otherwise search will return no results.
        check = requests.get("https://{}:{}/services/search/jobs/{}".format(splunkHost, splunkPort, sid), {"auth": basicAuth, "output_mode":"json"}, verify=False)
        if(check.json()['entry'][0]['content']['isDone']):
            searchDone = True
        else:
            log("[INFO] Job({}) not done. Sleeping 1 Second.".format(sid))
            time.sleep(1)

    ### Job Should be done if it gets to this point. Meaning it should return results.
    log('[INFO] Getting Results of SID :: {}'.format(sid))
    results = requests.get("https://{}:{}/services/search/jobs/{}/results/".format(splunkHost, splunkPort, sid), {"auth": basicAuth, "output_mode":"json"}, verify=False)

    ## Convert the return data to json obj
    resData = results.json()['results']

    ## Check if the results object contains data
    if (len(resData) > 0):
        ### Generate the table that will be used in the return
        returnTable = """<tr></tr><table class="splunkTable" style="text-align: center;">
        <tr>"""

        ## Generate Table head based on key names
        for key in resData[0]:
            returnTable += '<th>' + key + '</th>'
        returnTable += """</tr>
        <tr>"""
        for key in resData[0]:
            returnTable += '<td>' + resData[0][key] + '</td>'
        returnTable += """</tr>
        </table>"""

        ### Convert the string returned "51.00 %" to just a number "51.00" and make a float
        percentUsed = float( resData[0]['Percentage of License Used'][:-2] )

        ### Check if an email has been sent in the last hour to prevent an email every 10 minutes. Percentage of License Used resData[0]['Percentage of License Used']
        if ( (( datetime.datetime.now().timestamp() ) >= ( status["lastEmailTime"] + 3600 )) or ( (percentUsed >= disablePercent) and not status["inputsDisabled"] ) ):
            if ( (percentUsed >= disablePercent) and not status["inputsDisabled"] ):
                isDisabling = True
                status["inputsDisabled"] = True
                log('[WARN] Disabling input endpoints! Usage has reached set limit: {}%!'.format(disablePercent))
                inputs = requests.get("https://{}:{}/services/data/inputs/all/".format(splunkHost, splunkPort), {"output_mode":"json"}, verify=False)
                inputJson = inputs.json()
                ### If the app is search, the endpoint is ingesting data to the search app and causes an increase in license usage
                for input in inputJson['entry']:
                    ### If the app is search, the endpoint is ingesting data to the search app and causes an increase in license usage
                    if( input['acl']['app'] == "search" ):
                        ### id Field has a complete link to the input by name just need to tack on enable/disable
                        setDisable = requests.post(input['id'] + "/disable", verify=False)

            if ( (percentUsed > status["lastUsage"]) or isDisabling):
                log('[WARN] Percent Used: {}%. Sending Alert Email to: {}'.format(percentUsed, recipientEmail))
                status["lastEmailTime"] = datetime.datetime.now().timestamp()
                sendEmail()
            else:
                log('[INFO] Status has not changed since last check. Not Sending Email.')
        else:
            log("[INFO] Percent Used: {} %.Last Email was sent {} mins ago".format(percentUsed, round((datetime.datetime.now().timestamp() - status["lastEmailTime"]) / 60 )))
    else:
        if (status['inputsDisabled']):
            status['inputsDisabled'] = False
            log("[INFO] Usage is now less than {}%. Re-enabling input endpoints".format(emailPercent))

            ### Get all the inputs on the server
            inputs = requests.get("https://{}:{}/services/data/inputs/all/".format(splunkHost, splunkPort), {"output_mode":"json"}, verify=False)
            inputJson = inputs.json()
            for input in inputJson['entry']:
                ### If the app is search, the endpoint is ingesting data to the search app and causes an increase in license usage
                if( input['acl']['app'] == "search" ):
                    ### id Field has a complete link to the input by name just need to tack on enable/disable
                    setEnable = requests.post(input['id'] + "/enable", verify=False)

        log('[INFO] No results. Presume usage is less than {}%.'.format(emailPercent))

else:
    log('[ERROR] Did not receive a sid. :: Status: {}'.format(response.status_code) )

### Write to the json file at the end of all actions
## Try to make lastUsage percentUsed
try:
    status['lastUsage'] = percentUsed
except NameError:
    ### Just needed something here...
    status['lastUsage'] = status['lastUsage']
    
with open( workingDir+'status.json', 'w') as file:
    json.dump(status, file)
