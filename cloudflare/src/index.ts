import { Container, getContainer } from "@cloudflare/containers";

export interface Env {
  BOT_CONTAINER: DurableObjectNamespace<BotContainer>;
  API_ID: string;
  API_HASH: string;
  BOT_TOKEN: string;
}

/**
 * Durable Object wrapping the Telegram bot container.
 *
 * The bot itself (main.py) opens a long-lived connection to Telegram and
 * never listens on a port -- it is not request-driven. This class exists
 * only so Cloudflare's container runtime has something to keep alive.
 * `sleep_after` in wrangler.toml is combined with a cron ping (below) so
 * the instance is never idle long enough to be stopped.
 */
export class BotContainer extends Container<Env> {
  defaultPort = undefined; // no HTTP port -- the container is a background worker
  sleepAfter = "10m";

  envVars = {
    API_ID: this.env.API_ID,
    API_HASH: this.env.API_HASH,
    BOT_TOKEN: this.env.BOT_TOKEN,
    LOG_LEVEL: "INFO",
  };
}

async function pingContainer(env: Env): Promise<void> {
  const instance = getContainer(env.BOT_CONTAINER, "dark-tunnel-bot-singleton");
  // start() is idempotent -- it boots the container if it is not already
  // running, and is a no-op if it is.
  await instance.start();
}

export default {
  // Cron trigger: keeps the single bot container instance alive.
  async scheduled(_controller: ScheduledController, env: Env): Promise<void> {
    await pingContainer(env);
  },

  // Manual/health-check entrypoint: hitting the Worker URL also boots
  // the container, useful for verifying the deployment by hand.
  async fetch(_request: Request, env: Env): Promise<Response> {
    await pingContainer(env);
    return new Response("Dark Tunnel bot container is running.\n");
  },
};
