# STACK.MD — Guía de seguridad y arquitectura para apps con IA
> Basado en los 10 tips de @elijs.dev para apps construidas con Lovable, Cursor, Bolt, Claude, v0 u otras herramientas de vibe coding.
> Usa este archivo como contexto inicial en cada nuevo proyecto.

---

## 🧱 ARQUITECTURA BASE

- El frontend **nunca** maneja lógica sensible ni se comunica directamente con APIs externas de IA.
- Toda llamada a APIs externas (OpenAI, Anthropic, Stripe, Supabase, etc.) pasa por un **servidor proxy / backend propio**.
- Las API keys viven **únicamente en variables de entorno del servidor** (`.env`), nunca en el cliente.
- Usa ORMs (Prisma, Sequelize, TypeORM) para acceso a base de datos. **Nunca SQL crudo con interpolación de strings.**

```
FRONTEND → PROXY SERVER (tuyo) → EXTERNAL API (OpenAI / Anthropic / etc.)
```

---

## 🔐 SEGURIDAD — CHECKLIST OBLIGATORIO ANTES DE PUBLICAR

### 1. Protección DDoS y tráfico malicioso
- [ ] Usa **Cloudflare** o WAF (Web Application Firewall) frente al backend.
- [ ] El backend no debe recibir tráfico directo sin pasar por la capa de protección.

### 2. API Keys
- [ ] **Nunca en el frontend.** Siempre en variables de entorno del servidor.
- [ ] Activa **alertas de consumo** en Anthropic, OpenAI, Stripe y Supabase desde el día 1.
- [ ] Revisa en producción: ¿este código corre en el servidor o en el navegador del usuario?

### 3. Rate Limiting (desde el día 1)
- [ ] Implementa límite de peticiones por IP y por usuario (ej: 100 req/min).
- [ ] Herramientas: **Upstash Redis**, middleware de Next.js, Express rate-limit.
- [ ] Agrega **CAPTCHA** si el endpoint es público o sensible (registro, login, contacto).

### 4. CORS — Reglas estrictas
- [ ] Define exactamente qué dominios pueden consumir tu API.
- [ ] **Nunca uses `*` en producción.**
- [ ] Permite solo: `tuapp.com`, `admin.tuapp.com`, y los dominios reales que necesites.

### 5. Validación de inputs
- [ ] Valida **todos los inputs del usuario** antes de procesarlos (evita SQL injection y XSS).
- [ ] Aplica: límite de caracteres, tipo de dato, formato permitido, caracteres especiales bloqueados.
- [ ] Valida también los datos que **retornan tus endpoints**, no solo los que entran.

### 6. Manejo de errores
- [ ] Agrega `try/catch` en **cada llamada a la API**.
- [ ] Muestra mensajes útiles al usuario (no "error 500").
- [ ] Loggea errores con **Sentry** u otra herramienta desde el primer deploy.

### 7. Tareas largas (no bloquear el servidor)
- [ ] Usa **colas (queues)** para tareas pesadas (generación de contenido, procesamiento de archivos).
- [ ] Procesa en **background workers**, no en el hilo principal.
- [ ] Evita timeouts y caídas por carga.

### 8. Signup y acceso
- [ ] Agrega **CAPTCHA** en el formulario de registro para evitar bots.
- [ ] Implementa protección contra fuerza bruta en login.

---

## 📋 LEGAL — ANTES DE PUBLICAR

- [ ] **Política de privacidad**: qué datos recopilo, para qué, por cuánto tiempo, si los comparto con terceros.
- [ ] **Términos y condiciones**: reglas de uso de la app.
- [ ] **Declaración de datos** (cumplimiento): datos recopilados, finalidad, retención, terceros.
- [ ] **Marca y propiedad intelectual**: registrar nombre/logo si aplica (ej: INAPI en Chile, SIC en Colombia).

---

## 🛠️ STACK RECOMENDADO

| Capa | Herramientas sugeridas |
|---|---|
| Frontend | Next.js, React, Tailwind |
| Proxy / Backend | Next.js API Routes, Express, Fastify |
| Base de datos | Supabase (PostgreSQL) + Prisma ORM |
| Auth | Supabase Auth, Auth.js, Clerk |
| Rate Limiting | Upstash Redis, express-rate-limit |
| Seguridad / WAF | Cloudflare |
| Monitoreo de errores | Sentry |
| Variables de entorno | `.env.local` (dev), variables del servidor (prod) |
| Colas / Background | Upstash QStash, BullMQ, Inngest |
| Validación | Zod, Yup, Joi |
| CAPTCHA | hCaptcha, Turnstile (Cloudflare), reCAPTCHA |

