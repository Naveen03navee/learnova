import { Container, getContainer } from "@cloudflare/containers";

// Container class that wraps the FastAPI backend Docker image
export class LearnovaBackend extends Container {
  defaultPort = 8000;
  sleepAfter = "30m";
}

// Helper: pick one of N interchangeable container instances at random
function getRandom(binding, count) {
  const id = Math.floor(Math.random() * count);
  return getContainer(binding, `instance-${id}`);
}

export default {
  async fetch(request, env) {
    // Load-balance across 3 container instances
    const container = getRandom(env.LEARNOVA_BACKEND, 3);
    return container.fetch(request);
  },
};
