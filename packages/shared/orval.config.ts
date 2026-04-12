import { defineConfig } from "orval";

export default defineConfig({
  precis: {
    input: "./openapi.json",
    output: {
      target: "./src/generated/endpoints.ts",
      schemas: "./src/generated/schemas",
      client: "axios",
      mode: "tags-split",
      clean: true,
    },
  },
});
