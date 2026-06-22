/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: "#0B0F19",
          card: "#161E31",
          border: "#1F2B48",
          hover: "#28375C",
          text: "#E2E8F0"
        },
        primary: {
          DEFAULT: "#3B82F6",
          hover: "#2563EB"
        },
        accent: {
          success: "#10B981",
          danger: "#EF4444",
          warning: "#F59E0B"
        }
      }
    },
  },
  plugins: [],
}
