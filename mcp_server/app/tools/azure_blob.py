"""
Azure Blob Storage Tools for PanKB MCP Server

These tools fetch pre-computed analysis data from Azure Blob Storage,
enabling visualizations that require complex computations or large datasets.
"""
import requests
import gzip
import json
import io
import base64
import re
from typing import Literal
from collections import Counter

from fastmcp import FastMCP
from app.config import Config

# Import matplotlib with non-interactive backend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 string"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_base64


def fetch_blob_json(species: str, filename: str) -> dict:
    """Fetch JSON data from Azure Blob Storage"""
    url = f"{Config.AZURE_BLOB_BASE_URL}species/{species}/{filename}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_blob_gzip_json(species: str, filename: str) -> dict:
    """Fetch gzipped JSON data from Azure Blob Storage"""
    url = f"{Config.AZURE_BLOB_BASE_URL}species/{species}/{filename}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    decompressed = gzip.decompress(response.content)
    return json.loads(decompressed.decode('utf-8'))


def fetch_blob_text(species: str, filename: str) -> str:
    """Fetch text data from Azure Blob Storage"""
    url = f"{Config.AZURE_BLOB_BASE_URL}species/{species}/{filename}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.text


mcp = FastMCP(name="AzureBlobTools")


@mcp.tool()
def plot_heaps_law(species: str) -> str:
    """
    Plot Heap's Law curve showing pangenome openness.
    Shows how the number of new genes discovered changes as more genomes are added.
    Open pangenomes show continuous gene discovery.

    Args:
        species: Species identifier (e.g., 'Escherichia_coli')
    """
    try:
        data = fetch_blob_json(species, "heaps_law.json")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Data not available for {species}. The species may not have pre-computed analysis data."
        return f"HTTP Error: {str(e)}"

    avg_core = data.get("avg_core", [])
    avg_acc = data.get("avg_acc", [])

    if not avg_core or not avg_acc:
        return "No Heap's law data available for this species"

    x = list(range(1, len(avg_core) + 1))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, avg_core, 'b-', linewidth=2, label='Core genes')
    ax.plot(x, avg_acc, 'r-', linewidth=2, label='Accessory genes')

    ax.set_xlabel('Number of Genomes', fontsize=12)
    ax.set_ylabel('Number of Genes', fontsize=12)
    ax.set_title(f"Heap's Law - {species.replace('_', ' ')}", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)

    img_base64 = fig_to_base64(fig)

    return (f"data:image/png;base64,{img_base64}\n\n"
            f"Heap's Law plot for {species}:\n"
            f"- Final core genes: {avg_core[-1]:.0f}\n"
            f"- Final accessory genes: {avg_acc[-1]:.0f}\n"
            f"- Number of genomes: {len(avg_core)}")


@mcp.tool()
def plot_cumulative_gene_frequency(species: str) -> str:
    """
    Plot cumulative gene frequency curve showing how genes accumulate across genomes.
    Useful for understanding pangenome saturation.

    Args:
        species: Species identifier (e.g., 'Escherichia_coli')
    """
    try:
        data = fetch_blob_json(species, "cum_freq.json")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Data not available for {species}."
        return f"HTTP Error: {str(e)}"

    # The data structure may vary, handle common formats
    if isinstance(data, dict):
        if 'x' in data and 'y' in data:
            x = data['x']
            y = data['y']
        else:
            x = list(range(len(list(data.values())[0])))
            y = list(data.values())[0]
    else:
        return "Unexpected data format"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(x, y, 'b-', linewidth=2)

    ax.set_xlabel('Gene Frequency (% of genomes)', fontsize=12)
    ax.set_ylabel('Cumulative Gene Count', fontsize=12)
    ax.set_title(f"Cumulative Gene Frequency - {species.replace('_', ' ')}", fontsize=14)
    ax.grid(True, alpha=0.3)

    img_base64 = fig_to_base64(fig)

    return f"data:image/png;base64,{img_base64}\n\nCumulative gene frequency plot for {species}"


