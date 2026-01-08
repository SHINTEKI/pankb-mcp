"""
Visualization Tools for PanKB MCP Server

These tools generate matplotlib figures and return them as MCP Image objects.
"""
from typing import Optional, Union
from collections import Counter
import logging
import io

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
from matplotlib.patches import Patch
import numpy as np

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from app.config import Config
from app.utils.connections import mongo_client

logger = logging.getLogger(__name__)

# Color schemes
PANGENOME_COLORS = {'Core': '#2ecc71', 'Accessory': '#f39c12', 'Rare': '#e74c3c'}

COG_NAMES = {
    'J': 'Translation', 'A': 'RNA processing', 'K': 'Transcription',
    'L': 'Replication', 'B': 'Chromatin', 'D': 'Cell cycle',
    'Y': 'Nuclear structure', 'V': 'Defense', 'T': 'Signal transduction',
    'M': 'Cell wall', 'N': 'Cell motility', 'Z': 'Cytoskeleton',
    'W': 'Extracellular', 'U': 'Secretion', 'O': 'PTM/chaperones',
    'C': 'Energy production', 'G': 'Carbohydrate metabolism',
    'E': 'Amino acid metabolism', 'F': 'Nucleotide metabolism',
    'H': 'Coenzyme metabolism', 'I': 'Lipid metabolism',
    'P': 'Inorganic ion transport', 'Q': 'Secondary metabolites',
    'R': 'General function', 'S': 'Function unknown', '-': 'Not in COG'
}


