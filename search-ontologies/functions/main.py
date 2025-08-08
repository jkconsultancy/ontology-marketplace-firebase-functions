from firebase_functions import firestore_fn, https_fn

# The Firebase Admin SDK to access Cloud Firestore.
from firebase_admin import initialize_app, firestore, auth
import google.cloud.firestore
from dotenv import load_dotenv
from neo4j import GraphDatabase
import json
import os

# Load environment variables
load_dotenv()

# Neo4j connection configuration from environment variables
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

if not NEO4J_PASSWORD:
    raise ValueError("NEO4J_PASSWORD environment variable is required")


def get_neo4j_driver():
    """Create and return a Neo4j driver instance"""
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


app = initialize_app()


@https_fn.on_request()
def search_ontologies(req: https_fn.Request) -> https_fn.Response:
    """
    Firebase HTTPS function to find ontology nodes to for a given user.
    Returns a list of all ontology nodes created by the user, and those whose is_public property is set to true.
    """
    try:

        # Get Firebase Auth UID from headers
        auth_header = req.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return https_fn.Response(
                "Missing or invalid Authorization header.", status=401
            )
        id_token = auth_header.split("Bearer ")[1]

        # Verify Firebase ID token
        try:
            decoded_token = auth.verify_id_token(id_token)
            user_uid = decoded_token["uid"]
        except Exception as e:
            return https_fn.Response(f"Invalid token: {str(e)}", status=401)

        driver = get_neo4j_driver()
        with driver.session() as session:
            try:
                result = session.run(
                    """
                    MATCH (u:User {firebase_uid: $user_uid})
                    MATCH (o:Ontology)
                    WHERE ( (u)-[:CREATED]->(o) ) OR ( o.is_public IS NOT NULL AND o.is_public = true )
                    RETURN elementId(o) AS node_id, o.name AS name, o.description AS description, o.is_public AS is_public, o.source_url AS source_url, o.image_url AS image_url
                    """,
                    user_uid=user_uid,
                )

                # print(f"Result: {result}")
                # [print(f"Record: {record}") for record in result]
                # print(f"First record: {result}")
                ontologies = [
                    {
                        "node_element_id": record["node_id"],
                        "name": record["name"],
                        "description": record["description"],
                        "is_public": record["is_public"],
                        "source_url": record.get("source_url"),
                        "image_url": record.get("image_url"),
                    }
                    for record in result
                ]
                # ontologies = [dict(record["o"]) for record in result]

                if not ontologies or len(ontologies) == 0:
                    ontologies = []

                return https_fn.Response(
                    json.dumps(ontologies),
                    status=200,
                )
            except Exception as e:
                return https_fn.Response(f"Error querying Neo4j: {str(e)}", status=500)
    except Exception as e:
        return https_fn.Response(f"Error: {str(e)}", status=500)
