import { spawn } from "child_process";
import { mkdtempSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

async function globalSetup() {
  const dataDir = mkdtempSync(join(tmpdir(), "bark-e2e-"));
  process.env.BARK_E2E_DATA_DIR = dataDir;

  const projectRoot = join(__dirname, "..", "..");
  const backendPort = process.env.BARK_E2E_PORT || "18997";
  const nginxPort = process.env.BARK_E2E_NGINX_PORT || "18995";

  // Write .env.e2e which overrides .env via dotenv.filename config
  const envPath = join(projectRoot, ".env.e2e");
  writeFileSync(
    envPath,
    [
      `BARK_PORT=${backendPort}`,
      `BARK_NGINX_PORT=${nginxPort}`,
      `BARK_DATA_DIR=${dataDir}`,
      `BARK_JWT_SECRET=e2e-test-secret`,
      `BARK_DEFAULT_USER=admin`,
      `BARK_DEFAULT_PASSWORD=admin`,
      `BARK_TEST_MODE=1`,
      `OLLAMA_API_KEY=${process.env.OLLAMA_API_KEY || ""}`,
      `OLLAMA_BASE_URL=${process.env.OLLAMA_BASE_URL || ""}`,
      `OLLAMA_MODEL=${process.env.OLLAMA_MODEL || ""}`,
    ].join("\n"),
  );

  console.log(
    `Starting E2E server on port ${backendPort} ` +
      `with BARK_DATA_DIR=${dataDir}`,
  );

  const devenvProcess = spawn("devenv", ["up", "--no-tui"], {
    cwd: projectRoot,
    stdio: ["ignore", "pipe", "pipe"],
  });

  process.env.BARK_E2E_PID = String(devenvProcess.pid);

  devenvProcess.stdout?.on("data", (data: Buffer) => {
    process.stdout.write(`[bark] ${data}`);
  });
  devenvProcess.stderr?.on("data", (data: Buffer) => {
    process.stderr.write(`[bark] ${data}`);
  });

  const baseUrl = `http://localhost:${backendPort}`;
  const maxWait = 600;
  for (let i = 0; i < maxWait; i++) {
    try {
      const resp = await fetch(`${baseUrl}/api/config`);
      if (resp.ok) {
        console.log(`E2E server ready after ${i} seconds`);
        return;
      }
    } catch {
      // Server not ready yet
    }
    await new Promise((r) => setTimeout(r, 1000));
  }

  throw new Error("E2E server failed to start within 10 minutes");
}

export default globalSetup;
