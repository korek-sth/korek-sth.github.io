try:
    from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from datetime import datetime
    import io
except ModuleNotFoundError as e:
    import sys
    msg = (
        "Módulo 'flask' no encontrado. Instala las dependencias con:\n\n"
        "    pip install -r requirements.txt\n\n"
        "Si usas un entorno virtual asegúrate de activarlo y que VSCode/tu editor esté usando "
        "el intérprete correcto (Python)."
    )
    print(msg, file=sys.stderr)
    sys.exit(1)

import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev_secret_123")

# ==============================
# RUTAS DE ARCHIVOS JSON
# ==============================
DATA_PRODUCTOS = "data/productos.json"

# ==============================
# FUNCIONES PARA MANEJO DE JSON
# ==============================
def cargar_json(ruta):
    if not os.path.exists(ruta):
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        return []
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def guardar_json(ruta, data):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ==============================
# RUTAS PÚBLICAS
# ==============================
@app.route("/")
def index():
    productos = cargar_json(DATA_PRODUCTOS)
    return render_template("index.html", productos=productos)


@app.route("/productos")
def productos():
    productos = cargar_json(DATA_PRODUCTOS)
    return render_template("productos.html", productos=productos)


@app.route("/producto/<int:id>")
def producto_detalle(id):
    productos = cargar_json(DATA_PRODUCTOS)
    producto = next((p for p in productos if p["id"] == id), None)
    return render_template("producto_detalle.html", producto=producto)


@app.route("/cotizacion")
def cotizacion():
    productos = cargar_json(DATA_PRODUCTOS)
    return render_template("cotizacion.html", productos=productos)

