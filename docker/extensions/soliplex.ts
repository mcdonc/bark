import { Type } from "@sinclair/typebox";

export default function (pi: any) {
  pi.registerTool({
    name: "soliplex_list_rooms",
    description:
      "List available Soliplex knowledge base rooms. Returns room IDs, names, and descriptions. " +
      "Call this first to find the right room before querying with soliplex_query.",
    parameters: Type.Object({}),
    async execute(
      _toolCallId: string,
      _params: {},
      _signal: AbortSignal | undefined,
      _onUpdate: any,
      ctx: any
    ) {
      const request = JSON.stringify({ action: "soliplex_list_rooms" });
      const response = await ctx.ui.input("HOST_TOOL_REQUEST", request);
      return {
        content: [{ type: "text", text: response || "No rooms available." }],
        details: {},
      };
    },
  });

  pi.registerTool({
    name: "soliplex_query",
    description:
      "Query a Soliplex knowledge base room with a natural language question. " +
      "The room contains indexed documents searched using RAG. " +
      'Always use room_id "search" unless the user specifically asks for a different room.',
    parameters: Type.Object({
      room_id: Type.String({
        description: 'The room ID to query (default: "search")',
        default: "search",
      }),
      question: Type.String({
        description: "The natural language question to ask",
      }),
    }),
    async execute(
      _toolCallId: string,
      params: { room_id?: string; question: string },
      _signal: AbortSignal | undefined,
      _onUpdate: any,
      ctx: any
    ) {
      const roomId = params.room_id || "search";
      const request = JSON.stringify({
        action: "soliplex_query",
        room_id: roomId,
        question: params.question,
      });
      const response = await ctx.ui.input("HOST_TOOL_REQUEST", request);
      return {
        content: [
          {
            type: "text",
            text: response || "(No response from Soliplex)",
          },
        ],
        details: {},
      };
    },
  });
}
