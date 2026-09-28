from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, datetime

app = FastAPI()

DB = "stock.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            unidad TEXT DEFAULT 'unidades',
            stock_actual REAL DEFAULT 0,
            stock_minimo REAL DEFAULT 0,
            proveedor TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            cantidad REAL NOT NULL,
            lote TEXT,
            vencimiento TEXT,
            proveedor TEXT,
            observaciones TEXT,
            usuario TEXT,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    """)
    # Productos de ejemplo si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM productos")
    if c.fetchone()[0] == 0:
        c.executemany("""
            INSERT INTO productos (nombre, unidad, stock_actual, stock_minimo, proveedor)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("Vacuna Newcastle", "dosis", 5000, 1000, "Zoetis"),
            ("Vacuna Marek", "dosis", 3200, 800, "Zoetis"),
            ("Diluyente Standard", "litros", 45, 10, "Genérico"),
        ])
        conn.commit()
    conn.close()

init_db()

# ---------- MODELOS ----------

class ProductoIn(BaseModel):
    nombre: str
    descripcion: Optional[str] = ""
    unidad: Optional[str] = "unidades"
    stock_actual: Optional[float] = 0
    stock_minimo: Optional[float] = 0
    proveedor: Optional[str] = ""

class MovimientoIn(BaseModel):
    producto_id: int
    tipo: str  # "ingreso" o "egreso"
    cantidad: float
    lote: Optional[str] = ""
    vencimiento: Optional[str] = ""
    proveedor: Optional[str] = ""
    observaciones: Optional[str] = ""
    usuario: Optional[str] = "deposito"

# ---------- ENDPOINTS PRODUCTOS ----------

@app.get("/api/productos")
def listar_productos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/productos")
def crear_producto(p: ProductoIn):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO productos (nombre, descripcion, unidad, stock_actual, stock_minimo, proveedor)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (p.nombre, p.descripcion, p.unidad, p.stock_actual, p.stock_minimo, p.proveedor))
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return {"id": pid, "mensaje": "Producto creado"}

@app.delete("/api/productos/{pid}")
def eliminar_producto(pid: int):
    conn = get_db()
    conn.execute("DELETE FROM productos WHERE id=?", (pid,))
    conn.commit()
    conn.close()
    return {"mensaje": "Producto eliminado"}

# ---------- ENDPOINTS MOVIMIENTOS ----------

@app.get("/api/movimientos")
def listar_movimientos(limite: int = 200):
    conn = get_db()
    rows = conn.execute("""
        SELECT m.*, p.nombre as producto_nombre, p.unidad
        FROM movimientos m
        JOIN productos p ON m.producto_id = p.id
        ORDER BY m.fecha DESC
        LIMIT ?
    """, (limite,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/movimientos/hoy")
def movimientos_hoy():
    hoy = datetime.date.today().isoformat()
    conn = get_db()
    rows = conn.execute("""
        SELECT m.*, p.nombre as producto_nombre, p.unidad
        FROM movimientos m
        JOIN productos p ON m.producto_id = p.id
        WHERE DATE(m.fecha) = ?
        ORDER BY m.fecha DESC
    """, (hoy,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/movimientos")
def registrar_movimiento(m: MovimientoIn):
    conn = get_db()
    c = conn.cursor()

    # Verificar stock disponible para egresos
    producto = c.execute("SELECT * FROM productos WHERE id=?", (m.producto_id,)).fetchone()
    if not producto:
        conn.close()
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if m.tipo == "egreso" and producto["stock_actual"] < m.cantidad:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {producto['stock_actual']} {producto['unidad']}")

    # Actualizar stock
    if m.tipo == "ingreso":
        nuevo_stock = producto["stock_actual"] + m.cantidad
    else:
        nuevo_stock = producto["stock_actual"] - m.cantidad

    c.execute("UPDATE productos SET stock_actual=? WHERE id=?", (nuevo_stock, m.producto_id))
    c.execute("""
        INSERT INTO movimientos (producto_id, tipo, cantidad, lote, vencimiento, proveedor, observaciones, usuario)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (m.producto_id, m.tipo, m.cantidad, m.lote, m.vencimiento, m.proveedor, m.observaciones, m.usuario))
    conn.commit()
    conn.close()
    return {"mensaje": "Movimiento registrado", "stock_nuevo": nuevo_stock}

@app.get("/api/stats")
def stats():
    conn = get_db()
    total_productos = conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    stock_bajo = conn.execute("SELECT COUNT(*) FROM productos WHERE stock_actual <= stock_minimo").fetchone()[0]
    hoy = datetime.date.today().isoformat()
    mov_hoy = conn.execute("SELECT COUNT(*) FROM movimientos WHERE DATE(fecha)=?", (hoy,)).fetchone()[0]
    conn.close()
    return {"total_productos": total_productos, "stock_bajo": stock_bajo, "movimientos_hoy": mov_hoy}

# ---------- STATIC ----------
app.mount("/", StaticFiles(directory="static", html=True), name="static")
