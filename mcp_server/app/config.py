"""
PanKB MCP Server Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Server
    SERVER_NAME = "pankb"
    SERVER_VERSION = "1.0.0"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # MongoDB - Two database connections
    # MONGODB_PANKB_CONN_STRING: PanKB data (for queries)
    # MONGODB_CONN_STRING: Vector data (for RAG)
    MONGODB_PANKB_CONN_STRING = os.getenv("MONGODB_PANKB_CONN_STRING")
    MONGODB_VECTOR_CONN_STRING = os.getenv("MONGODB_CONN_STRING")
    MONGODB_DB_NAME = os.getenv("MONGODB_NAME", "pankb").strip("'\"")
    MONGO_USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME")
    MONGO_PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD")

    # Azure Blob Storage
    AZURE_BLOB_BASE_URL = "https://pankb.blob.core.windows.net/data/PanKB/web_data_v2/"

    # Collections
    COLLECTIONS = {
        "organisms": "pankb_organisms",
        "gene_annotations": "pankb_gene_annotations",
        "gene_info": "pankb_gene_info",
        "genome_info": "pankb_genome_info",
        "pathway_info": "pankb_pathway_info",
        "isolation_info": "pankb_isolation_info",
        "genome_phylons": "pankb_genome_phylons",
        "gene_phylons": "pankb_gene_phylons",
        "pankb_stats": "pankb_stats",
    }

    @classmethod
    def get_pankb_mongodb_uri(cls) -> str:
        """Get PanKB data MongoDB connection URI (for data queries)"""
        if cls.MONGODB_PANKB_CONN_STRING:
            return cls.MONGODB_PANKB_CONN_STRING
        raise ValueError("MONGODB_PANKB_CONN_STRING not configured.")

    @classmethod
    def get_vector_mongodb_uri(cls) -> str:
        """Get Vector MongoDB connection URI (for RAG)"""
        if cls.MONGODB_VECTOR_CONN_STRING:
            return cls.MONGODB_VECTOR_CONN_STRING
        raise ValueError("MONGODB_CONN_STRING not configured.")

    @classmethod
    def validate(cls) -> bool:
        try:
            cls.get_pankb_mongodb_uri()
            return True
        except ValueError as e:
            print(f"Error: {e}")
            return False
