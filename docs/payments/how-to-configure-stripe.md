# Configure Stripe for Academy

Step-by-step guide on how to set up the necessary Stripe credentials so that an academy can have its own Stripe payment method.

## EN:

1. Access the admin at https://breathecode.herokuapp.com/admin/payments/academypaymentsettings and, if an `Academy Payment Settings` does not exist for the academy in question, create a new one

2. Assign the academy

3. Go to [Stripe](https://stripe.com) and sign in or create an account (make sure you are not in a test environment, normally a notice appears at the top indicating that you are)

4. In the Home tab, copy the secret key and paste it into the `Stripe api key` field in the admin

5. Also copy the publishable key and paste it into the `Stripe publishable key` field

6. Sign in or create an account on [Postman](https://postman.com) and then enter [this collection](https://www.postman.com/joint-operations-participant-13247951/workspace/e96d8c39-187a-4960-b8d1-2ab873f1bea0/collection/39523424-d4fd519f-93fb-4fd5-9866-58f742258f4b?action=share&source=copy-link&creator=39523424)

7. Enter the ***Create webhook endpoint*** request, go to the ***Authorization*** tab, and in the `Token` field, insert the Stripe secret key, then click Send

8. Return to Stripe and in the dashboard click on ***Developers*** in the lower left, then on ***Webhooks***. Upon refreshing, the created webhook will appear, enter it

9. Copy the key in the ***Signing secret*** section on the right side, return to the admin and paste it into the `Stripe webhook secret` field

10. Save, and the academy configuration will have been created

## ES:

1. Acceder al admin en https://breathecode.herokuapp.com/admin/payments/academypaymentsettings y, en caso de que no exista un `Academy Payment Settings` con la academia en cuestión, crear uno nuevo

2. Asignar la academia

3. Ir a [Stripe](https://stripe.com) e iniciar sesión o crear una cuenta (asegúrate de no estar en un entorno de prueba, normalmente aparece un aviso en la parte superior indicando que lo estás)

4. En la pestaña Inicio, copiar la clave secreta y pegarla en el campo `Stripe api key` del admin

5. Copiar también la clave publicable y pegarla en el campo `Stripe publishable key`

6. Iniciar sesión o crearse una cuenta en [Postman](https://postman.com) y luego entrar a [esta colección](https://www.postman.com/joint-operations-participant-13247951/workspace/e96d8c39-187a-4960-b8d1-2ab873f1bea0/collection/39523424-d4fd519f-93fb-4fd5-9866-58f742258f4b?action=share&source=copy-link&creator=39523424)

7. Entrar en la request ***Create webhook endpoint***, ir a la pestaña ***Authorization***, y en el campo `Token`, insertar la clave secreta de Stripe, luego hacer click en Send

8. Volver a Stripe y en el dashboard hacer click en ***Desarrolladores*** en la parte inferior izquierda, luego en ***Webhooks***. Al resfrescar aparecerá el webhook creado, entrar en él

9. Copiar la clave en la sección ***Clave secreta de firma*** del lado derecho, volver al admin y pegarla en el campo `Stripe webhook secret`

10. Guardar, y la configuración de la academia se habrá creado
