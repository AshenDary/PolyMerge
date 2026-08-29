require("dotenv").config();

const Fastify = require("fastify");
const { PrismaClient } = require("@prisma/client");

const prisma = new PrismaClient();
const server = Fastify({
  logger: true,
});

const port = Number(process.env.PORT || 3000);
const mlServiceUrl = process.env.ML_SERVICE_URL || "http://localhost:8000";

server.get("/health", async () => ({
  status: "ok",
  service: "polymerge-backend",
  mlServiceUrl,
}));

server.post("/formulations/search", async (request, reply) => {
  const { diseases = [], constraints = {} } = request.body || {};

  if (!Array.isArray(diseases) || diseases.length === 0) {
    return reply.code(400).send({
      error: "At least one disease must be provided.",
    });
  }

  const queryLog = await prisma.queryLog.create({
    data: {
      query: JSON.stringify({ diseases, constraints }),
    },
  });

  return reply.code(202).send({
    queryId: queryLog.id,
    status: "accepted",
    message: "Formulation search queued for ML evaluation.",
  });
});

async function start() {
  try {
    await server.listen({ port, host: "0.0.0.0" });
  } catch (error) {
    server.log.error(error);
    process.exit(1);
  }
}

process.on("SIGINT", async () => {
  await prisma.$disconnect();
  await server.close();
  process.exit(0);
});

process.on("SIGTERM", async () => {
  await prisma.$disconnect();
  await server.close();
  process.exit(0);
});

start();
