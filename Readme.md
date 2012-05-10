# RESTMail

RESTMail is a SMTP server with a HTTP REST interface for accessing mails. 

STMP server built on Inbox.py (https://github.com/kennethreitz/inbox.py).


## Required packages

* Inbox.py

## REST API

### Get mails

Request: `GET /inbox/:email-address`

Response:

    [
      {
        "received": "2012-05-11 01:59:38", 
        "sender": "mgronhol@localhost.local", 
        "attachments": [
           {
             "type": "image/png", 
             "payload-id": "9cd6b97ed75d36ca6eeff82dffa098e375c4fe84", 
             "filename": "logo.png"
         }
        ], 
        "content": "Example message", 
        "to": [
        "mgronhol@local.host"
       ], 
       "id": "5abf12ad7dae55a2faad5c36af198631", 
       "subject": "Test message"
      }
   ]


### Get attatchment

Request: `GET /files/:payload-id`

