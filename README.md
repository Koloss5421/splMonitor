# splMonitor
Splunk License Monitor is a relatively simple script run via cron every 10 minutes to ensure alert you when your license used percentage is greater than or equal to a value set by yourself.

The script runs a search through your splunk API, Gets the SID of the job, and checks the job until it is done to get the results. If Results are returned, it means the usage percent is at or above a value you set and the script will use SMTPS to send an email via google SMTP to alert you. Otherwise it just logs that it ran.

If you use your own splunk search, ensure it only returns data when it is above your threshold.

## Setup
Store the files on the splunk server (unless you allow external API requests). For this example I will use ```/opt/splunk_scripts/``` on the splunk server itself.

If firewalled - allow port 465 out.

Open splMonitor.py in your favorite editor and add your Host(ln 13), Port(ln 14), API user/pass(ln 8), and Gmail user/pass(ln 9) (recommend making an account just for this) and recipientEmail(Admin/Your email)(ln 11).

If you modify the location of the file edit the directory in 

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
