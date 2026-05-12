import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Import from neo4j_graphrag instead of openai/langchain
from neo4j_graphrag.llm import AzureOpenAILLM
from neo4j_graphrag.embeddings import AzureOpenAIEmbeddings

# Load environment variables immediately
load_dotenv()


# Neo4j config helpers
def get_neo4j_config():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    pwd = os.getenv("NEO4J_PASSWORD")
    return uri, user, pwd


# Driver
def get_driver():
    uri, user, pwd = get_neo4j_config()
    
    if not uri or not user or not pwd:
        raise ValueError(
            "Neo4j credentials missing. Please set NEO4J_URI, "
            "NEO4J_USERNAME, and NEO4J_PASSWORD in your .env file or environment variables."
        )
    
    print(f"Connecting to Neo4j at: {uri}")
    print(f"Username: {user}")
    
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    
    # Test connection
    try:
        driver.verify_connectivity()
        print("===> Neo4j connection verified!")
    except Exception as e:
        print(f"XXXX: Neo4j connection failed: {e}")
        driver.close()
        raise
    
    return driver


# LLM - Using neo4j_graphrag's Azure wrapper
def get_llm(model_name="gpt-4o"):
    api_key = os.getenv("DIAL_API_KEY")
    
    if not api_key:
        raise ValueError("DIAL_API_KEY missing in environment.")

    return AzureOpenAILLM(
        azure_endpoint="https://ai-proxy.lab.epam.com",
        api_key=api_key,
        api_version="2024-02-01",
        azure_deployment=model_name,
        model_name=model_name,
        # Low temperature for deterministic extraction
        model_params={
            "temperature": 0,
            "max_tokens": 8192
        }
    )


# Embeddings for retrievers - Using neo4j_graphrag's Azure wrapper
def get_embedder(model="text-embedding-ada-002"):
    api_key = os.getenv("DIAL_API_KEY")
    
    if not api_key:
        raise ValueError("DIAL_API_KEY missing in environment.")

    return AzureOpenAIEmbeddings(
        azure_endpoint="https://ai-proxy.lab.epam.com",
        api_key=api_key,
        api_version="2024-02-01",
        azure_deployment=model,
        model=model
    )