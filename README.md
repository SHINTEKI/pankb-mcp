


## Architecture

![Architecture](architecture.svg)

## To-do list:

- [x] initialize codebase, use uv for env control, follow microservice structure to separate server and client apps into two directories, but track them using one repo 
- [x] write tools based on research papers, design tool categories
- [ ] transfer previous RAG to current tools
- [ ] design and write resources
- [ ] design and write prompts 
- [x] write server app using FastMCP and uvicorn (to enable hot-reload for development), mount all server-side components
- [x] write client app, initiate client instance, import openai llm, write interaction loop between user, client, server and llm
- [x] write streamlit app, create session state to display conversation history, design welcome messages to display functions and guide usage
- [x] write dockerfiles to containerize server and client, write docker-compose to orchestrate
- [x] add logs for both server and client apps
- [ ] add CI/CD workflow
- [ ] design authorization methods, user-client (third-party OAuth), server-client
- [ ] design a panel on the streamlit front page to display past conversations and available tools, resources and prompts 
- [ ] build a SQL database to store user info, token usage and past conversations 
- [ ] apply for a certificate from Let's Encrypt and use nginx for reverse proxy, connect to prod server and publish to MCP server registry
- [ ] add export function for PNG/SVG and CSV
- [ ] set up a monitoring and alerting system (Grafana)