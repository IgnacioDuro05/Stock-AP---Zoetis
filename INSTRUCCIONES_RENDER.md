# 📦 StockApp — Guía de Despliegue en Render.com

## ¿Qué contiene este paquete?

```
stockapp/
├── main.py              ← Backend (FastAPI + SQLite)
├── requirements.txt     ← Dependencias de Python
├── render.yaml          ← Config automática de Render
├── .gitignore
└── static/
    └── index.html       ← Frontend completo
```

---

## 🚀 Pasos para publicarlo en Render.com (GRATIS)

### Paso 1 — Crear cuenta en GitHub
Si no tenés cuenta: https://github.com → "Sign up" (es gratis)

### Paso 2 — Subir el proyecto a GitHub
1. Entrá a https://github.com/new
2. Nombre del repositorio: `stockapp-deposito`
3. Hacé clic en **"Create repository"**
4. En la página siguiente, hacé clic en **"uploading an existing file"**
5. **Descomprimí el ZIP** que descargaste
6. Subí **todos los archivos** manteniendo la estructura de carpetas:
   - `main.py`
   - `requirements.txt`
   - `render.yaml`
   - `.gitignore`
   - `static/index.html`
7. Hacé clic en **"Commit changes"**

### Paso 3 — Crear cuenta en Render.com
1. Entrá a https://render.com
2. Hacé clic en **"Get Started for Free"**
3. Registrate con tu cuenta de GitHub (recomendado)

### Paso 4 — Crear el servicio web
1. En el dashboard de Render, hacé clic en **"New +"** → **"Web Service"**
2. Conectá tu repositorio de GitHub (`stockapp-deposito`)
3. Render va a detectar automáticamente el `render.yaml` y autocompletar todo
4. Verificá que esté configurado así:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Hacé clic en **"Create Web Service"**

### Paso 5 — ¡Listo! 🎉
Render va a construir y publicar la app en aproximadamente 2-3 minutos.  
Te va a dar una URL del tipo:  
**`https://stockapp-deposito.onrender.com`**

Esa URL la compartís con los chicos del depósito y ya pueden usarla desde el navegador.

---

## 👤 Usuarios del sistema

| Perfil | Acceso |
|---|---|
| **Administrador** | Dashboard + Movimientos + Productos + Historial + Exportar CSV |
| **Depósito** | Dashboard + Movimientos + Historial |

> ⚠️ Por ahora no hay contraseña — cualquiera puede elegir el perfil.  
> Si necesitás agregar contraseñas reales, avisame y lo agrego.

---

## ⚠️ Nota importante sobre Render (plan gratis)

El plan gratuito de Render tiene una limitación:  
> Si la app no recibe visitas por **15 minutos**, se "duerme" y la primera visita tarda ~30 segundos en cargar.

**Solución:** Usá https://uptimerobot.com (gratis) para hacer un ping cada 10 minutos y mantenerla despierta.

---

## 🛠️ ¿Querés actualizar el sistema en el futuro?

Solo modificá los archivos en GitHub y Render re-deployea automáticamente.

---

*Generado por ZenAI*