def fig_to_image(fig) -> Image:
    """Convert matplotlib figure to MCP Image object"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)
    return Image(data=buf.getvalue(), format="png")


mcp = FastMCP(name="ChartTools")


@mcp.tool()
def plot_gene_frequency_histogram(pangenome_analysis: str) -> Union[Image, str]:
    """
    Generate gene frequency histogram (U-shape curve) for a species.

    Args:
        pangenome_analysis: Species pangenome analysis name (e.g., 'Escherichia_coli')
    """
    collection = mongo_client.get_collection(Config.COLLECTIONS["gene_annotations"])

    pipeline = [
        {"$match": {"pangenome_analysis": pangenome_analysis}},
        {"$group": {"_id": "$frequency", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    results = list(collection.aggregate(pipeline))

    if not results:
        return f"No data found for {pangenome_analysis}"

    frequencies = [r["_id"] for r in results]
    counts = [r["count"] for r in results]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(frequencies, counts, color='steelblue', alpha=0.7, width=1.0)
    ax.set_xlabel('Gene Frequency (number of genomes)', fontsize=12)
    ax.set_ylabel('Number of Genes', fontsize=12)
    ax.set_title(f'Gene Frequency Distribution\n{pangenome_analysis.replace("_", " ")}', fontsize=14)
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    return fig_to_image(fig)


@mcp.tool()
def plot_pangenome_class_distribution(pangenome_analysis: str) -> Union[Image, str]:
    """
    Generate pie chart showing Core/Accessory/Rare gene distribution for a species.

    Args:
        pangenome_analysis: Species pangenome analysis name (e.g., 'Bacillus_subtilis')
    """
    collection = mongo_client.get_collection(Config.COLLECTIONS["gene_annotations"])

    pipeline = [
        {"$match": {"pangenome_analysis": pangenome_analysis}},
        {"$group": {"_id": "$pangenomic_class", "count": {"$sum": 1}}}
    ]
    results = list(collection.aggregate(pipeline))

    if not results:
        return f"No data found for {pangenome_analysis}"

    class_counts = {r["_id"]: r["count"] for r in results}
    labels = []
    sizes = []
    colors = []

    for cls in ['Core', 'Accessory', 'Rare']:
        if cls in class_counts:
            labels.append(cls)
            sizes.append(class_counts[cls])
            colors.append(PANGENOME_COLORS.get(cls, 'gray'))

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(
        sizes, labels=labels, colors=colors,
        autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100*sum(sizes)):,})',
        startangle=90, explode=[0.02] * len(sizes)
    )
    ax.set_title(f'Pangenome Class Distribution\n{pangenome_analysis.replace("_", " ")}', fontsize=14)

    return fig_to_image(fig)


@mcp.tool()
def plot_cog_category_distribution(pangenome_analysis: str, top_n: int = 15) -> Union[Image, str]:
    """
    Generate bar chart showing COG functional category distribution for a species.

    Args:
        pangenome_analysis: Species pangenome analysis name
        top_n: Number of top categories to show (default: 15)
    """
    collection = mongo_client.get_collection(Config.COLLECTIONS["gene_annotations"])

    pipeline = [
        {"$match": {"pangenome_analysis": pangenome_analysis}},
        {"$group": {"_id": "$cog_category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": top_n}
    ]
    results = list(collection.aggregate(pipeline))

    if not results:
        return f"No data found for {pangenome_analysis}"

    categories = [r["_id"] if r["_id"] else "-" for r in results]
    counts = [r["count"] for r in results]
    labels = [f"{cat}: {COG_NAMES.get(cat, 'Unknown')}" for cat in categories]

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.viridis([i/len(categories) for i in range(len(categories))])
    ax.barh(range(len(categories)), counts, color=colors)

    ax.set_yticks(range(len(categories)))
    ax.set_yticklabels(labels)
    ax.set_xlabel('Number of Genes', fontsize=12)
    ax.set_title(f'COG Category Distribution\n{pangenome_analysis.replace("_", " ")}', fontsize=14)
    ax.invert_yaxis()

    for i, count in enumerate(counts):
        ax.text(count + max(counts)*0.01, i, f'{count:,}', va='center', fontsize=9)

    ax.set_xlim(0, max(counts) * 1.15)
    ax.grid(True, axis='x', alpha=0.3)

    return fig_to_image(fig)


@mcp.tool()
def plot_species_comparison(family: str, top_n: int = 10) -> Union[Image, str]:
    """
    Generate stacked bar chart comparing Core/Accessory/Rare genes across species in a family.

    Args:
        family: Family name to compare species (e.g., 'Bacillaceae')
        top_n: Number of top species to show (default: 10)
    """
    collection = mongo_client.get_collection(Config.COLLECTIONS["organisms"])

    results = list(collection.find(
        {"family": {"$regex": family, "$options": "i"}},
        {"species": 1, "gene_class_distribution": 1, "genomes_num": 1}
    ).sort("genomes_num", -1).limit(top_n))

    if not results:
        return f"No species found for family: {family}"

    species_names = []
    core_counts = []
    accessory_counts = []
    rare_counts = []

    for r in results:
        species_names.append(r.get("species", "Unknown").replace("_", " "))
        dist = r.get("gene_class_distribution", [0, 0, 0])
        if isinstance(dist, list) and len(dist) >= 3:
            core_counts.append(dist[0])
            accessory_counts.append(dist[1])
            rare_counts.append(dist[2])
        else:
            core_counts.append(0)
            accessory_counts.append(0)
            rare_counts.append(0)

    fig, ax = plt.subplots(figsize=(12, 6))

    x = range(len(species_names))
    width = 0.6

    ax.bar(x, core_counts, width, label='Core', color=PANGENOME_COLORS['Core'])
    ax.bar(x, accessory_counts, width, bottom=core_counts, label='Accessory', color=PANGENOME_COLORS['Accessory'])
    ax.bar(x, rare_counts, width, bottom=[c+a for c, a in zip(core_counts, accessory_counts)],
           label='Rare', color=PANGENOME_COLORS['Rare'])

    ax.set_ylabel('Number of Genes', fontsize=12)
    ax.set_title(f'Pangenome Composition by Species\nFamily: {family}', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(species_names, rotation=45, ha='right', fontsize=10)
    ax.legend(loc='upper right')
    ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    return fig_to_image(fig)


@mcp.tool()
def plot_genome_count_by_family(family: Optional[str] = None, top_n: int = 15) -> Union[Image, str]:
    """
    Generate bar chart showing genome counts across families or species.

    Args:
        family: Optional: filter by family name to show species within
        top_n: Number of top entries to show (default: 15)
    """
    collection = mongo_client.get_collection(Config.COLLECTIONS["organisms"])

    if family:
        pipeline = [
            {"$match": {"family": {"$regex": family, "$options": "i"}}},
            {"$sort": {"genomes_num": -1}},
            {"$limit": top_n},
            {"$project": {"name": "$species", "count": "$genomes_num"}}
        ]
        title = f"Genome Count by Species\nFamily: {family}"
    else:
        pipeline = [
            {"$group": {"_id": "$family", "count": {"$sum": "$genomes_num"}}},
            {"$sort": {"count": -1}},
            {"$limit": top_n},
            {"$project": {"name": "$_id", "count": 1}}
        ]
        title = "Genome Count by Family"

    results = list(collection.aggregate(pipeline))

    if not results:
        return "No data found"

    names = [r.get("name", "Unknown").replace("_", " ") for r in results]
    counts = [r.get("count", 0) for r in results]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(range(len(names)), counts, color='steelblue')

    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel('Number of Genomes', fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.invert_yaxis()

    for i, count in enumerate(counts):
        ax.text(count + max(counts)*0.01, i, f'{count:,}', va='center', fontsize=9)

    ax.set_xlim(0, max(counts) * 1.15)
    ax.grid(True, axis='x', alpha=0.3)

    return fig_to_image(fig)


@mcp.tool()
def plot_gc_content_distribution(pangenome_analysis: str) -> Union[Image, str]:
    """
    Generate histogram of GC content distribution for genomes in a species.

    Args:
        pangenome_analysis: Species pangenome analysis name
    """
    collection = mongo_client.get_collection(Config.COLLECTIONS["genome_info"])

    results = list(collection.find(
        {"pangenome_analysis": pangenome_analysis},
        {"gc_content": 1}
    ))

    if not results:
        return f"No data found for {pangenome_analysis}"

    gc_values = [r.get("gc_content", 0) * 100 for r in results if r.get("gc_content")]

    if not gc_values:
        return f"No GC content data for {pangenome_analysis}"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(gc_values, bins=30, color='steelblue', alpha=0.7, edgecolor='white')
    mean_gc = sum(gc_values)/len(gc_values)
    ax.axvline(mean_gc, color='red', linestyle='--', label=f'Mean: {mean_gc:.2f}%')

    ax.set_xlabel('GC Content (%)', fontsize=12)
    ax.set_ylabel('Number of Genomes', fontsize=12)
    ax.set_title(f'GC Content Distribution\n{pangenome_analysis.replace("_", " ")}', fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    return fig_to_image(fig)


@mcp.tool()
def plot_geographic_distribution(pangenome_analysis: Optional[str] = None, top_n: int = 20) -> Union[Image, str]:
    """
    Generate bar chart showing geographic distribution of genomes by country.

    Args:
        pangenome_analysis: Optional: filter by species pangenome analysis name
        top_n: Number of top countries to show (default: 20)
    """
    if pangenome_analysis:
        genome_collection = mongo_client.get_collection(Config.COLLECTIONS["genome_info"])
        pipeline = [
            {"$match": {"pangenome_analysis": pangenome_analysis}},
            {
                "$lookup": {
                    "from": Config.COLLECTIONS["isolation_info"],
                    "localField": "genome_id",
                    "foreignField": "genome_id",
                    "as": "isolation"
                }
            },
            {"$unwind": {"path": "$isolation", "preserveNullAndEmptyArrays": False}},
            {"$group": {"_id": "$isolation.country_standard", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$ne": None, "$ne": "missing", "$ne": "Missing"}}},
            {"$sort": {"count": -1}},
            {"$limit": top_n}
        ]
        results = list(genome_collection.aggregate(pipeline))
    else:
        collection = mongo_client.get_collection(Config.COLLECTIONS["isolation_info"])
        pipeline = [
            {"$group": {"_id": "$country_standard", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$ne": None, "$ne": "missing", "$ne": "Missing"}}},
            {"$sort": {"count": -1}},
            {"$limit": top_n}
        ]
        results = list(collection.aggregate(pipeline))

    if not results:
        return "No geographic data found"

    countries = [r["_id"] if r["_id"] else "Unknown" for r in results]
    counts = [r["count"] for r in results]

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.Blues([0.3 + 0.7 * i / len(countries) for i in range(len(countries))])
    ax.barh(range(len(countries)), counts, color=colors)

    ax.set_yticks(range(len(countries)))
    ax.set_yticklabels(countries)
    ax.set_xlabel('Number of Genomes', fontsize=12)
    title = f'Geographic Distribution of Genomes'
    if pangenome_analysis:
        title += f'\n{pangenome_analysis.replace("_", " ")}'
    ax.set_title(title, fontsize=14)
    ax.invert_yaxis()

    for i, count in enumerate(counts):
        ax.text(count + max(counts)*0.01, i, f'{count:,}', va='center', fontsize=9)

    ax.set_xlim(0, max(counts) * 1.15)
    ax.grid(True, axis='x', alpha=0.3)

    return fig_to_image(fig)


@mcp.tool()
def plot_isolation_source_distribution(pangenome_analysis: Optional[str] = None, top_n: int = 10) -> Union[Image, str]:
    """
    Generate pie chart showing distribution of isolation sources for genomes.

    Args:
        pangenome_analysis: Optional: filter by species pangenome analysis name
        top_n: Number of top sources to show (default: 10)
    """
    if pangenome_analysis:
        genome_collection = mongo_client.get_collection(Config.COLLECTIONS["genome_info"])
        pipeline = [
            {"$match": {"pangenome_analysis": pangenome_analysis}},
            {
                "$lookup": {
                    "from": Config.COLLECTIONS["isolation_info"],
                    "localField": "genome_id",
                    "foreignField": "genome_id",
                    "as": "isolation"
                }
            },
            {"$unwind": {"path": "$isolation", "preserveNullAndEmptyArrays": False}},
            {"$group": {"_id": "$isolation.isolation_source", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$nin": [None, "Missing", "missing", "", "-", "Not available", "not available"]}}},
            {"$sort": {"count": -1}},
            {"$limit": top_n}
        ]
        results = list(genome_collection.aggregate(pipeline))
    else:
        collection = mongo_client.get_collection(Config.COLLECTIONS["isolation_info"])
        pipeline = [
            {"$group": {"_id": "$isolation_source", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$nin": [None, "Missing", "missing", "", "-", "Not available", "not available"]}}},
            {"$sort": {"count": -1}},
            {"$limit": top_n}
        ]
        results = list(collection.aggregate(pipeline))

    if not results:
        return "No isolation source data found"

    sources = [r["_id"] if r["_id"] else "Unknown" for r in results]
    counts = [r["count"] for r in results]

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.Set3(range(len(sources)))
    ax.pie(
        counts, labels=sources, colors=colors,
        autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
        startangle=90
    )

    title = 'Isolation Source Distribution'
    if pangenome_analysis:
        title += f'\n{pangenome_analysis.replace("_", " ")}'
    ax.set_title(title, fontsize=14)

    return fig_to_image(fig)


@mcp.tool()
def plot_phylogroup_distribution(pangenome_analysis: str) -> Union[Image, str]:
    """
    Generate bar chart showing phylogroup distribution for a species.

    Args:
        pangenome_analysis: Species pangenome analysis name
    """
    collection = mongo_client.get_collection(Config.COLLECTIONS["genome_info"])

    pipeline = [
        {"$match": {"pangenome_analysis": pangenome_analysis}},
        {"$group": {"_id": "$phylo_group", "count": {"$sum": 1}}},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"count": -1}}
    ]
    results = list(collection.aggregate(pipeline))

    if not results:
        return f"No phylogroup data found for {pangenome_analysis}"

    phylogroups = [r["_id"] if r["_id"] else "Unknown" for r in results]
    counts = [r["count"] for r in results]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.tab10(range(len(phylogroups)))
    ax.bar(range(len(phylogroups)), counts, color=colors)

    ax.set_xticks(range(len(phylogroups)))
    ax.set_xticklabels(phylogroups, fontsize=11)
    ax.set_xlabel('Phylogroup', fontsize=12)
    ax.set_ylabel('Number of Genomes', fontsize=12)
    ax.set_title(f'Phylogroup Distribution\n{pangenome_analysis.replace("_", " ")}', fontsize=14)
    ax.grid(True, axis='y', alpha=0.3)

    for i, count in enumerate(counts):
        ax.text(i, count + max(counts)*0.02, f'{count}', ha='center', fontsize=10)

    ax.set_ylim(0, max(counts) * 1.15)

    return fig_to_image(fig)


@mcp.tool()
def plot_pangenome_openness(family: Optional[str] = None, top_n: int = 20) -> Union[Image, str]:
    """
    Generate bar chart comparing pangenome openness (Open/Closed) across species.

    Args:
        family: Optional: filter by family name
        top_n: Number of species to show (default: 20)
    """
    collection = mongo_client.get_collection(Config.COLLECTIONS["organisms"])

    query = {}
    if family:
        query["family"] = {"$regex": family, "$options": "i"}

    results = list(collection.find(
        query,
        {"species": 1, "openness": 1, "genomes_num": 1}
    ).sort("genomes_num", -1).limit(top_n))

    if not results:
        return "No species data found"

    species_names = []
    openness_values = []
    colors = []

    openness_colors = {
        'Open': '#e74c3c',
        'Intermediate Open': '#f39c12',
        'Closed': '#2ecc71'
    }

    for r in results:
        species_names.append(r.get("species", "Unknown").replace("_", " "))
        openness = r.get("openness", "Unknown")
        openness_values.append(openness)
        colors.append(openness_colors.get(openness, 'gray'))

    fig, ax = plt.subplots(figsize=(12, 8))
    y_pos = range(len(species_names))
    ax.barh(y_pos, [1] * len(species_names), color=colors, height=0.7)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(species_names, fontsize=10)
    ax.set_xlim(0, 1.5)
    ax.set_xticks([])

    title = 'Pangenome Openness by Species'
    if family:
        title += f'\nFamily: {family}'
    ax.set_title(title, fontsize=14)
    ax.invert_yaxis()

    for i, openness in enumerate(openness_values):
        ax.text(0.5, i, openness, ha='center', va='center', fontsize=9, fontweight='bold')

    legend_elements = [
        Patch(facecolor='#2ecc71', label='Closed'),
        Patch(facecolor='#f39c12', label='Intermediate Open'),
        Patch(facecolor='#e74c3c', label='Open')
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    return fig_to_image(fig)


@mcp.tool()
def plot_phylon_heatmap(pangenome_analysis: str, max_genomes: int = 50) -> Union[Image, str]:
    """
    Generate heatmap showing phylon weights for genomes in a species.

    Args:
        pangenome_analysis: Species pangenome analysis name
        max_genomes: Maximum number of genomes to show (default: 50)
    """
    collection = mongo_client.get_collection(Config.COLLECTIONS["genome_phylons"])

    results = list(collection.find(
        {"pangenome_analysis": pangenome_analysis},
        {"genome_id": 1, "phylon_weights": 1}
    ).limit(max_genomes))

    if not results:
        return f"No phylon data found for {pangenome_analysis}"

    genome_ids = []
    weight_matrix = []
    phylon_keys = None

    for r in results:
        weights_dict = r.get("phylon_weights", {})
        if weights_dict and isinstance(weights_dict, dict):
            if phylon_keys is None:
                phylon_keys = sorted(weights_dict.keys(), key=lambda x: int(x) if x.isdigit() else x)

            weights = [weights_dict.get(k, 0) for k in phylon_keys]
            genome_ids.append(r.get("genome_id", "Unknown")[:15])
            weight_matrix.append(weights)

    if not weight_matrix:
        return f"No phylon weights found for {pangenome_analysis}"

    weight_array = np.array(weight_matrix)
    n_phylons = len(phylon_keys)

    fig, ax = plt.subplots(figsize=(max(10, n_phylons * 0.5), max(8, len(genome_ids) * 0.25)))

    im = ax.imshow(weight_array, aspect='auto', cmap='YlOrRd')

    ax.set_yticks(range(len(genome_ids)))
    ax.set_yticklabels(genome_ids, fontsize=8)
    ax.set_xticks(range(n_phylons))
    ax.set_xticklabels([f'P{k}' for k in phylon_keys], fontsize=9)
    ax.set_xlabel('Phylon', fontsize=12)
    ax.set_ylabel('Genome', fontsize=12)
    ax.set_title(f'Phylon Weight Heatmap\n{pangenome_analysis.replace("_", " ")}', fontsize=14)

    plt.colorbar(im, ax=ax, label='Weight')

    plt.tight_layout()
    return fig_to_image(fig)
