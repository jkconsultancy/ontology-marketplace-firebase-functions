from firebase_functions import firestore_fn, https_fn

# The Firebase Admin SDK to access Cloud Firestore.
from firebase_admin import initialize_app, firestore, auth
import google.cloud.firestore


from dotenv import load_dotenv
from neo4j import GraphDatabase
import os

# Load environment variables
load_dotenv()

# Neo4j connection configuration from environment variables
NEO4J_URI = os.environ.get("NEO4J_URI") or os.environ.get("neo4j_uri")
NEO4J_USER = os.environ.get("NEO4J_USERNAME") or os.environ.get("neo4j_username")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD") or os.environ.get("neo4j_password")

if not NEO4J_PASSWORD:
    raise ValueError("NEO4J_PASSWORD environment variable is required")


def get_neo4j_driver():
    """Create and return a Neo4j driver instance"""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


app = initialize_app()


@https_fn.on_request()
def delete_ontology(req: https_fn.Request) -> https_fn.Response:
    """
    Firebase HTTPS function to delete an ontology node from Neo4j.
    Expects JSON payload with 'node_id'.
    Also merges a node for the authenticated user and creates a relationship to the ontology.
    """
    try:
        # CORS preflight
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Authorization, Content-Type",
            "Access-Control-Max-Age": "3600",
        }

        if req.method == "OPTIONS":
            return https_fn.Response("", status=204, headers=cors_headers)

        data = req.get_json(force=True)
        uuid = data.get("uuid")

        # Get Firebase Auth UID from headers
        auth_header = req.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return https_fn.Response(
                "Missing or invalid Authorization header.", status=401, headers=cors_headers
            )
        id_token = auth_header.split("Bearer ")[1]

        # Verify Firebase ID token
        try:
            decoded_token = auth.verify_id_token(id_token)
            user_uid = decoded_token["uid"]
        except Exception as e:
            return https_fn.Response(f"Invalid token: {str(e)}", status=401, headers=cors_headers)

        if not uuid:
            return https_fn.Response(
                "Missing Ontology 'uuid' in payload.", status=400, headers=cors_headers
            )

        driver = get_neo4j_driver()
        with driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {firebase_uid: $user_uid})-[r:CREATED|OWNS|MANAGES]->(o:Ontology {uuid: $uuid})
                WITH o, u, o.uuid AS uuid, u.firebase_uid AS user_id
                DETACH DELETE o
                RETURN uuid, user_id
                """,
                user_uid=user_uid,
                uuid=uuid,
            )
            record = result.single()
            if not record:
                return https_fn.Response(
                    f"No ontology found with uuid: {uuid}",
                    status=404,
                    headers=cors_headers,
                )
            deleted_uuid = record["uuid"]
            user_id = record["user_id"]

        return https_fn.Response(
            f"Ontology node deleted with uuid: {deleted_uuid} that was linked to user ID: {user_id}",
            status=201,
            headers=cors_headers,
        )
    except Exception as e:
        return https_fn.Response(f"Error: {str(e)}", status=500, headers=cors_headers)
