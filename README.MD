# OptiSolver Desktop

Aplicación de escritorio para resolver problemas de programación lineal con el **Método Simplex Primal** y el **Método Simplex Dual**, mostrando el procedimiento paso a paso mediante tablas de iteración.

**Autor:** Olmedo Ramírez Axel Yahir

## Características

- Maximización y minimización.
- Selección del algoritmo: Simplex Primal o Simplex Dual.
- Hasta 8 variables de decisión y 10 restricciones.
- Restricciones de tipo ≤, ≥ y =, con signo seleccionable por fila.
- Matriz de entrada dinámica: los campos se generan según n y m.
- Entrada de coeficientes como enteros, decimales o fracciones (por ejemplo `1/2`).
- Tabla inicial y una tabla por cada iteración, con el elemento pivote resaltado.
- Prueba del cociente visible: columna θ en el Primal y fila θ en el Dual.
- Resumen final con el valor óptimo Z*, el vector óptimo x* y las variables básicas.
- Detección de problemas no acotados e infactibles con alertas visuales.
- Aviso cuando el método elegido no es aplicable al problema.
- Visualización en fracciones o decimales.
- Tema claro y oscuro.
- Cuatro ejemplos precargados (Primal, Dual, no acotado e infactible).

## Requisitos

- Windows 10 u 11.
- Python 3.10 o superior (solo para ejecutar desde el código fuente o compilar).
- Dependencias: NumPy (`requirements.txt`).

Si solo quieres usar la aplicación, descarga el ejecutable desde la sección **Releases** del repositorio. No requiere tener Python instalado.

## Estructura del proyecto

```
OptiSolver/
├── simplex.py        # Motor Simplex (Primal, Dual, historial, excepciones)
├── gui.py            # Interfaz gráfica en Tkinter
├── test_simplex.py   # Casos de prueba del motor
├── requirements.txt  # Dependencias
├── build.bat         # Genera el ejecutable
└── run.bat           # Ejecuta la app desde el código fuente
```

## Ejecución desde el código fuente

1. Clona el repositorio:
   ```
   git clone https://github.com/axelOlm/OptiS_Cuaz.git
   cd OptiSolver
   ```
2. Ejecuta con doble clic en `run.bat`, o desde la terminal:
   ```
   pip install -r requirements.txt
   python gui.py
   ```

## Compilación del ejecutable (Windows)

1. Instala Python 3.10 o superior de 64 bits desde python.org, marcando **Add Python to PATH**.
2. Haz doble clic en `build.bat`. El script crea un entorno virtual, instala las dependencias y ejecuta PyInstaller.
3. El ejecutable queda en `dist\OptiSolver_Desktop.exe`.

Comando equivalente:
```
pyinstaller --noconfirm --clean --onefile --windowed --name OptiSolver_Desktop gui.py
```

**Notas**
- Al abrir el `.exe` en otro equipo, Windows SmartScreen puede mostrar "Windows protegió su PC". Pulsa **Más información → Ejecutar de todos modos**.
- Si tu antivirus lo marca como falso positivo, quita `--onefile` en `build.bat` y distribuye la carpeta `dist\OptiSolver_Desktop\` comprimida.
- El primer arranque con `--onefile` puede tardar unos segundos.

## Uso

1. Elige **Maximizar** o **Minimizar**.
2. Elige el método: **Simplex Primal** o **Simplex Dual**.
3. Define el número de variables (n) y de restricciones (m).
4. Ingresa los coeficientes de la función objetivo (fila `Z`) y de cada restricción, con su signo y su lado derecho `b`.
5. Pulsa **Resolver** (o `Ctrl+Enter`).
6. Revisa los resultados:
   - La barra lateral de datos se oculta y las tablas ocupan la pantalla.
   - Navega con ◀ ▶ o con los números de iteración.
   - Cambia entre **Una** (una tabla) y **Todas** (todas las tablas).
   - Activa o desactiva **Fracciones**.
   - Usa **Mostrar datos** para editar el problema y volver a resolver.

El menú **Cargar ejemplo** rellena automáticamente los casos de prueba.

## Cuándo usar cada método

| Método | Se puede usar cuando | Si no se cumple |
|---|---|---|
| Primal | Todos los lados derechos b ≥ 0 | La app sugiere usar el Dual |
| Dual | La fila Z no tiene coeficientes negativos (solución superóptima) | La app sugiere usar el Primal |

Implementación interna:
- Las restricciones ≥ se multiplican por −1 para convertirlas a ≤.
- Una restricción `=` se divide en dos desigualdades (≤ y ≥), por lo que requiere el Dual.
- Minimizar Z se resuelve como maximizar −Z, y el signo se revierte al mostrar el resultado.
- Los empates en la prueba del cociente se resuelven con la regla de Bland.
- Se usa una tolerancia numérica de 1e-9.

## Casos de prueba

| Caso | Problema | Método | Resultado |
|---|---|---|---|
| Primal | Max Z = 3x₁ + 5x₂ <br> x₁ ≤ 4, 2x₂ ≤ 12, 3x₁ + 2x₂ ≤ 18 | Primal | x = (2, 6), Z = 36 |
| Dual | Min Z = 2x₁ + 3x₂ <br> x₁ + x₂ ≥ 5, x₁ + 2x₂ ≥ 8 | Dual | x = (2, 3), Z = 13 |
| No acotado | Max Z = x₁ + x₂ <br> x₁ − x₂ ≤ 1, x₁ − 2x₂ ≤ 2 | Primal | Alerta: solución no acotada |
| Infactible | Min Z = x₁ + x₂ <br> x₁ + x₂ ≥ 5, x₁ + x₂ ≤ 2 | Dual | Alerta: problema infactible |

Para ejecutar las pruebas del motor:
```
python test_simplex.py          # imprime los tableaux de los cuatro casos
python -m pytest test_simplex.py  # valida los resultados (requiere: pip install pytest)
```

## Limitaciones

- No implementa Big-M ni Dos Fases: el Primal exige b ≥ 0 y el Dual exige factibilidad dual.
- Todas las variables de decisión son no negativas (xⱼ ≥ 0).
- Máximo de 8 variables y 10 restricciones (configurable con `N_MAX` y `M_MAX` en `gui.py`).
- La fuente recomendada es DM Sans; si no está instalada, se usa Segoe UI.

## Tecnologías

Python · NumPy · Tkinter · PyInstaller