import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { viteSingleFile } from "vite-plugin-singlefile";

// Single-file build: the site must run from one self-contained HTML file so it
// works as a repo artifact, from a USB stick, and on the claude.ai artifact
// host (whose CSP blocks external requests except Google Fonts).
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: { cssCodeSplit: false, assetsInlineLimit: 100000000, target: "es2020" },
});
