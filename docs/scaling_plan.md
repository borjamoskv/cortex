# CORTEX Scaling Plan — De Local a SaaS

> Fecha: 2026-02-19
> Autor: Borja Moskv + MOSKV-1
> Estado: Draft v1.0

---

## Inventario: Lo que YA tienes

| Componente | Estado | Notas |
|---|---|---|
| REST API (FastAPI) | ✅ Producción | 12+ routers, CORS, rate limiting |
| Auth (API keys + SHA-256) | ✅ Producción | `auth.py` — tenant_id, permissions, revoke |
| Multi-tenant schema | ✅ Parcial | `tenant_id` en api_keys, pero sin row-level isolation en facts |
| Rate limiting | ✅ Producción | Sliding window, in-memory, configurable |
| Vector search | ✅ Producción | sqlite-vec, 384-dim embeddings |
| Hash-chain ledger | ✅ Producción | SHA-256, append-only |
| Consensus (RWC) | ✅ Producción | Reputation-weighted, agents, trust edges |
| MCP server | ✅ Producción | 4 tools: store, search, recall, status |
| Federation | ✅ Básico | `federation.py`, shard_dir |
| Connection pool | ✅ Producción | `connection_pool.py` |
| Landing page (Vercel) | ✅ Desplegada | cortex landing |
| Config env-based | ✅ Producción | Todos los settings via `os.environ` |

**Conclusión: ~70% del trabajo de backend está hecho.**

---

## Fase 1: Multi-Tenant Real (2-3 días)

### Problema actual
`facts`, `transactions`, `heartbeats` no filtran por tenant. Un API key da acceso a TODO.

### Solución: Row-Level Isolation

```python
# Antes (inseguro):
SELECT * FROM facts WHERE project = ?

# Después (multi-tenant):
SELECT * FROM facts WHERE project = ? AND tenant_id = ?
```

### Tareas

- [ ] **1.1** Añadir columna `tenant_id TEXT NOT NULL DEFAULT 'default'` a:
  - `facts`
  - `transactions`
  - `heartbeats`
  - `time_entries`
  - `consensus_votes` / `consensus_votes_v2`
  - `ghosts`
  - `compaction_log`

- [ ] **1.2** Crear migración SQL:
  ```sql
  ALTER TABLE facts ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default';
  CREATE INDEX idx_facts_tenant ON facts(tenant_id);
  -- Repetir para cada tabla
  ```

- [ ] **1.3** Inyectar `tenant_id` desde `AuthResult` en TODOS los queries:
  - `AsyncCortexEngine.store()` → incluir tenant
  - `AsyncCortexEngine.recall()` → filtrar por tenant
  - `AsyncCortexEngine.search()` → filtrar por tenant
  - Todas las rutas de admin

- [ ] **1.4** Middleware de tenant isolation:
  ```python
  async def inject_tenant(request: Request):
      auth = request.state.auth  # from require_auth
      request.state.tenant_id = auth.tenant_id
  ```

- [ ] **1.5** Tests:
  - Tenant A no puede leer facts de Tenant B
  - Tenant A no puede votar en facts de Tenant B
  - Admin puede ver todos los tenants

**Esfuerzo: ~16h**

---

## Fase 2: Database Backend Pluggable (3-5 días)

### Opción A: Turso (SQLite en la nube) ⭐ RECOMENDADA

```
Tu SQLite actual → libsql (Turso) → Edge-compatible
```

- **Ventaja:** Misma sintaxis SQL, mínimos cambios de código
- **Ventaja:** Edge replicas (baja latencia global)
- **Ventaja:** Free tier generoso (500 DBs, 9GB storage)
- **Precio:** $29/mo Pro (ilimitado)

```python
# config.py — solo cambiar la conexión
import libsql_experimental as libsql

# Local mode (actual)
CORTEX_DB = "file:~/.cortex/cortex.db"

# Cloud mode (Turso)  
CORTEX_DB = os.environ.get(
    "CORTEX_DB", 
    "libsql://cortex-borjamoskv.turso.io"
)
CORTEX_DB_TOKEN = os.environ.get("CORTEX_DB_TOKEN", "")
```

### Opción B: PostgreSQL + pgvector

- **Ventaja:** Escalabilidad infinita, ecosistema maduro
- **Desventaja:** Reescribir queries SQL (diferencias de sintaxis)
- **Desventaja:** Hosting más caro ($15-50/mo mínimo)
- **Cuándo:** Si superas 100K+ facts por tenant

### Tareas (Turso)

- [ ] **2.1** Instalar `pip install libsql-experimental`
- [ ] **2.2** Crear `cortex/storage/backend.py` — interfaz abstracta:
  ```python
  class StorageBackend(Protocol):
      async def execute(self, sql: str, params: tuple) -> list[Row]: ...
      async def executemany(self, sql: str, params: list[tuple]): ...
      async def transaction(self) -> AsyncContextManager: ...
  ```
- [ ] **2.3** Implementar `SQLiteBackend` (actual) y `TursoBackend`
- [ ] **2.4** Modificar `AsyncCortexEngine.__init__` para aceptar backend
- [ ] **2.5** Migrar sqlite-vec → Turso vector extension (o API externa para embeddings)

