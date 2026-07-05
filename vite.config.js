export default {
  // Relative base so the build works at any mount path (GitHub Pages serves
  // this site from /github-star-atlas/, not the domain root).
  base: './',
  server: {
    host: '0.0.0.0',
    allowedHosts: true,
  },
};
