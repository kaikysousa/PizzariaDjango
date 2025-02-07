document.addEventListener("DOMContentLoaded", function () {
    let pedido = localStorage.getItem('pedido') ? JSON.parse(localStorage.getItem('pedido')) : {};
    let total = 0;
    let itemList = document.getElementById("item-list");

    for (let item in pedido) {
        let nome = pedido[item][1];
        let quantidade = pedido[item][0];
        let preco = pedido[item][2];
        total += preco;

        let itemHTML = `<li>${quantidade}x ${nome} - R$ ${preco.toFixed(2)}</li>`;
        itemList.innerHTML += itemHTML;
    }

    document.getElementById("total-pedido").textContent = total.toFixed(2);
    document.getElementById("data-hora").textContent = new Date().toLocaleString("pt-BR");
});

// Função para imprimir apenas o formulário
function imprimirNota() {
    window.print();
}
