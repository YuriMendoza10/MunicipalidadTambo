import mysql.connector
import telebot
from telebot import types
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("MYTOKEN")
bot = telebot.TeleBot(TOKEN)

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="bd_municipalidad",
    port=3306
)

cursor = db.cursor()

# MANEJADOR DE ESTADOS
user_data = {}

# Comando de inicio
@bot.message_handler(commands=['hola'])
def send_welcome(message):
    bot.reply_to(message, "Hola, soy tu asistente virtual. ¿Cómo puedo ayudarte?")
    # Guardar estado
    user_data[message.chat.id] = {"state": "MENU"}

    # Crear menú con botones
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Seguimiento de Trámite", callback_data="SEG_tramite"))
    markup.add(types.InlineKeyboardButton("Pagos", callback_data="SEG_pagos"))
    markup.add(types.InlineKeyboardButton("Denuncia", callback_data="SEG_denuncia"))
    bot.send_message(message.chat.id, "Opciones:", reply_markup=markup)

#--------------------------------------------------------------------------------------------------------------------
# MANEJADOR DE CALLBACKS (cuando hacen click en un botón)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "SEG_tramite":
        seguimiento_tramite(call)
    elif call.data == "SEG_pagos":
        seguimiento_pagos(call)
    elif call.data == "SEG_denuncia":
        seguimiento_denuncia(call)

#---------------------------------------------------------------------------------------------------------------------
# FUNCIONES PARA CADA BOTÓN
def seguimiento_tramite(call):
    bot.answer_callback_query(call.id)  # Quita el "loading..."
    bot.send_message(call.message.chat.id, "🔎 Por favor ingresa el número de tu trámite:")

    # Guardamos el estado para esperar el número de trámite
    user_data[call.message.chat.id] = {"state": "INGRESAR_TRAMITE"}


def seguimiento_pagos(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "💰 Aquí puedes consultar tus pagos. Ingresa tu DNI:")

    # Guardamos estado
    user_data[call.message.chat.id] = {"state": "INGRESAR_DNI_PAGO"}


def seguimiento_denuncia(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "📢 Describe tu denuncia:")

    # Guardamos estado
    user_data[call.message.chat.id] = {"state": "INGRESAR_DENUNCIA"}

#-----------------------------------------------------------------------------------------------------------
# MANEJAR RESPUESTAS SEGÚN ESTADO
@bot.message_handler(func=lambda message: True, content_types=["text", "photo", "location"])
def manejar_respuestas(message):
    chat_id = message.chat.id

    if chat_id in user_data:
        estado = user_data[chat_id].get("state")
#-----------------------------------INICIO DE TRAMITE -------------------------------------------
        if estado == "INGRESAR_TRAMITE":
            numero = message.text
            # Aquí haces la consulta SQL
            cursor.execute("SELECT estado FROM tramites WHERE numero = %s", (numero,))
            resultado = cursor.fetchone()

            if resultado:
                bot.send_message(chat_id, f"📄 Estado de tu trámite: {resultado[0]}")
            else:
                bot.send_message(chat_id, "❌ No se encontró el trámite.")
            user_data[chat_id]["state"] = "MENU"
#-----------------------------------FIN DE TRAMITE -------------------------------------------
#-----------------------------------INICIO DE PAGO -------------------------------------------
        elif estado == "INGRESAR_DNI_PAGO":
            dni = message.text
            cursor.execute("SELECT monto, estado FROM pagos WHERE dni = %s", (dni,))
            resultado = cursor.fetchone()

            if resultado:
                bot.send_message(chat_id, f"💵 Monto: {resultado[0]}, Estado: {resultado[1]}")
            else:
                bot.send_message(chat_id, "❌ No se encontraron pagos.")
            user_data[chat_id]["state"] = "MENU"
