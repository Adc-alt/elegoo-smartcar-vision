# Código en `src/` — flujo actual

## Resumen

El programa **vídeo MJPEG del coche** (`VideoCapture` sobre la misma URL que en el navegador), **detecta verde** en cada frame (HSV + máscara) y muestra **dos ventanas**: imagen BGR con círculo si hay detección, y máscara binaria para calibrar.

## Archivos

| Archivo | Función |
|--------|---------|
| `stream_reader.py` | Define `STREAM_URL` (y puede lanzar `main` si ejecutas este archivo). |
| `vision.py` | `green_detect` → centro o `None`, máscara, radio; **circularidad** + círculo envolvente. |
| `main.py` | Punto de entrada: captura, detección, dibujo, dos `imshow`. |

## Flujo (orden de ejecución)

1. **`main.py`** (al ejecutar `python src/main.py` desde la raíz del repo): si hace falta, añade la raíz del proyecto a `sys.path` para poder importar `src.*`.
2. Se abre **`cv2.VideoCapture(STREAM_URL)`** con `STREAM_URL` importado de `stream_reader.py` (por defecto `http://192.168.4.1/streaming`).
3. Se configura **buffer de captura** a 1 frame para reducir latencia.
4. Se crean dos ventanas **OpenCV** (`BGR` y `mask`), modo redimensionable.
5. **Bucle** hasta pulsar **`q`**:
   - `cap.read()` → frame BGR o fallo.
   - Si hay frame: **`green_detect(frame)`** en `vision.py`:
     - BGR → blur → **HSV** → **`inRange`**; open + close morfológico.
     - Mayor contorno; área ≥ `_MIN_AREA` y **circularidad** ≥ `_MIN_CIRC` (descarta formas alargadas).
     - **`minEnclosingCircle`**: centro y **radio** que rodea todo el blob (el dibujo usa ese radio).
     - Devuelve **`(centro | None, máscara, radio)`**.
   - Se copia el frame, **círculo verde** con ese radio, texto `BGR`.
   - Máscara en **3 canales** (`GRAY2BGR`), texto `mask`.
   - La primera vez que hay frame, **`moveWindow`** coloca la ventana de la máscara a la derecha del vídeo.
   - **`imshow`** en ambas ventanas; **`waitKey(1)`** procesa eventos y lee `q`.
6. Al salir: **`cap.release()`** y **`destroyAllWindows()`**.

## Diagrama

```mermaid
flowchart TD
    start[main.py]
    start --> cap[VideoCapture STREAM_URL]
    cap --> loop[Bucle]
    loop --> read[cap.read frame]
    read --> gd[vision.green_detect]
    gd --> hsv[HSV + inRange + morph]
    hsv --> cnt[mayor contorno + circularidad + minEnclosingCircle]
    cnt --> draw[Dibujar BGR + mask]
    draw --> imshow[imshow x2 + waitKey]
    imshow --> loop
    imshow --> q{tecla q?}
    q -->|sí| end[release + destroy]
    q -->|no| loop
```

## Cómo ejecutar

Desde la **raíz del repositorio** (donde está `requirements.txt`):

```bash
python src/main.py
```

Requisitos: PC en la Wi‑Fi del coche, `opencv-python` instalado. Si el suelo/reflejos entran en la máscara, sube **S mínimo** y acota **H** en `vision.py`; si la bola desaparece, baja un poco S o ensancha H.

### Geometría en cm (misma lógica que en C)

- \(d_y\) desde el píxel vertical \(y\): `estimate_dy_cm(y)`  
  \[
  d_y \approx -10.35 + \frac{7285.24}{y - 87.30}
  \]
- \(d_x = -0.0025 \cdot d_y \cdot x'\) con \(x' = x - w/2\) px → `estimate_dx_cm(x_prime, dy_cm)`.
- Distancia euclídea: \(d = \sqrt{d_x^2 + d_y^2}\) → `math.hypot(dx_cm, dy_cm)`.
- Ángulo: \(\beta = \mathrm{atan2}(d_x, d_y)\) rad → también se imprime en grados.
- Radio de giro (modelo): \(r_{\mathrm{turn}} = d / (2\sin\beta)\) cm → `turn_radius_cm`. Si \(|\sin\beta| < 0.02\) (casi alineado al frente), se imprime `n/a` para no dividir por casi cero.

Constantes en `main.py`: `_DY_A`, `_DY_C`, `_DY_Y0`, `_DX_K`, `_MIN_ABS_SIN_BETA`. Si `y ≤ 87.30`, no hay `d_y` válido.

## English (short)

`main` pulls MJPEG via OpenCV from `STREAM_URL`, runs `green_detect` per frame (HSV threshold + morph + largest contour), then shows two windows: BGR overlay and binary mask for tuning. Press `q` to quit.