@app.route("/descargar-cotizacion", methods=["POST"])
def descargar_cotizacion():
    try:
        data = request.json
        carrito = data.get("carrito", [])
        productos_dict = data.get("productos", [])
        
        if not carrito:
            return jsonify({"error": "Carrito vacío"}), 400
        
        # Construir datos para la tabla
        data_tabla = [["Producto", "Precio Unit.", "Cantidad", "Subtotal"]]
        total = 0
        
        for item in carrito:
            prod = next((p for p in productos_dict if p["id"] == item["id"]), None)
            if not prod:
                continue
            qty = item.get("qty", 1)
            subtotal = prod["precio"] * qty
            total += subtotal
            data_tabla.append([
                prod["nombre"],
                f"S/ {prod['precio']:.2f}",
                str(qty),
                f"S/ {subtotal:.2f}"
            ])
        
        # Crear PDF en memoria
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor("#df5900"),
            spaceAfter=6,
            alignment=1
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#666666"),
            spaceAfter=12,
            alignment=1
        )
        
        # Elementos del documento
        elements = []
        elements.append(Paragraph("FERRERI-WORK", title_style))
        elements.append(Paragraph("Cotización Comercial", subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Info empresa
        info_text = f"""
        <b>Empresa:</b> Ferreri-Work | <b>Teléfono:</b> +51 999 999 999 | <b>Email:</b> info@ferreri-work.com<br/>
        <b>Fecha:</b> {datetime.now().strftime("%d/%m/%Y")} | <b>Válida por:</b> 30 días
        """
        elements.append(Paragraph(info_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Tabla
        tabla = Table(data_tabla, colWidths=[2.5*inch, 1.2*inch, 0.8*inch, 1.2*inch])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d17000")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f7fb")]),
        ]))
        elements.append(tabla)
        elements.append(Spacer(1, 0.3*inch))
        
        # Total
        total_style = ParagraphStyle(
            'Total',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor("#d17000"),
            fontName='Helvetica-Bold',
            alignment=2
        )
        elements.append(Paragraph(f"<b>TOTAL: S/ {total:.2f}</b>", total_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor("#999999"),
            alignment=1
        )
        elements.append(Paragraph("Gracias por su interés. Para confirmar pedido, contáctenos.", footer_style))
        elements.append(Paragraph("© 2025 Ferreri-Work · Todos los derechos reservados", footer_style))
        
        # Construir PDF
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"cotizacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
    
    except Exception as e:
        print(f"Error generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/mas")
def mas():
    return render_template("mas.html")

# ==============================
# ADMINISTRACIÓN (login + protección)
# ==============================
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_auth"):
        return redirect(url_for("admin_index"))

    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == "75745462":
            session["admin_auth"] = True
            return redirect(url_for("admin_index"))
        return render_template("admin/login.html", error="Contraseña incorrecta")
    return render_template("admin/login.html")


@app.route("/admin/dashboard")
def admin_index():
    if not session.get("admin_auth"):
        return redirect(url_for("admin_login"))
    return render_template("admin/dashboard.html")


def _require_admin_or_redirect():
    if not session.get("admin_auth"):
        return redirect(url_for("admin_login"))
    return None


@app.route("/admin/productos")
def admin_productos():
    r = _require_admin_or_redirect()
    if r:
        return r
    productos = cargar_json(DATA_PRODUCTOS)
    return render_template("admin/productos.html", productos=productos)


@app.route("/admin/add", methods=["GET", "POST"])
def add_producto():
    r = _require_admin_or_redirect()
    if r:
        return r

    if request.method == "POST":
        productos = cargar_json(DATA_PRODUCTOS)
        
        try:
            nuevo = {
                "id": max([p["id"] for p in productos], default=0) + 1,
                "nombre": request.form.get("nombre", "").strip(),
                "marca": request.form.get("marca", "").strip(),
                "precio": float(request.form.get("precio", 0)),
                "descripcion": request.form.get("descripcion", "").strip(),
                "imagen": request.form.get("imagen", "").strip()
            }
            
            if not nuevo["nombre"] or nuevo["precio"] <= 0:
                return render_template("admin/add_producto.html", error="Datos inválidos")
            
            productos.append(nuevo)
            guardar_json(DATA_PRODUCTOS, productos)
            return redirect(url_for("admin_productos"))
        except ValueError:
            return render_template("admin/add_producto.html", error="El precio debe ser un número")

    return render_template("admin/add_producto.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_auth", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def edit_producto(id):
    r = _require_admin_or_redirect()
    if r:
        return r
    
    productos = cargar_json(DATA_PRODUCTOS)
    producto = next((p for p in productos if p["id"] == id), None)
    
    if not producto:
        return "Producto no encontrado", 404
    
    if request.method == "POST":
        try:
            producto["nombre"] = request.form.get("nombre", "").strip()
            producto["marca"] = request.form.get("marca", "").strip()
            producto["precio"] = float(request.form.get("precio", 0))
            producto["descripcion"] = request.form.get("descripcion", "").strip()
            producto["imagen"] = request.form.get("imagen", "").strip()
            
            if not producto["nombre"] or producto["precio"] <= 0:
                return render_template("admin/edit_producto.html", producto=producto, error="Datos inválidos")
            
            guardar_json(DATA_PRODUCTOS, productos)
            return redirect(url_for("admin_productos"))
        except ValueError:
            return render_template("admin/edit_producto.html", producto=producto, error="El precio debe ser un número")
    
    return render_template("admin/edit_producto.html", producto=producto)


@app.route("/admin/ventas")
def admin_ventas():
    r = _require_admin_or_redirect()
    if r:
        return r
    # Lógica para mostrar ventas (no implementada)
    return render_template("admin/ventas.html")


@app.route("/admin/eliminar/<int:id>", methods=["POST"])
def eliminar_producto(id):
    r = _require_admin_or_redirect()
    if r:
        return r
    
    productos = cargar_json(DATA_PRODUCTOS)
    productos = [p for p in productos if p["id"] != id]
    guardar_json(DATA_PRODUCTOS, productos)
    
    return jsonify({"status": "ok"}), 200

# ==============================
# RECLAMOS
# ==============================
def enviar_email_reclamo(nombre, email, telefono, tipo_reclamo, descripcion):
    try:
        # Configuración del email
        remitente = "tu_correo@gmail.com"  # Cambiar por tu email
        contraseña = "tu_contraseña_app"   # Usar contraseña de aplicación
        destinatario = "Ferreri-work@hotmail.com"
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = remitente
        msg['To'] = destinatario
        msg['Subject'] = f"Nuevo Reclamo - {tipo_reclamo}"
        
        # Cuerpo del email
        cuerpo = f"""
        <html>
          <body style="font-family: Arial, sans-serif; background: #f9f5f0; padding: 20px;">
            <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #ff8c42;">
              <h2 style="color: #ff8c42;">📋 Nuevo Reclamo Recibido</h2>
              
              <h3 style="color: #6b7280;">Datos del Cliente:</h3>
              <p><strong>Nombre:</strong> {nombre}</p>
              <p><strong>Email:</strong> {email}</p>
              <p><strong>Teléfono:</strong> {telefono if telefono else 'No proporcionado'}</p>
              
              <h3 style="color: #6b7280;">Detalles del Reclamo:</h3>
              <p><strong>Tipo:</strong> {tipo_reclamo}</p>
              <p><strong>Descripción:</strong></p>
              <p style="background: #f9f5f0; padding: 10px; border-radius: 4px;">{descripcion}</p>
              
              <hr style="border: none; border-top: 1px solid #e6e9ef; margin: 20px 0;">
              <p style="color: #999; font-size: 12px;">Este es un correo automático. Por favor, responde directamente al cliente.</p>
            </div>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(cuerpo, 'html'))
        
        # Enviar email
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remitente, contraseña)
        servidor.send_message(msg)
        servidor.quit()
        
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False


@app.route("/enviar-reclamo", methods=["POST"])
def enviar_reclamo():
    try:
        datos = request.json
        nombre = datos.get("nombre", "").strip()
        email = datos.get("email", "").strip()
        telefono = datos.get("telefono", "").strip()
        tipo_reclamo = datos.get("tipo_reclamo", "").strip()
        descripcion = datos.get("descripcion", "").strip()
        
        # Validar datos
        if not all([nombre, email, tipo_reclamo, descripcion]):
            return jsonify({"error": "Faltan datos obligatorios"}), 400
        
        # Enviar email
        if enviar_email_reclamo(nombre, email, telefono, tipo_reclamo, descripcion):
            return jsonify({"status": "ok", "mensaje": "Reclamo enviado exitosamente"}), 200
        else:
            return jsonify({"error": "Error al enviar el reclamo"}), 500
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# ==============================
# EJECUCIÓN
# ==============================
if __name__ == "__main__":
    app.run(debug=True)
