from channels.auth import channel_session_user_from_http, channel_session_user, http_session_user
from channels.sessions import channel_session
from django.http import HttpResponse
from channels.handler import AsgiHandler


def http_consumer(message):
    # Make standard HTTP response - access ASGI path attribute directly
    response = HttpResponse("Hello world! You asked for %s" % message.content['path'])
    # Encode that response into message format (ASGI)
    for chunk in AsgiHandler.encode_response(response):
        message.reply_channel.send(chunk)


from channels import Group


def ws_message(message):
    # ASGI WebSocket packet-received and send-packet message types
    # both have a "text" key for their textual data.
    Group('chat').send({
        "text": "{}".format(message.content['text']),
    })


# Connected to websocket.connect
@channel_session_user_from_http
@channel_session
def ws_add(message):
    print(message.user)
    room = message.content['path'].strip("/")
    print(room)
    Group("chat").add(message.reply_channel)


# Connected to websocket.disconnect
def ws_disconnect(message):
    Group("chat").discard(message.reply_channel)
