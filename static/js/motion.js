(() => {
  "use strict";

  const reduzir = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const itens = [...document.querySelectorAll("[data-reveal]")];

  if (reduzir || !("IntersectionObserver" in window)) {
    itens.forEach((item) => item.classList.add("revelado"));
  } else {
    const observador = new IntersectionObserver(
      (entradas) => {
        for (const entrada of entradas) {
          if (!entrada.isIntersecting) continue;
          const indice = itens.indexOf(entrada.target);
          entrada.target.style.transitionDelay = `${Math.min(indice, 6) * 55}ms`;
          entrada.target.classList.add("revelado");
          observador.unobserve(entrada.target);
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
    );

    itens.forEach((item) => observador.observe(item));
  }

  const topo = document.querySelector(".topo");
  if (topo) {
    const atualizar = () => {
      topo.classList.toggle("topo--rolado", window.scrollY > 12);
    };
    window.addEventListener("scroll", atualizar, { passive: true });
    atualizar();
  }
})();
