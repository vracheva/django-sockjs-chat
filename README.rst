Inherit from sockjs_chat.main.BaseSockJSHandler, implement to methods:

    class SockJSHandler(BaseSockJSHandler):
        def save_message(self, message, users):
            pass

        def get_friends_list(self):
            return []

Add 'sockjs_chat' to INSTALLED_APPS
Add

    SOCKJS_PORT = 8080
    SOCKJS_CHANNEL = 'websocket'
    SOCKJS_CLASSES = (
        'app.sockets.SockJSHandler',
    )

to settings
