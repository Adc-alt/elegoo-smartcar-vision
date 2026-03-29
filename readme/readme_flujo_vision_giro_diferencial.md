# Flujo completo: de ver la bola a girar (para ~14 años)

Este programa es como un "juego" en el que el coche:

1. Mira por la camara.
2. Encuentra una bola verde.
3. Decide hacia donde tiene que girar.
4. Convierte esa idea en dos velocidades distintas: una para la rueda izquierda y otra para la derecha.
5. (Opcional) Envia esas velocidades por Wi-Fi al coche.
6. Repite todo en bucle.

No hace falta entender matematicas: aqui la clave es **el orden de pasos** y **que dato sale en cada uno**.

---

## El mapa del flujo (orden)

```mermaid
flowchart TD
  A[main.py: bucle principal] --> B[vision.py: green_detect]
  B --> C[main.py: coordenadas -> direccion]
  C --> D[control.py: direccion -> radio R]
  D --> E[control.py: radio R -> v_left/v_right]
  E --> F[main.py: payload JSON]
  F --> G[car_motors.py: HTTP POST (o solo visual con --no-send)]
  G --> A
```

---

## 1) `src/main.py`: el bucle principal

En `src/main.py` se abre el video con:

- `cv2.VideoCapture(STREAM_URL)`

Luego entra en un bucle infinito (`while True`):

- Lee un frame (una imagen) de la camara: `cap.read()`.
- Intenta encontrar la bola verde con `green_detect(...)`.
- Si encuentra la bola, calcula el giro y prepara un mensaje para el coche.
- Si no la encuentra, el coche se queda parado (y en la pantalla aparece "IDLE").

Dato importante: el programa corre continuamente, frame a frame.

---

## 2) `src/vision.py`: detectar la bola (ver donde esta)

La funcion clave es:

- `pt, mask, r_ball = green_detect(frame)`

Aqui:
- `pt = (x, y)` te dice **en que lugar de la imagen** esta el centro de la bola verde.
- `mask` es una imagen en blanco/negro para debug (para ver que considera "verde").
- `r_ball` es un radio para dibujar el circulo (no es "la distancia real exacta").

Si `green_detect` dice "no encontre nada", entonces el programa no tiene direccion que calcular.

---

## 3) `src/main.py`: de (x, y) a "que direccion necesita"

Cuando si hay bola:

1. `x` dice "esta a la izquierda o a la derecha" en la imagen.
2. `y` (por como esta calibrada la camara) se usa para estimar "que tan lejos / hacia delante esta".

Con eso el codigo saca dos cosas:

- `d_cm`: una distancia aproximada al objetivo
- `beta_rad`: un angulo que resume "que giro necesita el coche para encarar la bola"

En `src/main.py` veras la idea:

- `beta_rad = math.atan2(dx_cm, dy_cm)`

Idea para dummies: el coche convierte "donde aparece la bola en la pantalla" en "que giro necesito".

---

## 4) `src/control.py`: convertir el giro en una curva (radio R)

Aqui entra la parte de "trayectoria curva".

El controlador asume que el coche puede girar siguiendo un arco. Para describir esa curva calcula un radio:

- `R = turn_radius_cm(beta_rad, dist_cm)` dentro de `src/control.py`

Traduccion sin matematicas:
- si `beta` es pequeno (bola casi centrada), el giro es "suave" => `R` grande => casi recto
- si `beta` es grande (bola a un lado), el giro es "cerrado" => `R` pequeno => curva marcada

O sea: **`R` es una forma de describir la curva**.

---

## 5) `src/control.py`: "transferencia" a velocidades de ruedas

Un coche con traccion diferencial gira porque:

- una rueda va mas rapida
- la otra rueda va mas lenta

En `src/control.py` el codigo usa el radio `R` para repartir velocidades y producir:

- `v_left`
- `v_right`

Y ademas mete un "empujon" extra segun el signo de `beta` para que el giro sea mas evidente:

- `steer = K_BETA_SPEED * beta_rad`
- se suma a una rueda y se resta en la otra

Resultado final: el robot no se mueve "como una flecha hacia el objetivo", sino que **gira describiendo una curva** usando dos velocidades distintas.

---

## 6) `payload`: el JSON que se manda al coche

La variable `payload` en `src/main.py` es el mensaje que contiene los comandos de motores.

Cuando hay bola valida:

- `payload = diff_ctrl.motors_command_from_beta_dist(beta_rad, d_safe)`

En `src/control.py` se empaqueta con una estructura como:

```json
{
  "motors": {
    "left": {"action": "...", "speed": ...},
    "right": {"action": "...", "speed": ...}
  }
}
```

Si no hay bola valida, `payload` se queda como `stop_payload` (velocidades a 0).

---

## 7) Envio al coche o solo visual

En `src/main.py`:

- si NO usas `--no-send`, el programa manda `payload` con `car.offer_json(payload)`
- si usas `--no-send`, no envia nada: solo muestra ventanas (`cv2.imshow`) y prints de consola

Dentro de `src/car_motors.py` ese mensaje se envia via HTTP POST al ESP32.

---

## 8) Dibujo "de trayectoria" en pantalla (solo para ti)

Tu `main.py` dibuja una linea desde el robot hacia la bola:

- `cv2.line(...)`

Eso es para que veas la idea visualmente.

La "fisica real" la marca lo que se manda en `payload` (las velocidades `v_left/v_right`).

---

## Resumen en una frase

El coche convierte "donde esta la bola en la imagen" en un **angulo**, ese angulo en un **radio de curva**, ese radio en dos velocidades distintas, y con esas velocidades gira hacia la bola.

