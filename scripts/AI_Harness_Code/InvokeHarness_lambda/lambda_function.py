import json
import uuid
import boto3

HARNESS_ARN = 'arn:aws:bedrock-agentcore:us-east-1:196715057542:harness/service_desk_agent-9azKjr0Vnm'
client = boto3.client("bedrock-agentcore")

def lambda_handler(event, context):
    # 1. Read the message and session id from the event.
    message = event.get("message")
    # Use the session id the caller sends (keeps one conversation together).
    session_id = event.get("session_id") 
    print(message)

    # 2. Invoke the harness.
    response = client.invoke_harness(
        harnessArn=HARNESS_ARN,
        runtimeSessionId=session_id,
        messages=[{"role": "user", "content": [{"text": message}]}],
    )
    print(response)

    # 3. Collect the streamed reply into one string.
    reply = ""
    for chunk in response["stream"]:
        if "contentBlockDelta" in chunk:
            reply += chunk["contentBlockDelta"]["delta"].get("text", "")

    print(reply)
    # 4. Return the reply and the session id used.
    return {"reply": reply, "session_id": session_id}            
