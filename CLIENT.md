# Browser-Delegated Tool Calls via Backend Bridge

## Context

Bark users sometimes operate in environments where the only authentication credentials for accessing data exist in the user's browser (cookies, OAuth tokens, session-based APIs). When Pi runs in the container, it can't access these credentials. Previously, the AG-UI RPC channel allowed Pi extensions to delegate UI requests to the browser. With the move to terminal-based Pi (interactive mode, no RPC), that channel is gone.

We need a new mechanism that lets Pi extensions inside the container ask the browser to perform actions on their behalf — specifically, making authenticated HTTP requests using the browser's session.

## Design: Backend-Mediated Bridge

Pi extensions make an HTTP POST to a bridge endpoint on the Bark backend (reachable from the container via `host.docker.internal`). The backend relays the request to the Flutter client over the existing WebSocket connection. The Flutter client executes the action (e.g., fetches a URL with browser credentials), sends the result back over the same WebSocket, and the backend returns it as the HTTP response to the Pi extension.

```text
Pi extension (container)
  │
  │ HTTP POST to host.docker.internal:<nginx_port>/api/browser-delegate
  ▼
Backend (bridge endpoint)
  │
  │ WebSocket message: {"type": "browser_request", "id": "req-1", ...}
  ▼
Flutter client (browser)
  │ executes action with browser credentials
  │
  │ WebSocket message: {"cmd": "browser_response", "id": "req-1", ...}
  ▼
Backend
  │
  │ HTTP response body
  ▼
Pi extension (gets result, returns as tool output)
```

### Key properties

- **Same WebSocket**: the browser_request/browser_response messages travel on the same WebSocket that already carries terminal I/O, heartbeats, and exec commands — just new message types
- **No new processes**: no sidecar or bridge process in the container
- **No Pi changes**: Pi extensions just make an HTTP call; Pi doesn't need a new mode
- **No escape sequences**: the terminal byte stream stays clean
- **Pi mode-agnostic**: works whether Pi runs in interactive mode (terminal) or RPC mode

## Implementation

### Phase 1: Backend bridge endpoint

**New endpoint**: `POST /api/browser-delegate`

- Receives JSON body from Pi extension: `{"action": "<action>", "workspace_id": "...", ...action-specific fields...}`
- Actions are extensible — initially `fetch`, `celebrate`, `beep`
- Generates a unique request ID
- Sends `{"type": "browser_request", "id": "<id>", "action": "<action>", ...}` to all WebSocket subscribers for that workspace
- Holds the HTTP connection open (async wait with timeout)
- When the Flutter client responds with `{"cmd": "browser_response", "id": "<id>", ...}`, returns the result as the HTTP response
- Timeout after N seconds with an error response
- Some actions return data (`fetch` returns `{status, headers, body}`), others are fire-and-forget (`celebrate`, `beep` return `{status: "ok"}`)

**File**: `src/backend/bark_backend/api.py` — new endpoint
**File**: `src/backend/bark_backend/ws_handler.py` — new `browser_response` command handler, pending request registry

### Phase 2: Flutter client handler

**WebSocket handler**: when `browser_request` message arrives, dispatch on `action`:

- `fetch`: make HTTP request using the browser's `http` client (which carries cookies/session), return `{status, headers, body}`
- `celebrate`: trigger confetti animation, return `{status: "ok"}`
- `beep`: play a sound, return `{status: "ok"}`
- Unknown action: return `{error: "unknown action"}`

Send result back: `{"cmd": "browser_response", "id": "<id>", ...result...}`

**File**: `src/frontend/lib/workspace/workspace_page.dart` or a new `browser_delegate.dart`
**File**: `src/frontend/lib/agui/agui_client.dart` — handle new `browser_request` message type in `_listenToChannel` (this file gets renamed post-AG-UI removal)

### Phase 3: `@bark/bridge` npm package

A small npm package that Pi extensions import to talk to the bridge. Reads `BARK_BRIDGE_URL` and `BARK_WORKSPACE_ID` from the environment (set by the container entrypoint). Provides:

- `browserFetch(url, options?)` — fetch a URL with the browser's session credentials
- `browserAction(action, payload?)` — trigger a browser-side action (celebrate, beep, etc.)
- `isBridgeAvailable()` — check if the bridge is reachable

Extension authors import one function and don't think about the plumbing:

```typescript
import { browserFetch, browserAction } from "@bark/bridge";

// In a tool handler:
const result = await browserFetch("https://authenticated-api.com/data");
await browserAction("celebrate");
```

**Location**: `src/bridge/` (published as `@bark/bridge`)

### Phase 4: Pi extensions

Reimplement existing client-side tools using the bridge:

**`browser_fetch`** — fetch a URL using the user's browser credentials

- LLM calls `browser_fetch(url, method, headers)`
- Extension uses `@bark/bridge` to POST to the backend bridge
- Backend relays to Flutter, Flutter makes the authenticated request, result flows back

