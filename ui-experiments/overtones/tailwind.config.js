export default {
  content: [
    "./*.html", 
    "./js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        'deep-blue': '#0d131f',
        'navy': '#1a2332', 
        'accent-blue': '#3b82f6',
        'accent-purple': '#8b5cf6',
        'text-primary': '#ffffff',
        'text-secondary': '#94a3b8'
      },
      fontFamily: {
        'mono': ['Monaco', 'Menlo', 'Ubuntu Mono', 'monospace'],
        'sans': ['Inter', 'sans-serif']
      }
    },
  },
};