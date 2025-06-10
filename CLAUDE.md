Context:
I am a staff software engineer in a large-scale software company, where backend services are in a microservice architecture. We have application logs in Prometheus and can also be accessed in Grafana log explorer. 
When there is any oncall alert fires through opsgenie we need to log into grafana, search for application logs manually. 

What I want:
I want a python script, which will get the applications logs, given some filters e.g. app name, message contains, time range, log type etc. Then It will summarise the errors, give potential places to look into, and which service, how often its happening, traces, reasoning. 

The script can used eu.anthropic.claude-3-7-sonnet from AWS bedrock INFERENCE PROFILE="arn:aws:bedrock:eu-west-1:951719175506:inference-profile/eu.anthropic.claude-3-7-sonnet-20250219-v1:0", and AWS_REGION "eu-west-1"
The script can assume that access to application logs through kubernetes is already done. 
It can use prometheus endpoints to get data if needed. 

Deliverables 
#1 Python scripts
#2 a how-to markdown file
#3 create a Readme file