**`celebrate`** — trigger confetti animation in the Flutter UI

- LLM calls `celebrate()`
- Extension sends `browserAction("celebrate")`
- Flutter receives `browser_request` with `action: "celebrate"`, shows confetti
- Fire-and-forget (response is just `{"status": "ok"}`)

**`beep`** — play a sound in the browser

- LLM calls `beep()`
- Extension sends `browserAction("beep")`
- Flutter plays a sound
- Fire-and-forget

**File**: `src/docker/builtin-extensions/browser-tools.ts` or individual plugin files

### Phase 5: Dart plugin system for browser actions

The Flutter app needs a plugin registry so different deployments can handle different `browser_request` actions. A Bark plugin is a normal Pi extension (npm package) that optionally includes a `bark/` directory with Flutter code.

**Dart plugin interface:**

```dart
abstract class BarkPlugin {
  /// The browser_request action this plugin handles (e.g. "celebrate", "beep", "fetch")
  String get action;

  /// Handle a browser_request and return the response payload.
  Future<Map<String, dynamic>> handle(Map<String, dynamic> request, BuildContext context);
}
```

**Plugin structure** (npm package):

```text
my-plugin/
  package.json          # Normal Pi extension package
  src/
    index.ts            # Pi extension: registers tools, uses @bark/bridge
  bark/                 # Optional — only if the plugin needs Flutter-side behavior
    pubspec.yaml
    lib/plugin.dart     # Class extending BarkPlugin
    lib/...             # Supporting Dart files (widgets, audio, etc.)
```

**Build integration:**

- `import_dart_plugins.py` (or replacement) scans plugin directories for `bark/` subdirectories
- Generates a `bark_plugins` package with `createAllPlugins()` that returns all registered `BarkPlugin` instances
- Same codegen pattern as today, but the interface is `BarkPlugin` (handles `browser_request` actions) instead of `ToolPlugin` (handles AG-UI `HOST_TOOL_REQUEST`)

**Runtime dispatch in Flutter:**

When a `browser_request` arrives over the WebSocket:

1. Look up `request.action` in the plugin registry
2. If a `BarkPlugin` is registered for that action, call `plugin.handle(request, context)`
3. Return the result as `browser_response`
4. If no plugin is registered, return `{"error": "no handler for action: <action>"}`

**Built-in plugins** (ship with Bark, no external install):

- `celebrate` — confetti animation
- `beep` — play a sound

**Example: celebrate plugin Dart side:**

```dart
class CelebratePlugin extends BarkPlugin {
  @override
  String get action => "celebrate";

  @override
  Future<Map<String, dynamic>> handle(Map<String, dynamic> request, BuildContext context) async {
    // trigger confetti overlay
    return {"status": "ok"};
  }
}
```

**Example: celebrate plugin Pi extension side:**

```typescript
import { browserAction } from "@bark/bridge";

export default function (pi) {
  pi.registerTool("celebrate", {
    description: "Celebrate with confetti in the user's browser",
    parameters: {},
    async execute(ctx, args) {
      await browserAction("celebrate");
      return "Celebration triggered!";
    },
  });
}
```

### Phase 6: Remove AG-UI chat panel

With the bridge in place for tool delegation:

- Create `with-agui` branch to preserve history
- Remove chat panel (`chat_panel.dart`, `debug_panel.dart`)
- Remove AG-UI event types and translator (`agui_events.dart`, `agui_translator.py`)
- Remove Pi RPC client (`pi_rpc_client.py`)
- Remove Pi-specific WebSocket handlers (prompt, steer, follow_up, abort, extension_ui_response)
- Remove message history endpoints and table
- Simplify `ide_layout.dart` — terminal/files take full width
- Simplify `workspace_page.dart` — remove AG-UI event handling
- Keep: terminal, exec, heartbeat, container lifecycle, file service, browser delegate

## Nginx configuration

Add `/api/browser-delegate` to the nginx proxy pass (already passes `/` to the backend, so this may just work). The Pi extension needs access from the Docker network, so the existing ACL rules in the nginx config need to allow it (same subnets as `/llm-proxy/`).

## Security considerations

- The bridge endpoint should require workspace-level authentication — the request must come from a container that belongs to a workspace the user owns
- Rate limiting to prevent abuse
- Action allowlist (initially just `fetch`) — don't allow arbitrary browser actions
- URL allowlist or domain restrictions (optional, per-workspace config)

## Verification

1. Backend unit tests for bridge endpoint (request/response flow, timeout, unknown workspace)
2. Frontend unit tests for browser_request handler
3. E2E test: create workspace, connect, trigger browser_fetch tool, verify round-trip
4. Manual test: Pi extension calls browser_fetch for an authenticated URL, browser makes the request, Pi gets the data
