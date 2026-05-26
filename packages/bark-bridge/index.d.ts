export interface BrowserFetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  headers?: Record<string, string>;
  body?: string;
}

export interface BrowserFetchResponse {
  status: number;
  headers: Record<string, string>;
  body: string;
}

export interface BrowserActionResponse {
  status: string;
}

/**
 * Fetch a URL using the user's browser session credentials.
 *
 * The request is routed through the Bark backend to the Flutter client,
 * which makes the HTTP request with the browser's cookies and session.
 *
 * Requires BARK_BRIDGE_URL and BARK_BRIDGE_TOKEN environment variables
 * (set automatically by the Bark container entrypoint).
 */
export function browserFetch(
  url: string,
  options?: BrowserFetchOptions,
): Promise<BrowserFetchResponse>;

/**
 * Trigger a browser-side action (e.g. celebrate, beep).
 *
 * Fire-and-forget actions that don't return data, just confirmation.
 */
export function browserAction(
  action: string,
  payload?: Record<string, unknown>,
): Promise<BrowserActionResponse>;

/**
 * Check whether the browser bridge is available.
 * Returns true if BARK_BRIDGE_URL and BARK_BRIDGE_TOKEN are set
 * and the bridge endpoint is reachable.
 */
export function isBridgeAvailable(): Promise<boolean>;
