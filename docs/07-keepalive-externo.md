# trackmyseries — Pinger externo (arranque en frío)

## Por qué

El backend está en el **plan free de Render**, que **duerme el servicio tras ~15 min
de inactividad**; la siguiente petición tarda ~30 s en despertarlo (arranque en frío).

Ya existe un mitigador en el repo — `.github/workflows/keepalive.yml`, un cron de
GitHub Actions que hace `curl` a `/health` cada 10 min. **Funciona, pero no es del
todo fiable**: el planificador de cron de GitHub Actions **no garantiza puntualidad**
y en horas punta se retrasa (a veces 15–20 min). Si el retraso supera la ventana de
inactividad de Render, el backend se duerme igual y el usuario se come el arranque en
frío.

Un **pinger externo** (servicio de monitorización) dispara mucho más puntual, cada
5 min, y de paso te avisa si el backend se cae. Es gratis y sustituye (o refuerza) al
workflow de GitHub.

## Qué hay que hacer

Dar de alta un monitor HTTP que haga una petición GET cada **5 minutos** a:

```
https://series-tracker-api-jqx1.onrender.com/health
```

`/health` devuelve `200` y es barato (no toca BD pesada). Con un ping cada 5 min el
servicio nunca llega a los ~15 min de inactividad que lo dormirían.

> **Nota sobre el consumo de horas de Render:** el plan free da 750 h/mes. Mantener
> el servicio despierto 24/7 son ~730 h, así que **cabe**, pero vas justo. Si tuvieras
> otro servicio free en la misma cuenta, vigila el total.

Elige **una** de las dos opciones (no hace falta las dos).

### Opción A — UptimeRobot (recomendada: añade alertas de caída)

1. Crea una cuenta gratis en <https://uptimerobot.com> (el plan free permite 50
   monitores con intervalo mínimo de 5 min).
2. **+ New monitor**:
   - **Monitor Type:** `HTTP(s)`
   - **Friendly Name:** `trackmyseries backend`
   - **URL:** `https://series-tracker-api-jqx1.onrender.com/health`
   - **Monitoring Interval:** `5 minutes`
3. (Opcional) En **Alert Contacts**, añade tu email para recibir aviso si `/health`
   deja de responder.
4. **Create Monitor.** Listo: empieza a pinguear solo.

### Opción B — cron-job.org (más simple, sin alertas ricas)

1. Crea una cuenta gratis en <https://cron-job.org>.
2. **Create cronjob**:
   - **Title:** `trackmyseries keepalive`
   - **URL:** `https://series-tracker-api-jqx1.onrender.com/health`
   - **Schedule:** cada 5 minutos (`Every 5 minutes` / expresión `*/5 * * * *`).
   - **Request method:** `GET`.
3. **Save.** Puedes ver el historial de ejecuciones en el panel.

## Después de configurarlo

- **Verifica** que el monitor marca el endpoint como *up* (status 200) tras el primer
  ping.
- El workflow `keepalive.yml` de GitHub puede **quedarse como refuerzo** (no molesta) o
  desactivarse para no gastar minutos de Actions. Para desactivarlo sin borrarlo,
  comenta el bloque `schedule:` en `.github/workflows/keepalive.yml` (deja
  `workflow_dispatch` para poder lanzarlo a mano).
- Si algún día migras el backend a un plan de pago sin spin-down, este pinger deja de
  ser necesario (aunque las alertas de caída de UptimeRobot siguen siendo útiles).
