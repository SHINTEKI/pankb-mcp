"""
Data Processing Utilities for PanKB MCP Server
"""
from typing import List, Dict, Any
import pandas as pd


class DataProcessor:
    """Data processing and transformation utilities"""

    @staticmethod
    def calculate_pangenome_statistics(organism_data: Dict) -> Dict[str, Any]:
        """Calculate pangenome statistics from organism data"""
        openness = organism_data.get("openness", 0)
        if isinstance(openness, str):
            openness_map = {"closed": 0.1, "moderately open": 0.35, "open": 0.7}
            openness = openness_map.get(openness.lower(), 0.0)

        stats = {
            "species": organism_data.get("species"),
            "total_genomes": organism_data.get("genomes_num", 0),
            "openness": float(openness),
        }

        gene_dist = organism_data.get("gene_class_distribution", {})

        if isinstance(gene_dist, list):
            core_genes = gene_dist[0] if len(gene_dist) > 0 else 0
            shell_genes = gene_dist[1] if len(gene_dist) > 1 else 0
            cloud_genes = gene_dist[2] if len(gene_dist) > 2 else 0
            total_genes = sum(gene_dist)
        elif isinstance(gene_dist, dict):
            core_genes = gene_dist.get("core", 0)
            shell_genes = gene_dist.get("shell", 0)
            cloud_genes = gene_dist.get("cloud", 0)
            total_genes = sum(gene_dist.values()) if gene_dist else 0
        else:
            core_genes = shell_genes = cloud_genes = total_genes = 0

        stats.update({
            "core_genes": core_genes,
            "shell_genes": shell_genes,
            "cloud_genes": cloud_genes,
            "total_genes": total_genes,
        })

        if total_genes > 0:
            stats["core_percentage"] = (core_genes / total_genes) * 100
            stats["shell_percentage"] = (shell_genes / total_genes) * 100
            stats["cloud_percentage"] = (cloud_genes / total_genes) * 100

        return stats

    @staticmethod
    def format_gene_info_table(gene_info_list: List[Dict]) -> str:
        """Format gene info as markdown table"""
        if not gene_info_list:
            return "No gene information found."

        df = pd.DataFrame(gene_info_list)
        columns = ['gene', 'genome_id', 'locus_tag', 'protein', 'start_position', 'end_position', 'strand']
        available_columns = [col for col in columns if col in df.columns]

        return df[available_columns].to_markdown(index=False)