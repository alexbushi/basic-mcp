## Running with Docker

### Step 1: Build the Docker image

```bash
docker build -t mcp-server .
```

### Step 2: Run the Docker container

```bash
docker run -p 8050:8050 mcp-server
```

This will start the MCP server inside a Docker container and expose it on port `8050`.

---

## Running the Client

Once the server is running, you can run the client in a separate terminal:

```bash
python client.py
```