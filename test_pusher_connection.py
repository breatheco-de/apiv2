"""
Script para verificar que Pusher está configurado correctamente para conectarse al servidor Soketi.

Ejecutar con:
  poetry run python test_pusher_connection.py

O desde Django shell:
  poetry run python manage.py shell
  >>> exec(open('test_pusher_connection.py', encoding='utf-8').read())
"""

import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "breathecode.settings")
django.setup()

from django.contrib.auth.models import User

from breathecode.feedback.services.pusher_service import get_pusher_client, send_survey_event

print("=" * 60)
print("VERIFICACIÓN DE CONFIGURACIÓN DE SOKETI PARA LA CONEXIÓN CON PUSHER")
print("=" * 60)
print()

# 1. Verificar variables de entorno
print("1. Verificando variables de entorno...")
app_id = os.environ.get("SOKETI_APP_ID", "")
key = os.environ.get("SOKETI_KEY", "")
secret = os.environ.get("SOKETI_SECRET", "")
host = os.environ.get("SOKETI_HOST", "")
port = os.environ.get("SOKETI_PORT", "")


print(f"   SOKETI_APP_ID: {'✅ Configurado' if app_id else '❌ No configurado'}")
print(f"   SOKETI_KEY: {'✅ Configurado' if key else '❌ No configurado'}")
print(f"   SOKETI_SECRET: {'✅ Configurado' if secret else '❌ No configurado'}")
print(f"   SOKETI_HOST: {'✅ Configurado' if host else '❌ No configurado'}")
print(f"   SOKETI_PORT: {'✅ Configurado' if port else '❌ No configurado'}")
print()

if not app_id or not key or not secret or not host or not port:
    print("❌ ERROR: Faltan variables de entorno de Soketi")
    print("   Configura las variables en Heroku o en tu archivo .env")
    sys.exit(1)

# 2. Verificar que el cliente se crea
print("2. Creando cliente de Pusher...")
client = get_pusher_client()

if client is None:
    print("   ❌ ERROR: No se pudo crear el cliente de Pusher")
    print("   Revisa las variables de entorno")
    sys.exit(1)
else:
    print("   ✅ Cliente de Pusher creado correctamente")
print()

# 3. Obtener un usuario de prueba
print("3. Obteniendo usuario de prueba...")
user = User.objects.first()
if not user:
    print("   ⚠️  No hay usuarios en la BD. Creando usuario de prueba...")
    user = User.objects.create_user(username="test_pusher", email="test_pusher@example.com", password="test123")
    print(f"   ✅ Usuario de prueba creado: {user.email}")
else:
    print(f"   ✅ Usuario encontrado: {user.email} (ID: {user.id})")
print()

# 4. Probar enviar un evento de prueba
print("4. Enviando evento de prueba a Soketi con el cliente de Pusher...")
print(f"   Canal: public-user-{user.id}")
print("   Evento: survey")

test_questions = [
    {
        "id": "test_q1",
        "type": "likert_scale",
        "title": "Test Question - How satisfied are you?",
        "required": True,
        "config": {"scale": 5, "labels": {"1": "Very unsatisfied", "5": "Very satisfied"}},
    }
]

test_context = {"trigger_type": "learnpack_completed", "asset_slug": "test-learnpack", "test": True}

result = send_survey_event(
    user_id=user.id, survey_response_id=999, questions=test_questions, trigger_context=test_context  # ID de prueba
)

if result:
    print("   ✅ Evento enviado correctamente a Soketi")
    print()
    print("   📋 Para verificar que el evento llegó:")
    print(f"   1. En el frontend, suscríbete al canal: public-user-{user.id}")
    print("   2. Escucha el evento: 'survey'")
    print("   3. O revisa los logs de Heroku para confirmar")
else:
    print("   ❌ ERROR: No se pudo enviar el evento")
    print("   Revisa los logs para más detalles")
    sys.exit(1)

print()
print("=" * 60)
print("✅ VERIFICACIÓN COMPLETA")
print("=" * 60)
print()
print("Si ves este mensaje, Pusher está configurado correctamente.")
print("Los canales públicos están funcionando.")
print()
print("Próximos pasos:")
print("1. Verifica en los logs de Heroku que el evento se envió")
print("2. Si tienes frontend configurado, verifica que recibe el evento")
print("3. Prueba crear un Survey Configuration y trigger un survey real")
