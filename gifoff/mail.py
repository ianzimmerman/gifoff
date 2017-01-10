import threading
from flask import copy_current_request_context, current_app
from flask_mail import Mail

mail = Mail()

def send_async_email(msg):

    @copy_current_request_context
    def send_message(message):
        mail.send(message)

    sender = threading.Thread(name='mail_sender', target=send_message, args=(msg,))
    sender.start()