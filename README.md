# Ontology Marketplace Firebase / Google Cloud Functions

## Requirements

- [Firebase CLI](https://firebase.google.com/docs/functions/get-started?authuser=0&gen=2nd#python)
- [Gloud CLI]()

## Local Testing

cd into the appropriate Functions folder then use the firebase emulator.

First time run: `firebase init emulators`

To start: `firebase emulators:start`

To get a new token for a given user:

```
API_KEY="<firebase_web_api_key>"
EMAIL="<user_email>"
PASSWORD="<user_password>"

ID_TOKEN=$(curl -s "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=$API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"returnSecureToken\":true}" \
  | jq -r '.idToken')

echo "ID Token: $ID_TOKEN"
```

## Deploying

1. First add credentials to the target firebase function
   `firebase functions:config:set neo4j.uri="bolt://localhost:7687" neo4j.username="neo4j" neo4j.password="your_password"`

2. Then deploy
   `firebase deploy`

The env creds will likely fail to upload, try again with glcloud cli:

```
gcloud functions deploy add_ontology_node \
--runtime python311 \
--entry-point add_ontology_node \
--region us-central1 \
--set-env-vars NEO4J_URI='<uri>',NEO4J_USERNAME='neo4j',NEO4J_PASSWORD='<password>'
```
