(() => {
  "use strict";

  const CHAVE = "carrinho:v2";
  const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

  const elementos = {
    drawer: document.getElementById("carrinho"),
    itens: document.getElementById("carrinho-itens"),
    vazio: document.getElementById("carrinho-vazio"),
    total: document.getElementById("carrinho-total"),
    contador: document.querySelector("[data-carrinho-contador]"),
    json: document.getElementById("carrinho-json"),
    form: document.getElementById("form-revisar"),
    aviso: document.getElementById("meia-aviso"),
    avisoTexto: document.getElementById("meia-texto"),
    toast: document.getElementById("toast"),
  };

  let meia = null;
  let toastTimer = null;

  const salvar = (carrinho) => {
    try {
      localStorage.setItem(CHAVE, JSON.stringify(carrinho));
    } catch (erro) {
      /* modo privado pode bloquear o armazenamento */
    }
  };

  const ler = () => {
    try {
      const bruto = JSON.parse(localStorage.getItem(CHAVE)) || {};
      const carrinho = {};
      let descartou = false;
      for (const [chave, item] of Object.entries(bruto)) {
        const preco = Number(item?.preco);
        const quantidade = Number(item?.quantidade);
        if (
          !Array.isArray(item?.ids) ||
          !Number.isFinite(preco) ||
          !Number.isInteger(quantidade) ||
          quantidade < 1
        ) {
          descartou = true;
          continue;
        }
        carrinho[chave] = { ...item, preco, quantidade };
      }
      if (descartou) salvar(carrinho);
      return carrinho;
    } catch (erro) {
      return {};
    }
  };

  const chaveDe = (ids) => [...ids].sort((a, b) => a - b).join("-");

  const totalDoCarrinho = (carrinho) =>
    Object.values(carrinho).reduce(
      (soma, item) => soma + Number(item.preco) * item.quantidade,
      0,
    );

  const quantidadeTotal = (carrinho) =>
    Object.values(carrinho).reduce((soma, item) => soma + item.quantidade, 0);

  const toast = (mensagem) => {
    if (!elementos.toast) return;
    elementos.toast.textContent = mensagem;
    elementos.toast.classList.add("toast--visivel");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(
      () => elementos.toast.classList.remove("toast--visivel"),
      2600,
    );
  };

  const pulsarContador = () => {
    if (!elementos.contador) return;
    elementos.contador.classList.remove("contador--pulso");
    void elementos.contador.offsetWidth;
    elementos.contador.classList.add("contador--pulso");
  };

  const atualizarContador = (carrinho = ler()) => {
    const quantidade = quantidadeTotal(carrinho);
    if (!elementos.contador) return;
    elementos.contador.textContent = String(quantidade);
    elementos.contador.hidden = quantidade === 0;
  };

  const criarBotao = (texto, acao, chave, rotulo) => {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.textContent = texto;
    botao.dataset.acao = acao;
    botao.dataset.chave = chave;
    if (rotulo) botao.setAttribute("aria-label", rotulo);
    return botao;
  };

  const render = () => {
    const carrinho = ler();
    atualizarContador(carrinho);

    if (!elementos.itens) return;

    const entradas = Object.entries(carrinho);

    elementos.itens.replaceChildren();

    if (entradas.length === 0) {
      elementos.vazio.hidden = false;
      elementos.itens.hidden = true;
    } else {
      elementos.vazio.hidden = true;
      elementos.itens.hidden = false;

      for (const [chave, item] of entradas) {
        const li = document.createElement("li");

        const dados = document.createElement("span");
        dados.className = "item__nome";
        dados.textContent = item.nome;

        const preco = document.createElement("span");
        preco.className = "item__preco";
        preco.textContent = moeda.format(Number(item.preco) * item.quantidade);

        const quantidade = document.createElement("span");
        quantidade.className = "qtd";
        quantidade.append(
          criarBotao("−", "menos", chave, `Diminuir ${item.nome}`),
        );
        const numero = document.createElement("span");
        numero.textContent = String(item.quantidade);
        numero.setAttribute("aria-live", "polite");
        quantidade.append(numero, criarBotao("+", "mais", chave, `Aumentar ${item.nome}`));

        const remover = document.createElement("button");
        remover.type = "button";
        remover.className = "remover";
        remover.textContent = "Remover";
        remover.dataset.acao = "remover";
        remover.dataset.chave = chave;
        remover.setAttribute("aria-label", `Remover ${item.nome}`);

        li.append(dados, preco, quantidade, remover);
        elementos.itens.append(li);
      }
    }

    if (elementos.total) {
      elementos.total.textContent = moeda.format(totalDoCarrinho(carrinho));
    }

    if (elementos.json) {
      elementos.json.value = JSON.stringify({
        itens: entradas.map(([, item]) => ({
          ids: item.ids,
          quantidade: item.quantidade,
        })),
      });
    }
  };

  const adicionar = (ids, nome, preco) => {
    const carrinho = ler();
    const chave = chaveDe(ids);
    const existente = carrinho[chave];

    if (existente) {
      existente.quantidade += 1;
    } else {
      carrinho[chave] = {
        ids,
        nome,
        preco: Number(preco),
        quantidade: 1,
      };
    }

    salvar(carrinho);
    render();
    pulsarContador();
    toast(`${nome} adicionado ao pedido.`);
  };

  const alterarQuantidade = (chave, delta) => {
    const carrinho = ler();
    const item = carrinho[chave];
    if (!item) return;

    item.quantidade += delta;
    if (item.quantidade <= 0) {
      delete carrinho[chave];
    }
    salvar(carrinho);
    render();
  };

  const remover = (chave) => {
    const carrinho = ler();
    const item = carrinho[chave];
    delete carrinho[chave];
    salvar(carrinho);
    render();
    if (item) toast(`${item.nome} removido.`);
  };

  const cancelarMeia = () => {
    meia = null;
    document.querySelectorAll(".js-meia.selecionado").forEach((botao) => {
      botao.classList.remove("selecionado");
      botao.textContent = "Meia";
    });
    if (elementos.aviso) elementos.aviso.hidden = true;
  };

  const escolherMeia = (botao) => {
    const id = Number(botao.dataset.id);
    const nome = botao.dataset.nome;
    const preco = Number(botao.dataset.preco);

    if (!meia) {
      meia = { id, nome, preco };
      botao.classList.add("selecionado");
      botao.textContent = "Metade escolhida";
      if (elementos.aviso && elementos.avisoTexto) {
        elementos.aviso.hidden = false;
        elementos.avisoTexto.textContent = `Metade escolhida: ${nome}. Escolha a segunda metade.`;
      }
      return;
    }

    if (meia.id === id) {
      cancelarMeia();
      return;
    }

    adicionar(
      [meia.id, id],
      `${meia.nome} / ${nome}`,
      (meia.preco + preco) / 2,
    );
    cancelarMeia();
  };

  let ultimoFoco = null;

  const abrirCarrinho = () => {
    if (!elementos.drawer) return;
    ultimoFoco = document.activeElement;
    if (typeof elementos.drawer.showModal === "function") {
      elementos.drawer.showModal();
    } else {
      elementos.drawer.setAttribute("open", "");
    }
    window.requestAnimationFrame(() => {
      elementos.drawer.classList.add("carrinho--aberto");
    });
    const fechar = elementos.drawer.querySelector("[data-fechar-carrinho]");
    if (fechar) fechar.focus();
  };

  const fecharCarrinho = () => {
    if (!elementos.drawer) return;
    elementos.drawer.classList.remove("carrinho--aberto");
    window.setTimeout(() => {
      if (elementos.drawer.open) elementos.drawer.close();
      if (ultimoFoco && typeof ultimoFoco.focus === "function") ultimoFoco.focus();
    }, 220);
  };

  document.addEventListener("click", (evento) => {
    const adicionarBtn = evento.target.closest(".js-adicionar");
    if (adicionarBtn) {
      adicionar(
        [Number(adicionarBtn.dataset.id)],
        adicionarBtn.dataset.nome,
        adicionarBtn.dataset.preco,
      );
      return;
    }

    const meiaBtn = evento.target.closest(".js-meia");
    if (meiaBtn) {
      escolherMeia(meiaBtn);
      return;
    }

    const acao = evento.target.closest("[data-acao]");
    if (acao) {
      const chave = acao.dataset.chave;
      if (acao.dataset.acao === "mais") alterarQuantidade(chave, 1);
      if (acao.dataset.acao === "menos") alterarQuantidade(chave, -1);
      if (acao.dataset.acao === "remover") remover(chave);
      return;
    }

    if (evento.target.closest("[data-fechar-carrinho]")) {
      fecharCarrinho();
      return;
    }

    if (evento.target.closest("[data-abrir-carrinho]") && elementos.drawer) {
      evento.preventDefault();
      abrirCarrinho();
      return;
    }

    if (evento.target.closest("[data-cancelar-meia]")) {
      cancelarMeia();
    }
  });

  if (elementos.drawer) {
    elementos.drawer.addEventListener("cancel", (evento) => {
      evento.preventDefault();
      fecharCarrinho();
    });
    elementos.drawer.addEventListener("click", (evento) => {
      if (evento.target === elementos.drawer) fecharCarrinho();
    });
  }

  if (elementos.form) {
    elementos.form.addEventListener("submit", (evento) => {
      if (Object.keys(ler()).length === 0) {
        evento.preventDefault();
        toast("Seu carrinho está vazio.");
      }
    });
  }

  render();
})();
