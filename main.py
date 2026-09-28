from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import sqlite3, datetime, hashlib

app = FastAPI()
DB = "stock.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

def get_nombre(usuario):
    conn = get_db()
    row = conn.execute("SELECT nombre FROM usuarios WHERE usuario=?", (usuario,)).fetchone()
    conn.close()
    return row["nombre"] if row else usuario

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL, descripcion TEXT DEFAULT "",
        sistema TEXT DEFAULT "", unidad TEXT DEFAULT "unidades",
        stock_actual INTEGER DEFAULT 0, stock_minimo INTEGER DEFAULT 100,
        proveedor TEXT DEFAULT "", created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nro_remito INTEGER,
        producto_id INTEGER NOT NULL, tipo TEXT NOT NULL,
        cantidad INTEGER NOT NULL,
        cliente TEXT DEFAULT "",
        proveedor TEXT DEFAULT "",
        observaciones TEXT DEFAULT "",
        firma_img TEXT DEFAULT "",
        usuario TEXT DEFAULT "",
        fecha TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL, pass_hash TEXT NOT NULL,
        nombre TEXT NOT NULL, rol TEXT DEFAULT "deposito",
        estado TEXT DEFAULT "activo",
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS remito_seq (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        ultimo INTEGER DEFAULT 0
    )""")
    c.execute("INSERT OR IGNORE INTO remito_seq (id, ultimo) VALUES (1, 0)")

    c.execute("SELECT COUNT(*) FROM productos")
    if c.fetchone()[0] == 0:
        for p in [
            ("Caja EPS APX370","APX370","unidades",0,100),
            ("Caja Interna Producto APX370","APX370","unidades",0,100),
            ("Separador Lateral APX370 48/72 hs","APX370","unidades",0,100),
            ("Separador Superior APX370 48/72 hs","APX370","unidades",0,100),
            ("Gel Icesponge 1100","APX370","unidades",0,100),
            ("Gel Icesponge 3500","APX370","unidades",0,100),
            ("Conservadoras Grandes (Caja 10)","Caja 10","unidades",0,100),
            ("Gel Refrigerante x 800 gr","Caja 10","unidades",0,100),
        ]:
            c.execute("INSERT INTO productos (nombre,sistema,unidad,stock_actual,stock_minimo) VALUES (?,?,?,?,?)", p)
    conn.commit()
    conn.close()

init_db()

def enrich(m):
    d = dict(m)
    d["usuario_nombre"] = get_nombre(d.get("usuario","")) or d.get("usuario","")
    return d

def next_remito():
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE remito_seq SET ultimo = ultimo + 1 WHERE id = 1")
    conn.commit()
    nro = c.execute("SELECT ultimo FROM remito_seq WHERE id=1").fetchone()[0]
    conn.close()
    return nro

class ProductoIn(BaseModel):
    nombre: str; descripcion: Optional[str]=""; sistema: Optional[str]=""
    unidad: Optional[str]="unidades"; stock_actual: Optional[int]=0
    stock_minimo: Optional[int]=100; proveedor: Optional[str]=""

class MovimientoIn(BaseModel):
    producto_id: int; tipo: str; cantidad: int
    cliente: Optional[str]=""
    proveedor: Optional[str]=""; observaciones: Optional[str]=""
    firma_img: Optional[str]=""; usuario: Optional[str]=""

# ---- PRODUCTOS ----
@app.get("/api/productos")
def listar_productos():
    conn=get_db(); rows=conn.execute("SELECT * FROM productos ORDER BY sistema,nombre").fetchall(); conn.close()
    return [dict(r) for r in rows]

@app.post("/api/productos")
def crear_producto(p: ProductoIn):
    conn=get_db(); c=conn.cursor()
    c.execute("INSERT INTO productos (nombre,descripcion,sistema,unidad,stock_actual,stock_minimo,proveedor) VALUES (?,?,?,?,?,?,?)",
              (p.nombre,p.descripcion,p.sistema,p.unidad,p.stock_actual,p.stock_minimo,p.proveedor))
    conn.commit(); pid=c.lastrowid; conn.close()
    return {"id":pid,"mensaje":"Creado"}

@app.delete("/api/productos/{pid}")
def eliminar_producto(pid: int):
    conn=get_db(); conn.execute("DELETE FROM productos WHERE id=?", (pid,)); conn.commit(); conn.close()
    return {"mensaje":"Eliminado"}

@app.get("/api/productos/{pid}/historial")
def historial_producto(pid: int):
    conn=get_db()
    rows=conn.execute("""SELECT m.*,p.nombre as producto_nombre,p.unidad,p.sistema
        FROM movimientos m JOIN productos p ON m.producto_id=p.id
        WHERE m.producto_id=? ORDER BY m.fecha DESC""", (pid,)).fetchall()
    conn.close(); return [enrich(r) for r in rows]

# ---- MOVIMIENTOS ----
@app.get("/api/movimientos")
def listar_movimientos(limite: int=200):
    conn=get_db()
    rows=conn.execute("""SELECT m.*,p.nombre as producto_nombre,p.unidad,p.sistema
        FROM movimientos m JOIN productos p ON m.producto_id=p.id
        ORDER BY m.fecha DESC LIMIT ?""", (limite,)).fetchall()
    conn.close(); return [enrich(r) for r in rows]

@app.get("/api/movimientos/hoy")
def movimientos_hoy():
    hoy=datetime.date.today().isoformat(); conn=get_db()
    rows=conn.execute("""SELECT m.*,p.nombre as producto_nombre,p.unidad,p.sistema
        FROM movimientos m JOIN productos p ON m.producto_id=p.id
        WHERE DATE(m.fecha)=? ORDER BY m.fecha DESC""", (hoy,)).fetchall()
    conn.close(); return [enrich(r) for r in rows]

@app.get("/api/movimientos/{mid}")
def get_movimiento(mid: int):
    conn=get_db()
    row=conn.execute("""SELECT m.*,p.nombre as producto_nombre,p.unidad,p.sistema
        FROM movimientos m JOIN productos p ON m.producto_id=p.id
        WHERE m.id=?""", (mid,)).fetchone()
    conn.close()
    if not row: raise HTTPException(404,"No encontrado")
    return enrich(row)

@app.post("/api/movimientos")
def registrar_movimiento(m: MovimientoIn):
    conn=get_db(); c=conn.cursor()
    prod=c.execute("SELECT * FROM productos WHERE id=?", (m.producto_id,)).fetchone()
    if not prod: conn.close(); raise HTTPException(404,"Producto no encontrado")
    if m.tipo=="egreso" and prod["stock_actual"]<m.cantidad:
        conn.close(); raise HTTPException(400,f"Stock insuficiente. Disponible: {prod['stock_actual']} {prod['unidad']}")
    nuevo=prod["stock_actual"]+m.cantidad if m.tipo=="ingreso" else prod["stock_actual"]-m.cantidad
    nro=next_remito() if m.tipo=="egreso" else None
    c.execute("UPDATE productos SET stock_actual=? WHERE id=?", (nuevo,m.producto_id))
    c.execute("INSERT INTO movimientos (nro_remito,producto_id,tipo,cantidad,cliente,proveedor,observaciones,firma_img,usuario) VALUES (?,?,?,?,?,?,?,?,?)",
              (nro,m.producto_id,m.tipo,m.cantidad,m.cliente,m.proveedor,m.observaciones,m.firma_img,m.usuario))
    conn.commit(); mid=c.lastrowid; conn.close()
    return {"mensaje":"Registrado","stock_nuevo":nuevo,"id":mid,"nro_remito":nro}

# ---- STATS ----
@app.get("/api/stats")
def stats():
    conn=get_db()
    total=conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    critico=conn.execute("SELECT COUNT(*) FROM productos WHERE stock_actual<=100").fetchone()[0]
    hoy=datetime.date.today().isoformat()
    mov_hoy=conn.execute("SELECT COUNT(*) FROM movimientos WHERE DATE(fecha)=?", (hoy,)).fetchone()[0]
    conn.close(); return {"total_productos":total,"stock_bajo":critico,"movimientos_hoy":mov_hoy}

# ---- TENDENCIA ----
@app.get("/api/tendencia")
def tendencia(dias: int=7):
    conn=get_db()
    productos=conn.execute("SELECT id,nombre,stock_actual FROM productos ORDER BY sistema,nombre").fetchall()
    resultado=[]
    hoy=datetime.date.today()
    for p in productos:
        puntos=[]
        for i in range(dias-1,-1,-1):
            fecha=(hoy-datetime.timedelta(days=i)).isoformat()
            # stock al final de ese dia: stock_actual + sum(egresos posteriores) - sum(ingresos posteriores)
            egresos=conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE producto_id=? AND tipo='egreso' AND DATE(fecha)>?",(p['id'],fecha)).fetchone()[0]
            ingresos=conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE producto_id=? AND tipo='ingreso' AND DATE(fecha)>?",(p['id'],fecha)).fetchone()[0]
            stock_ese_dia=p['stock_actual']+egresos-ingresos
            puntos.append({"fecha":fecha,"stock":max(0,stock_ese_dia)})
        resultado.append({"id":p['id'],"nombre":p['nombre'],"puntos":puntos})
    conn.close(); return resultado

# ---- AUTH ----
@app.post("/api/auth/login")
def login(data: dict):
    usuario=data.get("usuario",""); pass_raw=data.get("pass","")
    conn=get_db(); row=conn.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario,)).fetchone(); conn.close()
    if not row or row["pass_hash"]!=hash_pass(pass_raw): raise HTTPException(401,"Usuario o contraseña incorrectos")
    return {"rol":row["rol"],"nombre":row["nombre"],"estado":row["estado"]}

@app.post("/api/auth/registro")
def registro(data: dict):
    usuario=data.get("usuario",""); pass_raw=data.get("pass","")
    nombre=data.get("nombre",""); rol=data.get("rol","deposito")
    if not usuario or not pass_raw or not nombre: raise HTTPException(400,"Faltan datos")
    conn=get_db()
    if conn.execute("SELECT id FROM usuarios WHERE usuario=?", (usuario,)).fetchone():
        conn.close(); raise HTTPException(409,"Ese usuario ya existe. Elegí otro.")
    conn.execute("INSERT INTO usuarios (usuario,pass_hash,nombre,rol,estado) VALUES (?,?,?,?,?)",
                 (usuario,hash_pass(pass_raw),nombre,rol,"activo"))
    conn.commit(); conn.close()
    return {"mensaje":"Cuenta creada"}

@app.get("/api/usuarios")
def listar_usuarios():
    conn=get_db(); rows=conn.execute("SELECT usuario,nombre,rol,estado,created_at FROM usuarios ORDER BY created_at DESC").fetchall(); conn.close()
    return [dict(r) for r in rows]

@app.post("/api/usuarios/{usuario}/aprobar")
def aprobar_usuario(usuario: str):
    conn=get_db(); conn.execute("UPDATE usuarios SET estado='activo' WHERE usuario=?", (usuario,)); conn.commit(); conn.close()
    return {"mensaje":"Aprobado"}

@app.delete("/api/usuarios/{usuario}")
def eliminar_usuario(usuario: str):
    conn=get_db(); conn.execute("DELETE FROM usuarios WHERE usuario=?", (usuario,)); conn.commit(); conn.close()
    return {"mensaje":"Eliminado"}

app.mount("/", StaticFiles(directory="static", html=True), name="static")
