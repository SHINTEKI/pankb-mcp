"""
Streamlit Chat App with MCP Tools
"""
import os
import re
import base64
import asyncio
import streamlit as st
from mcp_client import MCPClient
from dotenv import load_dotenv

load_dotenv()


def render_content(content: str):
    """Render content, handling base64 images"""
    # Pattern to match base64 image data
    pattern = r'data:image/(png|jpeg|jpg|gif);base64,([A-Za-z0-9+/=]+)'

    parts = re.split(pattern, content)

    i = 0
    while i < len(parts):
        part = parts[i]

        # Check if this is an image format indicator (png, jpeg, etc.)
        if i + 2 < len(parts) and parts[i + 1] in ['png', 'jpeg', 'jpg', 'gif']:
            # Render any text before the image
            if part.strip():
                st.markdown(part)

            # Render the image
            img_format = parts[i + 1]
            img_data = parts[i + 2]
            try:
                st.image(base64.b64decode(img_data), use_container_width=True)
            except Exception:
                st.markdown(f"[Image decode error]")

            i += 3
        else:
            # Regular text
            if part.strip():
                st.markdown(part)
            i += 1

# Configuration (read from environment variables)
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Page configuration
st.set_page_config(
    page_title="PanKB AI Assistant",
    page_icon="🧬",
    layout="wide"
)


# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "client" not in st.session_state:
    st.session_state.client = None
    st.session_state.connected = False


async def init_client():
    """Initialize MCP Client"""
    client = MCPClient(mcp_server_url=MCP_SERVER_URL, model=MODEL)
    await client.connect()
    return client


# Main interface
st.title("🧬 PanKB AI Assistant")
# st.caption("Pangenomic data and literacture intelligent assistant based on MCP protocol")

# Connect to MCP Server (auto-reconnect)
if not st.session_state.connected:
    try:
        st.session_state.client = asyncio.run(init_client())
        st.session_state.connected = True
        st.rerun()
    except Exception as e:
        st.error(f"Failed to connect to MCP Server: {str(e)}")
        st.stop()

# Display welcome message and hints when no conversation yet
if not st.session_state.messages:
    st.markdown("I can help you explore pangenomic data. Here are the available tools:")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
**� Query Tools**
| Tool | Description |
|------|-------------|
| `query_families` | List microbial families |
| `query_species` | Search species/pangenomes |
| `query_genomes` | Find genomes by species/country |
| `query_genes` | Search genes by name/function |
| `query_pathways` | Search KEGG pathways |
| `query_stats` | Database statistics |
        """)

    with col2:
        st.markdown("""
**📈 Visualization Tools**
| Tool | Description |
|------|-------------|
| `plot_gene_frequency_histogram` | U-shaped gene frequency curve |
| `plot_pangenome_class_distribution` | Core/Accessory/Rare pie chart |
| `plot_cog_category_distribution` | COG functional categories |
| `plot_species_comparison` | Compare species in a family |
| `plot_genome_count_by_family` | Genome counts bar chart |
| `plot_gc_content_distribution` | GC content histogram |
| `plot_geographic_distribution` | Genome locations by country |
| `plot_isolation_source_distribution` | Sample sources pie chart |
| `plot_phylogroup_distribution` | Phylogroup bar chart |
| `plot_pangenome_openness` | Open/Closed pangenome status |
| `plot_heaps_law` | Pangenome growth curve |
| `plot_dn_ds_ratio` | Selection pressure distribution |
        """)

    st.markdown("---")

# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        render_content(message["content"])

# Streaming response function
async def stream_response(client, user_prompt, placeholder):
    """Get AI response via streaming"""
    full_response = ""
    async for chunk in client.chat_stream(user_prompt):
        full_response += chunk
        # During streaming, just show text (images will render after complete)
        placeholder.markdown(full_response + "▌")
    return full_response


# User input
if prompt := st.chat_input("What species are in PanKB?"):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = asyncio.run(
            stream_response(st.session_state.client, prompt, response_placeholder)
        )
        # Clear placeholder and render with images
        response_placeholder.empty()
        render_content(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Rerun to refresh page (hide welcome message, scroll to bottom)
    st.rerun()