---

## ✅ TEST ANTES DE LANZAR

- [ ] Pide a **3 personas que usen la app sin explicarles nada**. Ahí vas a ver los problemas reales.
- [ ] Revisa: Arquitectura, Seguridad, Flujos de usuario, Datos críticos.
- [ ] Verifica que no haya API keys visibles en el navegador (DevTools → Network → Headers).
- [ ] Confirma que los errores de API no exponen información interna al usuario.

---

## 🚨 LOS 3 ERRORES MÁS COMUNES EN APPS HECHAS CON IA

1. **CORS abierto a cualquier dominio** (`*` en producción).
2. **Sin alertas de consumo** en Anthropic, OpenAI, Stripe o Supabase → un bot puede vaciarte la cuenta en horas.
3. **Signup sin CAPTCHA** → registro masivo de bots.

---

## 🌐 SEGURIDAD DE INFRAESTRUCTURA

- [ ] Fuerza **HTTPS** en todos los endpoints — nunca HTTP en producción.
- [ ] Configura **headers de seguridad HTTP** con `helmet.js` (o equivalente):
  - `Content-Security-Policy` (CSP) — evita XSS
  - `Strict-Transport-Security` (HSTS) — fuerza HTTPS
  - `X-Frame-Options` — evita clickjacking
  - `X-Content-Type-Options` — evita MIME sniffing
- [ ] Escanea dependencias vulnerables regularmente:
  - `npm audit` en cada deploy
  - **Snyk** o **Dependabot** (GitHub) para alertas automáticas
- [ ] Mantén dependencias actualizadas — las vulnerabilidades más explotadas son en paquetes desactualizados.

---

## 🗝️ GESTIÓN DE SECRETOS (nivel producción)

- [ ] Usa un **vault dedicado** para secrets en producción:
  - **Doppler** (más simple, recomendado para indie/startups)
  - **AWS Secrets Manager** o **HashiCorp Vault** (empresarial)
- [ ] Implementa **rotación periódica** de API keys (cada 90 días como mínimo).
- [ ] Nunca loggees secrets ni los incluyas en mensajes de error.
- [ ] Audita quién tiene acceso a cada secret y revoca accesos de colaboradores que salen del proyecto.

---

## 📁 SEGURIDAD EN UPLOADS DE ARCHIVOS

> Si tu app acepta archivos del usuario, esta sección es crítica.

- [ ] Valida el **tipo real del archivo** (magic bytes), no solo la extensión — un `.jpg` puede contener código malicioso.
- [ ] Define un **límite de tamaño** máximo por archivo y por usuario.
- [ ] Nunca sirvas archivos subidos por usuarios desde el mismo dominio de la app — usa un subdominio o CDN separado.
- [ ] Escanea archivos con antivirus si manejas documentos sensibles (ClamAV, VirusTotal API).
- [ ] Almacena uploads en un bucket privado (S3, Supabase Storage) con URLs firmadas y de tiempo limitado.

---

## 📊 MONITOREO Y ALERTAS EN TIEMPO REAL

- [ ] Detecta **comportamiento anómalo**: un usuario haciendo 500 requests en 1 minuto es una señal de abuso.
- [ ] Configura alertas por:
  - Picos de consumo de tokens o créditos
  - Intentos de login fallidos masivos
  - Errores 500 en producción
  - Latencia inusualmente alta
- [ ] Herramientas: **Sentry** (errores), **Datadog** / **Grafana** (métricas), **Upstash** (rate limiting con visibilidad).
- [ ] Ten un **runbook mínimo**: qué hacer si la app cae, quién recibe la alerta, cómo escalar.

---

## 🤖 SEGURIDAD ESPECÍFICA DE IA

> Lo que casi nadie considera al construir apps con LLMs.

- [ ] **Prompt injection**: un usuario puede intentar manipular tu system prompt vía input. Sanitiza y valida lo que entra al prompt.
- [ ] **No expongas el system prompt** — nunca lo retornes al cliente ni lo incluyas en respuestas de error.
- [ ] **Filtra el output de la IA** antes de mostrarlo al usuario si maneja datos sensibles o acciones críticas.
- [ ] Define qué puede y qué **no puede hacer la IA** en tu app — y aplícalo en el backend, no solo en el prompt.
- [ ] Si usas **function calling o tool use**: valida que la IA solo pueda llamar las funciones que autorizaste, con los parámetros correctos.
- [ ] Loggea todas las interacciones con la IA para auditoría y detección de abuso.

