from threading import Thread
from flask import render_template, current_app
from flask_mail import Message
from app import mail

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipient, template, **kwargs):
    
    msg = Message(subject,sender=current_app.config['MAIL_USERNAME'], recipients=[recipient])
    msg.body = render_template(template + ".txt", **kwargs)
    msg.html = render_template(template + ".html", **kwargs)

    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()