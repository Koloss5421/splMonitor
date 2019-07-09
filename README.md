# splMonitor
Splunk License Monitor is a relatively simple script run via cron every 10 minutes to ensure alert you when your license used percentage is greater than or equal to a value set by yourself.

## Features
 - Simple threshold settings.
 - Sends email to any email from a gmail account over 465
 - Automatically disables inputs assigned to the "search" app.
 - Multiple email spam preventions. It will only send a single email per hour unless your Usage goes over disablePercent. If it doesn't change after an hour it won't send another email with the same value.
 - Automatically re-enables inputs when the input falls below the threshold(typically only after 12AM/00:00:00)

## Setup
Recommended: Create a gmail account for the app to use with a strong(32 Chars+) randomly generated password.

Store the files on the splunk server (unless you allow external API requests). For this example I will use ```/opt/splunk_scripts/``` on the splunk server itself.

If firewalled - Allow out: 465(SMTP).

Using the '%%percent%%' in your email allows the email to contain your set percentage before emails being.

You should only have to modify these values with your own. If you change the location of the script, be sure to change the workingDir value as well as the cron output location.
```python
basicAuth = requests.auth.HTTPBasicAuth('[SPLUNK USER]', '[SPLUNK PASS]') ## Your splunk username/password
gmailUser = { 'username': '[GMAIL EMAIL]', 'password': "[GMAIL PASSWORD]" } ## Gmail account the script will use.

recipientEmail = "[RECIPIENT EMAIL]" ## Your email or whatever email you want to receive the alerts

splunkHost = "[SPLUNK ADDRESS]" ## Your splunk instance address(ex Splunk.home.net) or any IP (ex 172.16.100.5)
splunkPort = "[SPLUNK PORT]" ## Your splunk management port

emailPercent = 70 ## The Percent the script will begin sending emails
disablePercent = 90 ## The percent at which your inputs will be disabled
workingDir = "/opt/splunk_scripts/splMonitor/" ## Wherever your html and json files are.
```

Add 
Command:
```
crontab -e
```
Add Line for every 10 minutes. Redirect log location wherever you want it. The log output can be ingested.
```
*/10 * * * * python3 /opt/splunk_scripts/splMonitor/splMonitor.py >> /opt/splunk_scripts/logs/splMonitor.log
```

##### Example Email Output (Template not provided)
![Email Screenshot](https://image.prntscr.com/image/7ZHKkZtKRTmzGO7nPPeqKA.png)

##### Example Log output
![Log Screenshot](https://image.prntscr.com/image/iE4AEhOOQ1i6IYNBLbUTWw.png)
