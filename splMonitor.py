import requests, urllib3, datetime, time, smtplib, ssl, email
from email.mime.multipart import MIMEMultipart
from email.mime import text

### Used to disable Insecure warning despite using https...
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

basicAuth = requests.auth.HTTPBasicAuth('[API USERNAME]', '[API PASSWORD]')
gmailUser = { 'username': '[GMAIL ADDRESS]', 'password': "[GMAIL PASSWORD]" }

recipientEmail = "[YOUR EMAIL]"

splunkHost = "[SPLUNK SERVER ADDRESS]"
splunkPort = "[SPLUNK API PORT]"

### Splunk Search for usage data.
search = """host=splunk index=_internal group="per_host_thruput" NOT series="splunk" earliest=@d | eval mb=kb/1024 | stats sum(mb) as totalToday by series | eventstats sum(totalToday) as Total | sort - totalToday | head 1 | eval percent=round(((totalToday/500) * 100), 2) | where percent>=70 | eval percent=percent . " %" | eval hostpercent=round(((totalToday/Total) * 100), 2) . " %" | eval totalToday=round(totalToday, 2) . " Mb" | eval Total=round(Total, 2) . " Mb" | table series totalToday hostpercent Total percent | rename series as "Top Host", totalToday as "Host Data Ingested", Total as "Total Data Ingested Today", hostpercent as "Percentage of Total from Host", percent as "Percentage of License Used" """

### Used to build the html table from the splunk object returned
returnTable = ''
### Base Functions:

## print to screen with timestamp - looks cleaner in code this way
def log(message):
    print("[" + str(getTimeStamp()) + "] " + str(message))

## Get the current Time stamp for logging purpose.
def getTimeStamp():
    return datetime.datetime.now()

## Send the actual email.
def sendEmail():
    message = MIMEMultipart("alernative")
    message["Subject"] = "Splunk License Usage Alert"
    message["From"] = "Spunk Server <" + gmailUser['username'] + ">"
    message["To"] = recipientEmail

    html = ''
    with open('/opt/splunk_scripts/splMonitor/email_header.html', 'r') as file:
        html += file.read()
    html += returnTable
    with open('/opt/splunk_scripts/splMonitor/email_footer.html', 'r') as file:
        html += file.read()
    #message.attach(email.mime.text.MIMEText(text))
    message.attach(email.mime.text.MIMEText(html, 'html'))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(gmailUser['username'], gmailUser['password'])
        server.sendmail(gmailUser['username'], recipientEmail, message.as_string())

### create job to get sid
response = requests.post("https://" + splunkHost + ":" + splunkPort + "/services/search/jobs/", {"auth": basicAuth,"search": "search " + search, "output_mode":"json"}, verify=False)

### This is to prevent errors if no data is returned
if (response.status_code == 201):
    sid = response.json()['sid']
    log('SID Received :: ' + sid)
    searchDone = False
    while (not searchDone):
        log("Checking SID :: " + str(sid))
        ### Check if Job is done - Otherwise search will return no results.
        check = requests.get("https://" + splunkHost + ":" + splunkPort + "/services/search/jobs/" + sid, {"auth": basicAuth, "output_mode":"json"}, verify=False)
        if(check.json()['entry'][0]['content']['isDone']):
            searchDone = True
        else:
            log("Job(" + str(sid) + ") not done. Sleeping 1 Second.")
            time.sleep(1)

    ### Job Should be done if it gets to this point. Meaning it should return results.
    log('Getting Results of SID :: ' + str(sid))
    results = requests.get("https://" + splunkHost + ":" + splunkPort + "/services/search/jobs/" + sid + "/results/", {"auth": basicAuth, "output_mode":"json"}, verify=False)

    ## Convert the return data to json obj
    resData = results.json()['results']

    ## Check if the results object contains data
    if(len(resData) > 0):
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

        log('Sending Alert Email to: ' + recipientEmail)
        sendEmail()

    else:
        log('No results. Presume usage is less the 70%.')

else:
    log('[ERROR] Did not receive a sid. :: Status: ' + str(response.status_code) )