#-----------------------------------FIN DE PAGO -------------------------------------------            
#-----------------------------------INICIO DE DENUNCIA -------------------------------------------
        elif estado == "INGRESAR_DENUNCIA":
            # 1 Guardar descripción
            user_data[chat_id]["denuncia"] = {"descripcion": message.text}
            print( user_data[chat_id]["denuncia"]["descripcion"])
            # 2. Crear botón para compartir ubicación
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            button = types.KeyboardButton("📍 Compartir ubicación", request_location=True)
            markup.add(button)
            # 3. Pedir ubicación
            bot.send_message(chat_id, "Por favor comparte tu ubicación actual:", reply_markup=markup)
            # 4. Cambiar estado
            
            user_data[chat_id]["state"] = "INGRESAR_UBICACION"
            
        
        elif estado == "INGRESAR_UBICACION":
            if message.content_type == "location":
                # Extraer coordenadas
                lat = message.location.latitude
                lon = message.location.longitude

                # Guardar en memoria
                user_data[chat_id]["denuncia"]["latitud"] = lat
                user_data[chat_id]["denuncia"]["longitud"] = lon

                print(f"Ubicación recibida -> Lat: {lat}, Lon: {lon}")

                # Confirmar al usuario
                bot.send_message(chat_id, f"✅ Ubicación recibida.\n📍 Lat: {lat}, Lon: {lon}")

                # Pedir nombre
                bot.send_message(chat_id, "👤 Ingresa tu nombre:")
                user_data[chat_id]["state"] = "INGRESAR_NOMBRE"

            elif message.text and ("maps.app.goo.gl" in message.text or "google.com/maps" in message.text):
                # Si mandan un link en vez de ubicación
                user_data[chat_id]["denuncia"]["link"] = message.text
                print("Link de ubicación recibido:", message.text)

                bot.send_message(chat_id, f"✅ Ubicación recibida.\n📍 {message.text}")
                bot.send_message(chat_id, "👤 Ingresa tu nombre:")
                user_data[chat_id]["state"] = "INGRESAR_NOMBRE"

            else:
                bot.send_message(chat_id, "⚠️ Usa el botón 📍 para enviar tu ubicación o pega un link de Google Maps.")

        elif estado == "INGRESAR_NOMBRE":
            # 3 Guardar nombre
            user_data[chat_id]["denuncia"]["nombre"] = message.text
            bot.send_message(chat_id, "👤 Ingresa tu apellido:")
            user_data[chat_id]["state"] = "INGRESAR_APELLIDO"
            print(user_data[chat_id]["denuncia"]["nombre"] )
        elif estado == "INGRESAR_APELLIDO":
            # 4 Guardar apellido
            user_data[chat_id]["denuncia"]["apellido"] = message.text
            bot.send_message(chat_id, "📞 Ingresa tu número de teléfono:")
            user_data[chat_id]["state"] = "INGRESAR_TELEFONO"
            print(user_data[chat_id]["denuncia"]["apellido"])
        elif estado == "INGRESAR_TELEFONO":
            # 5 Guardar teléfono
            user_data[chat_id]["denuncia"]["telefono"] = message.text
            bot.send_message(chat_id, "📸 Por favor envía una imagen relacionada con la denuncia:")
            user_data[chat_id]["state"] = "INGRESAR_IMAGEN"
            print(user_data[chat_id]["denuncia"]["telefono"])
            
        elif estado == "INGRESAR_IMAGEN":
            #print("DEBUG - Estado INGRESAR_IMAGEN activado")
            #print("Tipo de mensaje:", message.content_type)
            if message.content_type == "photo":
                file_id = message.photo[-1].file_id
                file_info = bot.get_file(file_id)
                file_path = file_info.file_path

                image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
                user_data[chat_id]["denuncia"]["imagen"] = image_url

                print("Imagen guardada en user_data:", user_data[chat_id]["denuncia"]["imagen"])

                bot.send_message(chat_id, "✅ Imagen recibida correctamente")

                # Extraer datos
                datos = user_data[chat_id]["denuncia"]
                descripcion = datos.get("descripcion")
                latitud = datos.get("latitud")  # Puede ser None si no se comparte ubicación
                longitud = datos.get("longitud")  # Puede ser None si no se comparte ubicación
                nombre = datos.get("nombre")
                apellido = datos.get("apellido")
                telefono = datos.get("telefono")
                imagen = datos.get("imagen")  # Puede ser None si no se envía imagen

                # Generar link de Google Maps si se tiene latitud y longitud
                if latitud is not None and longitud is not None:
                    link_maps = f"https://www.google.com/maps/search/?api=1&query={latitud},{longitud}"
                else:
                    link_maps = None  # No se tiene ubicación

                # Guardar en la BD
                cursor.execute(
                    """
                    INSERT INTO denuncias 
                    (descripcion, latitud, longitud, nombre, apellido, telefono, imagen, link_maps)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (descripcion, latitud, longitud, nombre, apellido, telefono, imagen, link_maps)
                )
                db.commit()

                bot.send_message(chat_id, "✅ Tu denuncia ha sido registrada con éxito. ¡Gracias por tu colaboración!")
                user_data[chat_id]["state"] = "MENU"
            else:
                bot.send_message(chat_id, "❌ Debes enviar una imagen para completar la denuncia.")

#-----------------------------------FIN DE DENUNCIA -------------------------------------------

        else:
            bot.send_message(chat_id, "Usa /hola para ver las opciones disponibles.")

    else:
        bot.send_message(chat_id, "Por favor inicia con /hola")

#--------------------------------------------------------------------------------------------
# Inicia el chatbot
bot.polling()

db.close()
