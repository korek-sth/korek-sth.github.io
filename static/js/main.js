console.log("Ferreri-Work cargado");
(function(){
    const KEY = 'mi_tienda_cart';

    function safeParse(raw){
    try { const v = JSON.parse(raw); return Array.isArray(v) ? v : []; }
    catch(e){ return []; }
    }

    function guardar(cart){
    try { localStorage.setItem(KEY, JSON.stringify(cart)); }
    catch(e){ console.error('Error guardando carrito', e); }
    }

    function leer(){
    const raw = localStorage.getItem(KEY) || '[]';
    return safeParse(raw);
    }

    function actualizarContadorCarrito(){
    try {
        const cart = leer();
        const total = cart.reduce((s,i)=> s + (Number(i.qty)||0), 0);
        const badge = document.getElementById('cart-count');
        if(badge) badge.textContent = total;
    } catch(e){ console.error(e) }
    }

window.agregarCarrito = function(productId, cantidad){
    try {
        productId = Number(productId);
        cantidad = Number(cantidad) || 1;
    if (!Number.isFinite(productId)) throw new Error('ID inválido');

        const cart = leer();
        const idx = cart.findIndex(i => Number(i.id) === productId);
        if (idx >= 0) cart[idx].qty = (Number(cart[idx].qty)||0) + cantidad;
        else cart.push({ id: productId, qty: cantidad });

        guardar(cart);
        actualizarContadorCarrito();

      // feedback visual
        const msg = document.createElement('div');
        msg.textContent = 'Añadido al carrito';
        Object.assign(msg.style,{position:'fixed',right:'20px',top:'20px',background:'#10b981',color:'#fff',padding:'8px 12px',borderRadius:'8px',zIndex:9999,boxShadow:'0 6px 18px rgba(0,0,0,0.12)'});
        document.body.appendChild(msg);
        setTimeout(()=>msg.remove(),1400);

        console.info('Carrito actualizado', cart);
    } catch(err){
        console.error('agregarCarrito error', err);
        alert('No se pudo añadir al carrito.');
    }
};

  // Exponer util para depuración
    window.miTienda = { leer, guardar, actualizarContadorCarrito };

    document.addEventListener('DOMContentLoaded', actualizarContadorCarrito);
})();