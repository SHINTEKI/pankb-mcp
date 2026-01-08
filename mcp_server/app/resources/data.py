"""
Resources: Provide data for LLM to read
"""
from fastmcp import FastMCP

mcp = FastMCP(name="DataResources")


# ===== Static Resources =====
@mcp.resource("config://server")
def get_server_config() -> dict:
    """Get server configuration information"""
    return {
        "name": "PanKB-MCP",
        "version": "0.1.0",
        "description": "Genomic data analysis service",
        "available_tools": ["chart", "analysis", "query", "rag"]
    }


@mcp.resource("config://analysis")
def get_analysis_config() -> dict:
    """Get analysis module configuration"""
    return {
        "supported_methods": ["statistics", "comparison", "clustering"],
        "max_data_points": 10000,
        "default_precision": 4
    }


# ===== Dynamic Resources (Templates) =====
@mcp.resource("genome://{genome_id}/info")
def get_genome_info(genome_id: str) -> dict:
    """Get basic genome information"""
    # TODO: Query from database
    return {
        "id": genome_id,
        "name": f"Genome {genome_id}",
        "description": "Placeholder genome info",
        "length": 1000000,
        "gc_content": 0.45
    }


@mcp.resource("genome://{genome_id}/genes")
def get_genome_genes(genome_id: str) -> list[dict]:
    """Get gene list of a genome"""
    # TODO: Query from database
    return [
        {"gene_id": f"{genome_id}_gene1", "name": "geneA", "start": 100, "end": 500},
        {"gene_id": f"{genome_id}_gene2", "name": "geneB", "start": 600, "end": 1200},
    ]


@mcp.resource("species://{species_name}/genomes")
def get_species_genomes(species_name: str) -> list[dict]:
    """Get all genomes of a species"""
    # TODO: Query from database
    return [
        {"genome_id": f"{species_name}_001", "strain": "wild_type"},
        {"genome_id": f"{species_name}_002", "strain": "mutant"},
    ]