@mcp.tool()
def plot_gene_frequency_curve(species: str) -> str:
    """
    Plot gene frequency distribution from pre-computed data.
    Shows the classic U-shaped pangenome curve with core genes on the right and rare genes on the left.

    Args:
        species: Species identifier (e.g., 'Escherichia_coli')
    """
    try:
        data = fetch_blob_json(species, "gene_freq.json")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Data not available for {species}."
        return f"HTTP Error: {str(e)}"

    frequency = data.get("frequency", [])
    x15 = data.get("x15", 0)  # 15% threshold
    x99 = data.get("x99", 0)  # 99% threshold

    if not frequency:
        return "No gene frequency data available"

    # Count occurrences of each frequency
    freq_counts = Counter(frequency)
    x_vals = sorted(freq_counts.keys())
    y_vals = [freq_counts[x] for x in x_vals]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x_vals, y_vals, width=1, color='steelblue', alpha=0.7)

    # Add threshold lines
    if x15 > 0:
        ax.axvline(x=x15, color='orange', linestyle='--', label=f'15% threshold ({x15})')
    if x99 > 0:
        ax.axvline(x=x99, color='green', linestyle='--', label=f'99% threshold ({x99})')

    ax.set_xlabel('Gene Frequency (number of genomes)', fontsize=12)
    ax.set_ylabel('Number of Genes', fontsize=12)
    ax.set_title(f"Gene Frequency Distribution - {species.replace('_', ' ')}", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    img_base64 = fig_to_base64(fig)

    # Calculate statistics
    total_genes = len(frequency)
    max_freq = max(frequency) if frequency else 0
    rare_genes = sum(1 for f in frequency if f <= x15) if x15 > 0 else 0
    core_genes = sum(1 for f in frequency if f >= x99) if x99 > 0 else 0

    return (f"data:image/png;base64,{img_base64}\n\n"
            f"Gene frequency distribution for {species}:\n"
            f"- Total genes: {total_genes:,}\n"
            f"- Max frequency: {max_freq}\n"
            f"- Rare genes (<=15%): {rare_genes:,}\n"
            f"- Core genes (>=99%): {core_genes:,}")


@mcp.tool()
def plot_cog_by_gene_class(species: str) -> str:
    """
    Plot COG functional category distribution by gene class (Core/Accessory/Rare).
    Shows which functional categories are enriched in each pangenome class.

    Args:
        species: Species identifier (e.g., 'Escherichia_coli')
    """
    try:
        data = fetch_blob_json(species, "COG_distribution.json")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Data not available for {species}."
        return f"HTTP Error: {str(e)}"

    categories = data.get("categories", [])
    core = data.get("Core", [])
    accessory = data.get("Accessory", [])
    rare = data.get("Rare", [])

    if not categories:
        return "No COG distribution data available"

    # Shorten category labels
    short_labels = [c.split(']')[0] + ']' if ']' in c else c[:20] for c in categories]

    x = np.arange(len(categories))
    width = 0.25

    fig, ax = plt.subplots(figsize=(14, 8))

    ax.bar(x - width, core, width, label='Core', color='#2ecc71')
    ax.bar(x, accessory, width, label='Accessory', color='#3498db')
    ax.bar(x + width, rare, width, label='Rare', color='#e74c3c')

    ax.set_xlabel('COG Category', fontsize=12)
    ax.set_ylabel('Number of Genes', fontsize=12)
    ax.set_title(f"COG Distribution by Gene Class - {species.replace('_', ' ')}", fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(short_labels, rotation=45, ha='right', fontsize=8)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    img_base64 = fig_to_base64(fig)

    return (f"data:image/png;base64,{img_base64}\n\n"
            f"COG distribution by gene class for {species}:\n"
            f"- Total Core: {sum(core):,}\n"
            f"- Total Accessory: {sum(accessory):,}\n"
            f"- Total Rare: {sum(rare):,}")


@mcp.tool()
def get_gene_presence_absence_matrix(species: str, gene_class: Literal["core", "accessory", "rare"]) -> str:
    """
    Get gene presence/absence matrix data for heatmap visualization.
    Returns matrix dimensions and summary statistics. The full matrix can be very large.

    Args:
        species: Species identifier (e.g., 'Escherichia_coli')
        gene_class: Gene class to retrieve: 'core', 'accessory', or 'rare'
    """
    try:
        data = fetch_blob_gzip_json(species, f"heatmap_{gene_class}.json.gz")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Data not available for {species}."
        return f"HTTP Error: {str(e)}"

    rows = data.get("rows", [])
    cols = data.get("cols", [])
    matrix = data.get("matrix", [])

    # Calculate statistics
    n_genomes = len(rows)
    n_genes = len(cols)

    # Get genome names
    genome_names = [r.get("name", "unknown") for r in rows[:5]]
    gene_names = [c.get("name", "unknown") for c in cols[:5]]

    # Calculate sparsity
    total_elements = n_genomes * n_genes
    if matrix:
        ones = sum(sum(row) for row in matrix)
        sparsity = 1 - (ones / total_elements) if total_elements > 0 else 0
    else:
        sparsity = 0

    return (f"Gene presence/absence matrix for {species} ({gene_class} genes):\n\n"
            f"Matrix dimensions:\n"
            f"- Genomes (rows): {n_genomes:,}\n"
            f"- Genes (columns): {n_genes:,}\n"
            f"- Total elements: {total_elements:,}\n"
            f"- Sparsity: {sparsity:.1%}\n\n"
            f"Sample genomes: {', '.join(genome_names)}...\n"
            f"Sample genes: {', '.join(gene_names)}...")


@mcp.tool()
def get_phylogenetic_tree(species: str) -> str:
    """
    Get phylogenetic tree in Newick format for a species.
    Can be used for tree visualization or phylogenetic analysis.

    Args:
        species: Species identifier (e.g., 'Escherichia_coli')
    """
    try:
        newick = fetch_blob_text(species, "phylogenetic_tree.newick")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Phylogenetic tree not available for {species}."
        return f"HTTP Error: {str(e)}"

    # Count tips (leaves) in the tree
    tips = re.findall(r'([A-Za-z0-9_]+):', newick)
    n_tips = len(tips)

    # Truncate if too long
    if len(newick) > 2000:
        newick_display = newick[:2000] + "... [truncated]"
    else:
        newick_display = newick

    return (f"Phylogenetic tree for {species}:\n\n"
            f"Number of tips (genomes): {n_tips}\n"
            f"Tree length: {len(newick):,} characters\n\n"
            f"Newick format:\n{newick_display}")


@mcp.tool()
def plot_dn_ds_ratio(species: str) -> str:
    """
    Plot dN/dS ratio distribution from alleleome analysis.
    Shows selection pressure across genes - values < 1 indicate purifying selection, > 1 indicates positive selection.

    Args:
        species: Species identifier (e.g., 'Escherichia_coli')
    """
    try:
        data = fetch_blob_json(species, "panalleleome/dn_ds.json")
    except requests.exceptions.HTTPError:
        return "dN/dS data not available for this species (panalleleome analysis may not be completed)"
    except Exception as e:
        return f"Error: {str(e)}"

    # Extract dN/dS values - structure may vary
    if isinstance(data, dict):
        if 'dn_ds' in data:
            values = data['dn_ds']
        elif 'values' in data:
            values = data['values']
        else:
            values = list(data.values())[0] if data else []
    elif isinstance(data, list):
        values = data
    else:
        return "Unexpected data format for dN/dS"

    if not values:
        return "No dN/dS values available"

    # Filter valid values
    values = [v for v in values if isinstance(v, (int, float)) and not np.isnan(v) and v < 10]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(values, bins=50, color='steelblue', alpha=0.7, edgecolor='black')

    ax.axvline(x=1, color='red', linestyle='--', linewidth=2, label='Neutral (dN/dS = 1)')

    ax.set_xlabel('dN/dS Ratio', fontsize=12)
    ax.set_ylabel('Number of Genes', fontsize=12)
    ax.set_title(f"dN/dS Ratio Distribution - {species.replace('_', ' ')}", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    img_base64 = fig_to_base64(fig)

    # Statistics
    mean_val = np.mean(values)
    median_val = np.median(values)
    under_purifying = sum(1 for v in values if v < 1)
    under_positive = sum(1 for v in values if v > 1)

    return (f"data:image/png;base64,{img_base64}\n\n"
            f"dN/dS ratio distribution for {species}:\n"
            f"- Total genes analyzed: {len(values):,}\n"
            f"- Mean dN/dS: {mean_val:.3f}\n"
            f"- Median dN/dS: {median_val:.3f}\n"
            f"- Under purifying selection (dN/dS < 1): {under_purifying:,}\n"
            f"- Under positive selection (dN/dS > 1): {under_positive:,}")


@mcp.tool()
def plot_variant_dominant_frequency(species: str) -> str:
    """
    Plot variant dominant frequency from panalleleome analysis.
    Shows allele frequency patterns across the pangenome.

    Args:
        species: Species identifier (e.g., 'Escherichia_coli')
    """
    try:
        data = fetch_blob_json(species, "panalleleome/step_line.json")
    except requests.exceptions.HTTPError:
        return "Variant frequency data not available for this species"
    except Exception as e:
        return f"Error: {str(e)}"

    # Extract data
    if isinstance(data, dict):
        x = data.get('x', data.get('frequency', []))
        y = data.get('y', data.get('count', []))
    else:
        return "Unexpected data format"

    if not x or not y:
        return "No variant frequency data available"

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.step(x, y, where='mid', color='steelblue', linewidth=2)

    ax.set_xlabel('Dominant Variant Frequency', fontsize=12)
    ax.set_ylabel('Number of Genes', fontsize=12)
    ax.set_title(f"Variant Dominant Frequency - {species.replace('_', ' ')}", fontsize=14)
    ax.grid(True, alpha=0.3)

    img_base64 = fig_to_base64(fig)

    return f"data:image/png;base64,{img_base64}\n\nVariant dominant frequency plot for {species}"
