/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export so FastAPI can serve the UI from a single loopback origin.
  output: "export",
  reactStrictMode: true,
  images: { unoptimized: true },
  // Emit trailing-slash dirs so file paths map cleanly when served statically.
  trailingSlash: true,
};

export default nextConfig;
