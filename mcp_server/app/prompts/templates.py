"""
Prompts: Preset prompt templates
"""
from fastmcp import FastMCP

mcp = FastMCP(name="PromptTemplates")


@mcp.prompt
def analyze_genome(genome_id: str) -> str:
    """Standard prompt for genome analysis"""
    return f"""Please perform a comprehensive analysis of genome {genome_id}, including:

1. **Basic Information**: Length, GC content, gene count
2. **Structural Features**: Repeat sequences, gene density distribution
3. **Functional Annotation**: Main functional gene classifications
4. **Evolutionary Analysis**: Comparison with closely related species

Please use available tools to fetch data and perform the analysis."""


@mcp.prompt
def compare_genomes(genome_id_1: str, genome_id_2: str) -> str:
    """Prompt for comparing two genomes"""
    return f"""Please compare genomes {genome_id_1} and {genome_id_2}:

1. **Sequence Similarity**: Overall sequence alignment results
2. **Gene Differences**: Unique genes and shared genes
3. **Structural Variations**: Insertions, deletions, inversions, etc.
4. **Functional Differences**: Differences in metabolic pathways

Please call relevant tools to fetch data for comparative analysis."""


@mcp.prompt
def search_gene(gene_name: str, context: str = "general") -> str:
    """Prompt for searching genes"""
    return f"""Please search for gene "{gene_name}":

Research context: {context}

Please provide:
1. Basic gene information (position, length, direction)
2. Functional annotation
3. Distribution across different species
4. Related literature or database links

Use the query tool to perform the search."""


@mcp.prompt
def visualize_data(data_type: str, description: str = "") -> str:
    """Prompt for data visualization"""
    return f"""Please visualize the following data:

Data type: {data_type}
Description: {description}

Please:
1. Choose an appropriate chart type (bar chart, line chart, heatmap, etc.)
2. Use the chart tool to generate the chart
3. Explain the chart's meaning

Ensure the chart is clear and readable."""


@mcp.prompt
def explain_result(result_type: str) -> str:
    """Prompt for explaining analysis results"""
    return f"""Please explain the results of {result_type} analysis:

1. **Result Summary**: What are the main findings
2. **Biological Significance**: What do these results mean
3. **Confidence Level**: How reliable are the results
4. **Follow-up Recommendations**: What further analysis is suggested

Please explain in easy-to-understand language."""
