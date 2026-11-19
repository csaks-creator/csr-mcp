import json
import base64
import urllib.request
import boto3

# --- Jira account settings ---
BASE = "https://bedrock-kb-demo.atlassian.net"   # no trailing slash
EMAIL = "bettercallrahul@gmail.com"
TOKEN = "ATATT3xFfGF0RPGir64nfa5TEPssYR7vOizhx6Zboye0aG5NqorNz2pFVzfphf9cHmkupj79tIRzSpcRnpQ4f46eZN3S_bzLDSJbDEldiIN5_GqTlHPLMlQ9m5gfvswk_dLE7gQJ5MyA6BMht4ZLoL2jE8BfICGnNhHJ2pcxkp4pCgerNUu0JXQ=49A70FBC"
PROJECT = "SDD"

# For SNS
client = boto3.client('sns')

def lambda_handler(event, context):
    # 1. Read what the agent sent.
    summary = event["summary"]
    description = event.get("description")
    print (f"Input event is: {event}")

    # 2. Build the Jira issue - https://developer.atlassian.com/server/jira/platform/jira-rest-api-examples/
    issue = {
        "fields": {
            "project": {"key": PROJECT},
            "summary": summary,
            "issuetype": {"name": "Task"},
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": description}]}
                ],
            },
        }
    }
    print(f"Request to Jira : {issue}")

    # 3. Build the login header: base64 of "email:token" for Basic auth.
    login = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
    headers = {
        "Authorization": f"Basic {login}",
        "Content-Type": "application/json",
    }
    # 4. Send it to Jira.
    request = urllib.request.Request(
        f"{BASE}/rest/api/3/issue",
        data=json.dumps(issue).encode(),
        headers=headers,
        method="POST",
    )

    response = urllib.request.urlopen(request)
    result = json.loads(response.read())
    print(f"response from Jira: {result}")

    # For SNS
    response = client.publish(
            TopicArn='arn:aws:sns:us-east-1:196715057542:helpdesk-alert',
            Subject="New IT ticket",
            Message=result["key"],
        )   
        


    # 5. Return the new issue key and link.
    key = result["key"]
    return {"issue_key": key,"url": f"{BASE}/browse/{key}"}

