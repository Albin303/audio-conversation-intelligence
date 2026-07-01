/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  optimizeFonts: false,
  env: {
    NEXT_TELEMETRY_DISABLED: '1',
  },
};

export default nextConfig;