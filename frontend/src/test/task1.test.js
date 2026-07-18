import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "../..");

describe("Task 1: Dependency installation and tooling setup", () => {
  const pkg = JSON.parse(readFileSync(resolve(root, "package.json"), "utf8"));

  describe("Required runtime dependencies (Req 1.1)", () => {
    it("has react-router-dom in dependencies", () => {
      expect(pkg.dependencies).toHaveProperty("react-router-dom");
    });

    it("has react-leaflet in dependencies", () => {
      expect(pkg.dependencies).toHaveProperty("react-leaflet");
    });

    it("has leaflet in dependencies", () => {
      expect(pkg.dependencies).toHaveProperty("leaflet");
    });

    it("has lucide-react in dependencies", () => {
      expect(pkg.dependencies).toHaveProperty("lucide-react");
    });

    it("has @fontsource/inter in dependencies", () => {
      expect(pkg.dependencies).toHaveProperty("@fontsource/inter");
    });

    it("has @fontsource/jetbrains-mono in dependencies", () => {
      expect(pkg.dependencies).toHaveProperty("@fontsource/jetbrains-mono");
    });
  });

  describe("Required dev dependencies (Req 1.2)", () => {
    it("has vitest in devDependencies", () => {
      expect(pkg.devDependencies).toHaveProperty("vitest");
    });

    it("has @testing-library/react in devDependencies", () => {
      expect(pkg.devDependencies).toHaveProperty("@testing-library/react");
    });

    it("has @testing-library/jest-dom in devDependencies", () => {
      expect(pkg.devDependencies).toHaveProperty("@testing-library/jest-dom");
    });

    it("has @fast-check/vitest in devDependencies", () => {
      expect(pkg.devDependencies).toHaveProperty("@fast-check/vitest");
    });
  });

  describe(".env.example file (Req 1.6)", () => {
    it(".env.example exists", () => {
      expect(existsSync(resolve(root, ".env.example"))).toBe(true);
    });

    it(".env.example contains VITE_API_URL", () => {
      const content = readFileSync(resolve(root, ".env.example"), "utf8");
      expect(content).toContain("VITE_API_URL");
    });
  });
});
