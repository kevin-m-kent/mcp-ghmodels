## Model Context Protocol - GitHub Models Example

A weekend exploration of adapting the [Model Context Protocol getting started example](https://modelcontextprotocol.io/quickstart) with the [Azure AI Inference Library](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-inference-readme?view=azure-python-preview) and the [GitHub Models endpoints](https://github.com/marketplace/models). 

## Setup

Similar to the [Building a Client setup](https://modelcontextprotocol.io/tutorials/building-a-client), once you have initialized a uv environment, add the dependencies:

```
uv add mcp python-dotenv azure-ai-inference
```

Then set your `GITHUB_TOKEN` in your .env file, and you should be good to run it!

```
python client.py src/weather/server.py
```

You can substitute in a different `MODEL` value in [client.py](client.py) to try the example with a different model in the [catalog](https://github.com/marketplace/models/catalog). 
