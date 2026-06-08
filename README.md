# 🏧 Cajero Automático (ATM) en Python

Proyecto desarrollado en Python que simula el funcionamiento básico de un Cajero Automático (ATM), incorporando mecanismos de autenticación, seguridad, persistencia de datos mediante PostgreSQL y medidas de prevención de fraude.

## Características

### 🔐 Seguridad
- Autenticación mediante DNI y PIN.
- PIN almacenado utilizando hash con bcrypt.
- Bloqueo automático de la tarjeta después de 3 intentos fallidos consecutivos.
- Validación de tarjetas mediante el Algoritmo de Luhn.
- Registro de eventos de seguridad y alertas antifraude en `seguridad_atm.log`.

### 💳 Operaciones Bancarias
- Consulta de saldo.
- Depósitos.
- Retiros.
- Historial de movimientos.

### 🛡️ Prevención de Fraude
- Límite de retiro diario.
- Detección de retiros sospechosos por montos elevados.
- Bloqueo automático de tarjetas comprometidas.

### 🗄️ Persistencia de Datos
- Base de datos PostgreSQL.
- Registro de tarjetas y saldos.
- Registro histórico de transacciones.

---

# Tecnologías Utilizadas

- Python 3.x
- PostgreSQL
- psycopg2
- bcrypt
- Pydantic
- logging

---

# Configuración de Base de Datos

Crear una base de datos llamada:

```sql
CREATE DATABASE cajero;
```

Tabla de tarjetas:

```sql
CREATE TABLE tarjeta (
    id SERIAL PRIMARY KEY,
    dni VARCHAR(8) NOT NULL UNIQUE,
    pin VARCHAR(255) NOT NULL,
    tarjeta_balance NUMERIC(10,2) DEFAULT 0,
    intentos_fallidos INTEGER DEFAULT 0,
    bloqueada BOOLEAN DEFAULT FALSE
);
```

Tabla de historial:

```sql
CREATE TABLE historial (
    id SERIAL PRIMARY KEY,
    tarjeta_id INTEGER REFERENCES tarjeta(id),
    tipo_operacion VARCHAR(20),
    monto NUMERIC(10,2),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

# Datos de Prueba

Número de tarjeta válido para pruebas:

```text
1234567812345670
```

Usuarios disponibles:

| DNI | PIN |
|------|------|
| 11111111 | 123456 |
| 22222222 | 567800 |
| 33333333 | 000000 |
| 44444444 | 987600 |

---

# Instalación

```bash
pip install psycopg2 bcrypt pydantic
```

Configurar la conexión PostgreSQL en el código según tu entorno local.

---

# Ejecución

```bash
python main.py
```

---

# Flujo de Uso

1. Ingresar el número de tarjeta.
2. Validar la tarjeta mediante el algoritmo de Luhn.
3. Ingresar DNI y PIN.
4. Acceder al menú principal.
5. Realizar operaciones:
   - Consultar saldo.
   - Retirar dinero.
   - Depositar dinero.
   - Ver historial de movimientos.
6. Salir del sistema.

---

# Funcionalidades Implementadas

- Modularidad mediante clases y funciones.
- Manejo de excepciones.
- Validación de datos con Pydantic.
- Persistencia de datos con PostgreSQL.
- Autenticación con PIN cifrado.
- Consulta de saldo.
- Depósitos.
- Retiros.
- Historial de transacciones.
- Bloqueo por intentos fallidos.
- Límite de retiro diario.
- Detección de actividad sospechosa.
- Algoritmo de Luhn.
- Logs de seguridad.

---

# Autor

Hector Antonio Avila Gonzales.
