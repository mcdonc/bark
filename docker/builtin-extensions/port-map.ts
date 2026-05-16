import { Type } from "@sinclair/typebox";

export default function (pi: any) {
  const containerStart = 8000;
  const hostStart = parseInt(process.env.BARK_PORT_START || "9000", 10);

  pi.registerTool({
    name: "get_external_port",
    description:
      "Convert a container port (8000-8004) to the external port visible to the user's browser. " +
      "Use this when you need to tell the user which URL to visit for a running web app.",
    parameters: Type.Object({
      container_port: Type.Number({
        description: "The port number inside the container (8000-8004)",
      }),
    }),
    async execute(
      _toolCallId: string,
      params: { container_port: number },
      _signal: AbortSignal | undefined,
      _onUpdate: any,
      _ctx: any
    ) {
      const port = params.container_port;
      if (port < containerStart || port >= containerStart + 5) {
        return {
          content: [
            {
              type: "text",
              text: `Port ${port} is not a mapped port. Only ports ${containerStart}-${containerStart + 4} are mapped to external ports. The external ports are ${hostStart}-${hostStart + 4}.`,
            },
          ],
          details: {},
        };
      }
      const externalPort = hostStart + (port - containerStart);
      return {
        content: [
          {
            type: "text",
            text: `Container port ${port} is mapped to external port ${externalPort}. The user can access it at http://localhost:${externalPort}`,
          },
        ],
        details: {},
      };
    },
  });
}
