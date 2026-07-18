import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "../..");

describe("Task 2: index.html CDN removal and meta tags (Req 2.1, 2.5)", () => {
  const html = readFileSync(resolve(root, "index.html"), "utf8");

  describe("No CDN references remaining", () => {
    it("has no references to unpkg.com", () => {
      expect(html).not.toContain("unpkg.com");
    });

    it("has no references to cdnjs.cloudflare.com", () => {
      expect(html).not.toContain("cdnjs.cloudflare.com");
    });

    it("has no references to fonts.googleapis.com", () => {
      expect(html).not.toContain("fonts.googleapis.com");
    });
  });

  describe("Required meta tags are present", () => {
    it("has <meta name=\"description\">", () => {
      expect(html).toContain('<meta name="description"');
    });

    it("has <meta property=\"og:title\">", () => {
      expect(html).toContain('<meta property="og:title"');
    });

    it("has <meta property=\"og:description\">", () => {
      expect(html).toContain('<meta property="og:description"');
    });

    it("has <meta property=\"og:type\">", () => {
      expect(html).toContain('<meta property="og:type"');
    });

    it("has <meta property=\"og:url\">", () => {
      expect(html).toContain('<meta property="og:url"');
    });
  });
});
