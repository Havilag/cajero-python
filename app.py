from pydantic import BaseModel, Field, field_validator, ValidationError
import bcrypt
import psycopg2
import logging

def get_db_connection():
    conn = psycopg2.connect(
        dbname="cajero",
        user="postgres",
        password="root",
        host="localhost",
        port="5432"
    )
    
    return conn

logging.basicConfig(
    filename="seguridad_atm.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def validar_algoritmo_luhn(numero_tarjeta: str) -> bool:
    num = "".join(numero_tarjeta.split())
    
    if not num.isdigit():
        return False

    suma = 0
    alt = False
    
    for i in range(len(num) - 1, -1, -1):
        digito = int(num[i])
        if alt:
            digito *= 2
            if digito > 9:
                digito -= 9
        suma += digito
        alt = not alt
        
    return suma % 10 == 0


class Tarjeta:
    def __init__(self,id_bd:int,  dni: str, balance: float ):
        self.id= id_bd
        self.balance = balance
        self.dni = dni


class Security:
    
    def check_pin(self, pin: str, hashed_pin_bd: str):
        bytes_pin = pin.encode('utf-8')
        bytes_hashed_pin_bd = hashed_pin_bd.encode('utf-8')
        return bcrypt.checkpw(bytes_pin, bytes_hashed_pin_bd)
    
    def hash_pin(self, pin: str) -> str:
        bytes_pin = pin.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_pin = bcrypt.hashpw(bytes_pin, salt)
        return hashed_pin.decode('utf-8') 


class CajeroSchema(BaseModel):
    dni: str
    pin: str
    
    @field_validator("dni")
    @classmethod
    def validar_dni(cls, value: str) -> str:
        dni_limpio = value.strip()
        if (len(dni_limpio.strip())==0 or len(value.strip()) != 8):
            raise ValueError("Error: El DNI no puede estar vacio y debe tener 8 digitos")
        if not dni_limpio.isdigit():
            raise ValueError("El DNI debe contener solo números")
        return dni_limpio
    
    @field_validator("pin")
    @classmethod
    def validar_pin(cls, value: str) -> str:
        pin_limpio = value.strip()
        if (len(pin_limpio.strip())==0 or len(value.strip()) != 6):
            raise ValueError("Error: El PIN no puede estar vacio y debe tener 6 digitos")
        if not pin_limpio.isdigit():
            raise ValueError("El PIN debe contener solo números")
        return pin_limpio


class Cajero:
    def __init__(self):
        self.balance = 10000
        self.tarjeta_activa = None
        self.check = Security()
    
    def login(self, dni: str, pin: str):
        
        conn = get_db_connection()
        cursor = conn.cursor()

        
        try:
            cursor.execute("SELECT id, pin, tarjeta_balance, intentos_fallidos, bloqueada FROM tarjeta WHERE dni=%s;", (dni,))
            result = cursor.fetchone()
        
            if result is None:
                print("Error: El DNI es incorrecto")
                return False
            
            id_bd, hashed_pin, saldo_bd, intentos, esta_bloqueada = result[0], result[1], result[2], result[3], result[4]
            
            if esta_bloqueada:
                print("🔒 Acceso denegado: Esta tarjeta se encuentra BLOQUEADA por seguridad.")
                return False
            
            validation = self.check.check_pin(pin, hashed_pin)
            
            
            if validation:
                if intentos > 0:
                    cursor.execute("UPDATE tarjeta SET intentos_fallidos = 0 WHERE id = %s;", (id_bd,))
                    conn.commit()
                    
                self.tarjeta_activa = Tarjeta(id_bd, dni, float(saldo_bd))
                return True
            
            else:
                intentos_actuales = intentos + 1
                print(f"Pin incorrecto, Inteto fallido {intentos_actuales} de 3")
                
                if (intentos_actuales >=3):
                    cursor.execute("UPDATE tarjeta SET intentos_fallidos=%s, bloqueada=TRUE WHERE id=%s",(intentos_actuales, id_bd))
                    print("🚨Has superado el límite de intentos. Tu tarjeta ha sido BLOQUEADA.")
                else:
                    cursor.execute("UPDATE tarjeta SET intentos_fallidos=%s WHERE id=%s",(intentos_actuales, id_bd))
                conn.commit()
                return False
            
        except Exception as e:
            print(f"Error de operacion: {e}")
            return False
        
        finally:
            cursor.close()
            conn.close()
    
    
    def ver_saldo(self):
        if self.tarjeta_activa is None:
            print("Error: no hay tarjeta ingresada")
            return 
        print(f"Saldo disponible en su tarjeta: {self.tarjeta_activa.balance}")
    
    
    def retirar(self, amount: float):
        
        monto_maximo_sospechoso = 5000.0
        
        if (self.tarjeta_activa is None):
            print("Error: No hay usuario")
            return False
    
        if (amount <= 0):
            print("El monto debe ser mayor a 0")
            return False
        
        if (amount >= monto_maximo_sospechoso):
            print("🚨 Operación rechazada automáticamente por seguridad")
            print(f"El monto solicitado (${amount}) se considera actividad sospechosa (Monto inusualmente alto).")
            logging.critical(f"ALERTA ANTIFRAUDE: Retiro rechazado por monto sospechoso de ${amount} en DNI {self.tarjeta_activa.dni}.")
            return False
        
        if (amount > self.balance):
            print("El cajero no cuenta con dinero suficiente")
            return False
        
        if (amount > self.tarjeta_activa.balance):
            print("No cuenta con saldo suficiente para esta operacion")
            return False
    
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            retiro_diario = 2500.0
            cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM historial WHERE tarjeta_id = %s AND tipo_operacion = 'RETIRO' AND fecha::date = CURRENT_DATE;", (self.tarjeta_activa.id,))
            retirado_hoy = float(cursor.fetchone()[0])
            
            if ((retirado_hoy + amount) > retiro_diario):
                print(f"Operación rechazada: Supera el límite de retiro diario (${retiro_diario}).")
                print(f"Ya has retirado ${retirado_hoy} hoy. Monto máximo disponible restante: ${retiro_diario - retirado_hoy}")
                logging.warning(f"Retiro rechazado: DNI {self.tarjeta_activa.dni} excedió límite diario acumulado.")
                return False
            
            nuevo_saldo = self.tarjeta_activa.balance - amount
            
            cursor.execute("UPDATE tarjeta SET tarjeta_balance=%s WHERE id = %s", (nuevo_saldo, self.tarjeta_activa.id))
            cursor.execute("INSERT INTO historial (tarjeta_id, tipo_operacion, monto) VALUES (%s, %s, %s);", (self.tarjeta_activa.id,"RETIRO",amount))
            conn.commit()
            
            self.tarjeta_activa.balance = nuevo_saldo
            self.balance -= amount
            
            print(f"¡Retiro exitoso! Has retirado ${amount}")
            print(f"Tu nuevo saldo es: ${nuevo_saldo}")
            
            return True

        except Exception as e:
            print(f"Error de operación: {e}")
            return False
        
        finally:
            cursor.close()
            conn.close()


    def deposito(self, amount):
        if self.tarjeta_activa is None:
            print("Error: no hay tarjeta ingresada")
            return 
        
        if(amount < 10):
            print("El deposito debe ser de minimo 10 soles")
            return False
        
        nuevo_saldo = self.tarjeta_activa.balance + amount
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE tarjeta SET tarjeta_balance=%s WHERE id = %s", (nuevo_saldo, self.tarjeta_activa.id))
            cursor.execute("INSERT INTO historial (tarjeta_id, tipo_operacion, monto) VALUES (%s, %s, %s);", (self.tarjeta_activa.id,"DEPOSITO",amount))
            conn.commit()
            
            self.tarjeta_activa.balance = nuevo_saldo
            self.balance += amount
            
            print(f"✅ ¡Depósito exitoso! Has depositado ${amount}")
            print(f"Tu nuevo saldo es: ${nuevo_saldo}")
            
        except Exception as e:
            print(f"Error de oparion del deposito: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    def ver_historial(self):
        if self.tarjeta_activa is None:
            print("Error: no hay tarjeta ingresada")
            return 
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT tipo_operacion, monto, fecha FROM historial WHERE tarjeta_id=%s",(self.tarjeta_activa.id,))
        movimientos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        print("\n📜 === HISTORIAL DE MOVIMIENTOS ===")
        
        if not movimientos:
            print("No realizo nigun movimiento")
        else:
            for mov in movimientos:
                fecha = mov[2].strftime('%Y-%m-%d %H:%M:%S')
                tipo = mov[0]
                cantidad = mov[1]
                print(f"[{fecha}] {tipo}: ${cantidad}")

def main():
    cajero_atm = Cajero()
    
    print("\n" + "="*35)
    print("      BIENVENIDO AL CAJERO ATM      ")
    print("="*35)
    
    print("💳 [SISTEMA] Por favor, introduzca su número de tarjeta:")
    tarjeta_ingresada = input("Número de tarjeta (16 dígitos): ").strip()
    
    if not validar_algoritmo_luhn(tarjeta_ingresada):
        print("\n Error Crítico: La tarjeta ingresada es FALSA o está dañada.")
        print("🔒 Operación abortada por seguridad de hardware (Falló algoritmo de Luhn).")
        print("="*35 + "\n")
        return

    print("\nTarjeta detectada correctamente.")
    
    dni_ingresado = input("Por favor, ingrese su DNI: ").strip()
    pin_ingresado = input("Por favor, ingrese su PIN: ").strip()
    
    try:
        datos_validados = CajeroSchema(dni=dni_ingresado, pin=pin_ingresado)
    except ValidationError as e:
        print("Error de formato en los datos")
        for error in e.errors():
            print(f"- {error['msg']}")
        print("="*35 + "\n")
        return
    
    
    print("\n⏳ Verificando credenciales en la base de datos...")
    print("-" * 35)
    
    login_exitoso = cajero_atm.login(datos_validados.dni, datos_validados.pin)
    
    if login_exitoso:
        print("🎉 ¡Acceso exitoso!")
        
        while True:
            print("\n" + "-"*35)
            print("          MENÚ DE OPERACIONES          ")
            print("-"*35)
            print("1. Ver Saldo")
            print("2. Retirar Dinero")
            print("3. Depositar Dinero")
            print("4. Ver Historial de Movimientos")
            print("5. Salir")
            print("-"*35)
            
            opcion = input("Seleccione una opción (1-5): ").strip()
            
            if opcion == "1":
                cajero_atm.ver_saldo()
                
            elif opcion == "2":
                try:
                    monto_solicitado = float(input("Ingrese el monto que desea retirar: $"))
                    cajero_atm.retirar(monto_solicitado)
                except ValueError:
                    print("❌ Error: Debe ingresar un valor numérico válido.")
                    
            elif opcion == "3":
                try:
                    monto_deposito = float(input("Ingrese el monto que desea depositar: $"))
                    cajero_atm.deposito(monto_deposito)
                except ValueError:
                    print("❌ Error: Debe ingresar un valor numérico válido.")
            
            elif opcion == "4":
                cajero_atm.ver_historial()
                
            elif opcion == "5":
                print("\n👋 Retirando tarjeta... Gracias por usar nuestro servicio.")
                cajero_atm.tarjeta_activa = None
                break
            
            else:
                print("❌ Opción no válida. Por favor, intente de nuevo.")
                
    else:
        print("🔒 Acceso denegado. Inténtalo de nuevo ejecutando el programa.")
    print("="*35 + "\n")
    
    

if __name__ == '__main__':
    main()