---

## ⚖️ CUMPLIMIENTO LEGAL SEGÚN CONTEXTO

| Situación | Qué aplica |
|---|---|
| Usuarios en Europa | **GDPR** — consentimiento, derecho al olvido, portabilidad de datos |
| Usuarios en Colombia | **Ley 1581 de 2012** — habeas data, aviso de privacidad, registro en SIC |
| App con pagos | **PCI DSS** — nunca almacenes datos de tarjeta, usa Stripe/Wompi |
| App de salud | **Historia clínica digital** — regulación específica por país |
| App con menores | Protección especial de datos, verificación de edad |

- [ ] Implementa **derecho al olvido**: el usuario puede pedir que se borren todos sus datos.
- [ ] Mantén un **registro de auditoría** de quién accedió a qué datos sensibles y cuándo.
- [ ] Si usas datos para entrenar modelos: decláralo explícitamente en tu política de privacidad.

---

## 📶 NIVELES DE SEGURIDAD POR ETAPA

| Etapa | Prioridad |
|---|---|
| MVP / prueba | Checklist básico + API keys en servidor + rate limiting + CORS |
| App con usuarios reales | + headers HTTP + npm audit + prompt injection + monitoreo |
| App con pagos o datos sensibles | + vault de secrets + uploads seguros + cumplimiento legal |
| App regulada (salud, finanzas) | + pentest profesional + auditoría + cumplimiento sectorial |

---

## 💸 COSTOS Y TOKENS — CONTROL DESDE EL DÍA 1

> Un bot o un usuario abusivo puede vaciarte la cuenta en horas si no tienes límites.

- [ ] Define un **presupuesto máximo mensual** en cada proveedor (Anthropic, OpenAI, Stripe, Supabase) **antes de escribir la primera línea de código**.
- [ ] Configura **alerta al 80%** del presupuesto y **corte automático al 100%**.
- [ ] Establece un **límite máximo de tokens por request** para evitar prompts gigantes que disparen la factura.
- [ ] Implementa **caché de respuestas** para queries repetidas — si ya tienes la respuesta, no llames a la API.
- [ ] Loggea el **consumo por usuario** para detectar patrones de abuso temprano.

```
Presupuesto mensual → Alerta 80% → Corte 100%
Tokens por request → máximo definido (ej: 2000 tokens input, 1000 output)
Caché → Redis o similar para respuestas repetidas
```

---

## 🔑 AUTENTICACIÓN ROBUSTA

- [ ] Usa **JWT con expiración corta** (ej: 15 min) + refresh tokens de larga duración.
- [ ] Implementa **revocación de sesiones activas** (logout real, no solo borrar el token en el cliente).
- [ ] Agrega **2FA** si manejas datos sensibles, pagos o acceso administrativo.
- [ ] Bloquea IPs o usuarios tras N intentos fallidos de login (brute force protection).
- [ ] Herramientas recomendadas: **Supabase Auth**, **Clerk**, **Auth.js**.

---

## 🌍 VARIABLES DE ENTORNO — REGLAS FIJAS

- [ ] **Nunca subir `.env` a GitHub** — agrega `.env*` al `.gitignore` desde el primer commit.
- [ ] Usa `.env.local` para desarrollo y variables del servidor (no archivos) para producción.
- [ ] Si una API key quedó expuesta accidentalmente: **rótala de inmediato** en el dashboard del proveedor.
- [ ] Separa variables por ambiente: `NEXT_PUBLIC_` solo para lo que realmente debe ser público.
- [ ] Audita periódicamente qué keys existen y cuáles siguen activas.

```
.env.local        → desarrollo local (en .gitignore)
Variables servidor → producción (Vercel, Railway, Render, etc.)
Nunca             → hardcodeadas en el código ni en el frontend
```

---

## 🗄️ BACKUPS Y RESILIENCIA

- [ ] Confirma que tu base de datos tiene **backups automáticos** activos (Supabase los hace, pero verifícalo).
- [ ] Define qué pasa si un proveedor cae (OpenAI, Anthropic tienen outages) — ¿tienes fallback o mensaje claro al usuario?
- [ ] Guarda logs de las interacciones críticas para poder reconstruir estado si algo falla.
- [ ] Ten un **plan de contingencia mínimo**: página de mantenimiento, notificación a usuarios, tiempo estimado de recuperación.

---

> **Recuerda:** Que la app funcione no significa que esté lista para producción.
> Vibe coding no es el problema. Publicar sin saber qué publicas, sí.
