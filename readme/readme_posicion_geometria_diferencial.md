# Posicion -> Geometria -> Giro diferencial (para dummies)

Este documento explica (en lenguaje simple) como el programa convierte la posicion detectada de la bola en la pantalla a:

1. Una "trayectoria" geometrica de giro (radio de giro `R`)
2. Una transferencia a velocidades diferenciales de ruedas (`v_left` y `v_right`)

Fuentes principales en el codigo:
- Deteccion de la bola: `src/vision.py`
- Conversion geometrica y dibujo: `src/main.py`
- Control diferencial (radio/ratio/velocidades): `src/control.py`

---

## 1) Entrada: posicion de la bola en la imagen

La funcion `green_detect(...)` devuelve algo como:
- `pt = (x, y)` -> centro del blob verde en coordenadas de la imagen
- `r_ball` -> radio minimo envolvente (usado para dibujo)
- `mask` -> mascara binaria para depurar

En `src/main.py`, cuando hay `pt` y `r_ball > 0`, el programa usa `x` y `y` para calcular como debe girar el robot.

Tambien se dibuja una linea "de referencia" (visual):
- `cv2.line(bgr, (rx, ry), (x, y), ...)`
- donde `(rx, ry)` es el "ancla" del robot (`_robot_anchor(w, h)`).

Ojo: esa linea es solo visual (apunta desde el robot hacia la bola). La curva real que el robot intenta seguir se modela con el `beta` y el radio `R`.

---

## 2) Geometria: de (x, y) a (d, beta)

Tu `main.py` tiene una conversion empirica/calibrada:

### 2.1 Distancia hacia delante: `dy_cm`

Se calcula con:
- `dy_cm = estimate_dy_cm(y)`

La idea simple:
- si la bola esta "mas arriba/abajo" (valor `y` en pixels), eso corresponde a una distancia aproximada al robot.
- si `y` esta por debajo de un umbral (`_DY_Y0`), devuelve `None` y no hay geometria valida.

### 2.2 Desplazamiento lateral: `dx_cm`

Luego calcula:
- `x_prime = x - (w / 2.0)`  (izquierda vs derecha respecto al centro)
- `dx_cm = estimate_dx_cm(x_prime, dy_cm)`

La idea simple:
- la bola esta a la izquierda o a la derecha => eso se traduce en `dx_cm`.
- como el efecto lateral depende de la distancia, `dx_cm` usa `dy_cm` en la formula.

### 2.3 Distancia euclidea y angulo: `d_cm` y `beta_rad`

Con `dx_cm` y `dy_cm`:
- `d_cm = hypot(dx_cm, dy_cm)`
- `beta_rad = atan2(dx_cm, dy_cm)`

Intuicion:
- `beta_rad` es "hacia que lado" hay que girar y "cuanto".
- si la bola esta centrada (`dx_cm` ~ 0) => `beta_rad` ~ 0 => casi recto.
- si la bola se va mucho a un lado => `|beta_rad|` crece => mas giro.

---

## 3) La curva del giro: radio `R = d / (2*sin(beta))`

Tu control diferencial asume que el robot sigue un arco de circulo.

En `src/control.py`:
- `turn_radius_cm(beta_rad, dist_cm)` calcula el radio:
  - `R = dist_cm / (2.0 * sin(beta_rad))`

### Que significa para dummies

- Si `beta` es pequeno (bola casi al centro), `sin(beta)` es pequeno => `R` es enorme => giro "muy abierto" => casi linea recta.
- Si `beta` es grande (bola a un lado), `sin(beta)` es mayor => `R` es mas pequeno => giro "cerrado" => curva marcada.

Tambien hay una proteccion:
- si `abs(beta)` esta por debajo de `DEADBAND_DEG` o `sin(beta)` es casi 0, devuelve `inf` (recto).

---

## 4) Transferencia a ruedas: velocidad interior vs exterior

Ahora viene lo que tu llamas "transferencia de velocidad".

Un robot con ruedas diferenciales gira creando una diferencia de trayectorias:
- la rueda exterior recorre un camino mas largo en el mismo giro => debe ir mas rapida
- la rueda interior recorre un camino mas corto => debe ir mas lenta

### 4.1 Ratio geometrico a partir del radio `R`

En `src/control.py`:
- `DELTA_CM` es la separacion efectiva usada en el modelo (mitad del eje en cm).
- `wheel_speed_ratio(R_cm, delta_cm)` calcula:
  - `ratio = (R - delta) / (R + delta)`

Intuicion:
- cuando el radio `R` es grande (giro suave), el ratio queda cerca de 1 => ruedas casi igual => casi recto.
- cuando el radio `R` baja (giro cerrado), el ratio cambia mas => mayor diferencia de velocidades.

### 4.2 Como salen `v_left` y `v_right`

En `wheel_speeds_from_beta_dist(...)`:

1. Se elige una velocidad base `base` segun la distancia (`DIST_NEAR_CM` / `DIST_FAR_CM`).
2. Se usa el ratio geometrico para repartir esa velocidad entre ruedas.
3. Luego se aplica un refuerzo extra segun `beta`.

---

## 5) Refuerzo de giro (para que encare mas claro)

Aunque el modelo de ratio ya intenta girar, se agrega un empujon adicional:

- `steer = K_BETA_SPEED * beta_rad`
- se limita con `MAX_STEER_DIFF`
- luego:
  - `v_l = v_l + steer`
  - `v_r = v_r - steer`

En comentarios del codigo:
- "Beta < 0 (bola a la izquierda en tu convencion) debe hacer: right > left."

O sea, si la bola esta a la izquierda, el controlador empuja la diferencia de velocidades para que el robot gire hacia ese lado de forma mas evidente.

---

## 6) Donde se conectan todo en ejecucion

En `src/main.py`, cuando hay bola valida:

1. Vision da `pt = (x, y)`
2. Se calcula `dy_cm`, `dx_cm`, `d_cm`, `beta_rad`
3. Se calcula el `payload`:
   - `payload = diff_ctrl.motors_command_from_beta_dist(beta_rad, d_safe)`
4. Ese `payload` contiene:
   - accion (forward/stop)
   - velocidad izquierda y derecha

Ese `payload` es lo que luego se envia por HTTP a tu firmware desde `src/car_motors.py`.

---

## Resumen en una frase

La bola se ve en (x,y); eso se convierte en un angulo `beta` y una distancia `d`; con eso se obtiene un radio de giro `R`; y ese `R` se traduce en una diferencia de trayectorias de ruedas => `v_left` y `v_right` distintas => el robot describe una curva hacia la bola.