**Esfuerzo: ~24-40h**

---

## Fase 3: API Pública + Billing (3-5 días)

### Endpoints públicos

```
POST   /v1/store        → Guardar fact (autenticado)
GET    /v1/search?q=    → Buscar (autenticado)
GET    /v1/recall/:proj → Recall proyecto (autenticado)
GET    /v1/status       → Health check (público)
POST   /v1/keys         → Crear API key (admin)
DELETE /v1/keys/:id     → Revocar key (admin)
```

**Nota:** Tus rutas actuales ya cubren casi todo esto. Solo necesitas versionarlas (`/v1/`) y documentarlas con OpenAPI.

### Billing (Stripe)

```python
# cortex/billing.py
TIERS = {
    "free": {
        "price": 0,
        "max_facts": 1_000,
        "max_projects": 1,
        "max_searches_day": 100,
        "embeddings": "basic",    # ONNX local
    },
    "pro": {
        "price": 9_00,  # $9/mo en centavos
        "max_facts": 100_000,
        "max_projects": 20,
        "max_searches_day": 10_000,
        "embeddings": "advanced",  # Gemini API
        "features": ["consensus", "hybrid_search", "export"],
    },
    "team": {
        "price": 29_00,  # $29/mo
        "max_facts": 1_000_000,
        "max_projects": -1,  # ilimitado
        "max_searches_day": -1,
        "embeddings": "advanced",
        "features": ["consensus", "hybrid_search", "export", 
                     "multi_agent", "dashboard", "audit_trail"],
    },
}
```

### Tareas

- [ ] **3.1** Instalar `pip install stripe`
- [ ] **3.2** Crear `cortex/billing.py` con tier enforcement
- [ ] **3.3** Tabla `subscriptions` vinculada a `tenant_id`
- [ ] **3.4** Middleware de quota check (facts count, search count)
- [ ] **3.5** Webhook Stripe para activar/desactivar tiers
- [ ] **3.6** Página de pricing en landing (Vercel)

**Esfuerzo: ~24-40h**

---

## Fase 4: Deployment Producción (2-3 días)

### Arquitectura target

```
                    ┌──────────────────────────┐
                    │     Vercel (Landing)      │
                    │   cortex.borjamoskv.com   │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │     API Gateway           │
                    │   (Fly.io / Railway)      │
                    │   FastAPI + Uvicorn       │
                    │   SSL + Rate Limit        │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
    ┌─────────▼────────┐ ┌──────▼──────┐  ┌────────▼────────┐
    │  Turso (Primary)  │ │  Stripe     │  │  ONNX / Gemini  │
    │  SQLite Cloud     │ │  Billing    │  │  Embeddings     │
    │  Edge Replicas    │ │  Webhooks   │  │  API            │
    └──────────────────┘ └─────────────┘  └─────────────────┘
```

### Opciones de hosting para la API

| Plataforma | Free tier | Pro | Deploy |
|---|---|---|---|
| **Fly.io** | 3 shared VMs | $5/mo per VM | `fly deploy` |
| **Railway** | $5 crédito/mo | $5/mo + uso | Git push |
| **Render** | 750h/mo | $7/mo | Git push |
| **VPS (Hetzner)** | — | €4.5/mo (4GB) | Docker |

### Tareas

- [ ] **4.1** Crear `Dockerfile`:
  ```dockerfile
  FROM python:3.12-slim
  WORKDIR /app
  COPY . .
  RUN pip install -e ".[all]"
  CMD ["uvicorn", "cortex.api:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- [ ] **4.2** GitHub Actions CI/CD (tests + deploy)
- [ ] **4.3** Variables de entorno en producción
- [ ] **4.4** Dominio + SSL (`api.cortex.borjamoskv.com`)
- [ ] **4.5** Monitoring (uptimebot o similar)

**Esfuerzo: ~16h**

---

## Timeline Total

| Fase | Esfuerzo | Prioridad | Dependencia |
|---|---|---|---|
| **1. Multi-tenant** | 2-3 días | 🔴 P0 | Ninguna |
| **2. DB pluggable** | 3-5 días | 🟡 P1 | Fase 1 |
| **3. API + Billing** | 3-5 días | 🟡 P1 | Fase 1 |
| **4. Deploy prod** | 2-3 días | 🟢 P2 | Fases 1-3 |

**Total: ~10-16 días de trabajo enfocado.**

---

## Lo que NO necesitas hacer

- ❌ Reescribir el engine — ya funciona
- ❌ Cambiar de framework — FastAPI es perfecto
- ❌ Kubernetes/microservicios — overkill hasta 10K+ usuarios
- ❌ Cambiar el modelo de embeddings — ONNX local es suficiente para start
- ❌ GraphQL — REST + MCP cubren los use cases

---

## Métricas de éxito

| Milestone | KPI |
|---|---|
| **MVP SaaS** | 1 usuario externo usando la API |
| **Product-Market Fit** | 10 usuarios activos/semana |
| **Revenue** | Primer $1 de Stripe |
| **Scale** | 1000 facts/día sin degradación |

---

*"No necesitas ser Google para escalar. Necesitas ser pragmático."*
