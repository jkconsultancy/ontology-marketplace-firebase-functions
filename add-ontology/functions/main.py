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
def add_ontology(req: https_fn.Request) -> https_fn.Response:
    """
    Firebase HTTPS function to add an ontology node to Neo4j.
    Expects JSON payload with 'name', 'description', and optional 'properties'.
    Also merges a node for the authenticated user and creates a relationship to the ontology.
    """
    try:
        data = req.get_json(force=True)
        name = data.get("name")
        description = data.get("description")
        properties = data.get("properties", {})

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

        if not name or not description:
            return https_fn.Response(
                "Missing 'name' or 'description' in payload.", status=400
            )

        driver = get_neo4j_driver()
        with driver.session() as session:
            result = session.run(
                """
                MERGE (u:User {firebase_uid: $user_uid})
                CREATE (o:Ontology {name: $name, description: $description})
                SET o += $properties
                CREATE (u)-[:CREATED]->(o)
                RETURN elementId(o) AS node_id, u.firebase_uid AS user_id
                """,
                user_uid=user_uid,
                name=name,
                description=description,
                properties=properties,
            )
            record = result.single()
            node_id = record["node_id"]
            user_id = record["user_id"]

        return https_fn.Response(
            f"Ontology node created with ID: {node_id} and linked to user ID: {user_id}",
            status=201,
        )
    except Exception as e:
        return https_fn.Response(f"Error: {str(e)}", status=500)
