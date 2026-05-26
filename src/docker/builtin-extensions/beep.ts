const BRIDGE_URL = process.env.BARK_BRIDGE_URL;
const BRIDGE_TOKEN = process.env.BARK_BRIDGE_TOKEN;

export default function (pi: any) {
  if (!BRIDGE_URL || !BRIDGE_TOKEN) return;

  pi.registerTool({
    name: "beep",
    description:
      "Play a beep sound in the user's browser. " +
      "Use this to get the user's attention or signal completion.",
    parameters: {},
    async execute(
      _toolCallId: string,
      _params: Record<string, never>,
      _signal: AbortSignal | undefined,
      _onUpdate: any,
      _ctx: any,
    ) {
      try {
        const resp = await fetch(`${BRIDGE_URL}/api/browser-delegate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "beep",
            token: BRIDGE_TOKEN,
          }),
        });

        if (!resp.ok) {
          return {
            content: [
              {
                type: "text",
                text: "Could not play beep — no browser connected.",
              },
            ],
            details: {},
          };
        }

        return {
          content: [{ type: "text", text: "Beep played." }],
          details: {},
        };
      } catch {
        return {
          content: [{ type: "text", text: "Could not reach browser bridge." }],
          details: {},
        };
      }
    },
  });
}
