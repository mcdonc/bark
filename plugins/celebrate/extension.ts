const BRIDGE_URL = process.env.BARK_BRIDGE_URL;
const BRIDGE_TOKEN = process.env.BARK_BRIDGE_TOKEN;

const CONFETTI_CHARS = [
  "\x1b[91m*\x1b[0m",
  "\x1b[93m*\x1b[0m",
  "\x1b[92m*\x1b[0m",
  "\x1b[96m*\x1b[0m",
  "\x1b[95m*\x1b[0m",
  "\x1b[94m.\x1b[0m",
  "\x1b[91m'\x1b[0m",
  "\x1b[93m,\x1b[0m",
  "\x1b[92mo\x1b[0m",
];

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

async function ansiConfetti(): Promise<void> {
  const cols = parseInt(process.env.COLUMNS || "80", 10);
  const rows = parseInt(process.env.LINES || "24", 10);
  const particles: { x: number; y: number; ch: string; dy: number }[] = [];

  for (let i = 0; i < 40; i++) {
    particles.push({
      x: Math.floor(Math.random() * cols),
      y: 0,
      ch: CONFETTI_CHARS[Math.floor(Math.random() * CONFETTI_CHARS.length)],
      dy: 0.3 + Math.random() * 0.7,
    });
  }

  // Save cursor, hide it
  process.stdout.write("\x1b[s\x1b[?25l");

  for (let frame = 0; frame < 30; frame++) {
    // Clear previous positions
    for (const p of particles) {
      const row = Math.floor(p.y);
      if (row >= 1 && row <= rows) {
        process.stdout.write(`\x1b[${row};${p.x + 1}H `);
      }
    }

    // Update positions
    for (const p of particles) {
      p.y += p.dy;
      p.x += Math.random() < 0.5 ? -1 : 1;
      p.x = Math.max(0, Math.min(cols - 1, p.x));
    }

    // Draw new positions
    for (const p of particles) {
      const row = Math.floor(p.y);
      if (row >= 1 && row <= rows) {
        process.stdout.write(`\x1b[${row};${p.x + 1}H${p.ch}`);
      }
    }

    await sleep(80);
  }

  // Clear all particles
  for (const p of particles) {
    const row = Math.floor(p.y);
    if (row >= 1 && row <= rows) {
      process.stdout.write(`\x1b[${row};${p.x + 1}H `);
    }
  }

  // Restore cursor, show it
  process.stdout.write("\x1b[u\x1b[?25h");
}

export default function (pi: any) {
  if (!BRIDGE_URL || !BRIDGE_TOKEN) return;

  pi.registerTool({
    name: "celebrate",
    description:
      "Celebrate with a confetti animation. " +
      "Use this when the user has accomplished something or asks you to celebrate.",
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
            action: "celebrate",
            token: BRIDGE_TOKEN,
          }),
        });

        if (resp.ok) {
          return {
            content: [{ type: "text", text: "Celebration triggered!" }],
            details: {},
          };
        }
      } catch {
        // Bridge unreachable — fall through to ANSI
      }

      // No browser connected or bridge failed — ANSI fallback
      try {
        await ansiConfetti();
        return {
          content: [{ type: "text", text: "Celebration triggered!" }],
          details: {},
        };
      } catch {
        return {
          content: [{ type: "text", text: "Could not trigger celebration." }],
          details: {},
        };
      }
    },
  });
}
