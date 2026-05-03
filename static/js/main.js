tsParticles.load("particles-js", {
  fullScreen: { enable: false },

  background: {
    color: "transparent"
  },

  particles: {
    number: {
      value: 70
    },

    color: {
      value: ["#00ffff", "#ffffff", "#ffd700"]
    },

    shape: {
      type: "circle"
    },

    opacity: {
      value: 0.5
    },

    size: {
      value: { min: 1, max: 4 }
    },

    move: {
      enable: true,
      speed: 0.8
    },

    links: {
      enable: false
    }
  }
});