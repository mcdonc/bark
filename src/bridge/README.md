# @bark/bridge

Browser-delegated tool calls for Bark Pi extensions.

Routes requests through the Bark backend to the user's browser, which executes them with its session credentials (cookies, OAuth tokens, etc.).

## Usage

```typescript
import { browserFetch, browserAction, isBridgeAvailable } from "@bark/bridge";

// Fetch a URL using the browser's credentials
const result = await browserFetch("https://authenticated-api.com/data");
console.log(result.status, result.body);

// Trigger a browser-side action
await browserAction("celebrate");
await browserAction("beep");

// Check if the bridge is available
if (await isBridgeAvailable()) {
  // safe to use bridge functions
}
```

## Environment Variables

Set automatically by the Bark container entrypoint:

- `BARK_BRIDGE_URL` — URL of the Bark backend (via nginx)
- `BARK_BRIDGE_TOKEN` — Opaque token that identifies this container's workspace
