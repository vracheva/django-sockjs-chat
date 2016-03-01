Getting started
---------------

Inherit from `sockjs_chat.main.BaseSockJSHandler`, implement to methods:

```
    class SockJSHandler(BaseSockJSHandler):
        def save_message(self, message, users):
            pass

        def get_friends_list(self):
            return []
```

Add `'sockjs_chat'` to INSTALLED_APPS

Django command for running tornado [django-sockjs-tornado](https://github.com/peterbe/django-sockjs-tornado)

Add to settings

```
    SOCKJS_PORT = 8080
    SOCKJS_CHANNEL = 'websocket'
    SOCKJS_CLASSES = (
        'app.sockets.SockJSHandler',
    )
```

For running tornado `./manage.py socketserver`

A simple app might look like this:

```
    $(function () {
        var i;
        var Socket = {
            ws: null,

            init: function () {
                this.ws = new SockJS("//localhost:8080/websocket");

                this.ws.onopen = function () {
                    console.log('Socket opened');
                    self.ws.send(JSON.stringify({type: 'subscribe', user: window.user}));
                };

                this.ws.onclose = function () {
                    console.log('Socket close');
                };

                this.ws.onmessage = function (e) {
                    var msg = JSON.parse(e.data);
                    if (msg.type == 'message') {
                        console.log('New message: ' + msg.message);
                    } else if (msg.type == 'active') {
                        console.log('User now online: ' + msg.users);
                    } else if (msg.type == 'inactive') {
                        console.log('User now offline: ' + msg.users);
                    } else if (msg.type == 'invite') {
                        console.log('Invite to chart ' + msg.room + ' with users: ' + msg.users);
                    }
                };
            }
        };

        Socket.init();
        var socket = Socket.ws

        $('form').submit(function(){
            socket.send(JSON.stringify(data));
        });

        $('button.create-chat-with-user').click(function(){
            socket.send(JSON.stringify({type: 'invite', users: users}));
        });

        $('button.add-friends-to-chat').click(function(){
            socket.send(JSON.stringify({type: 'invite', users: users, 'room': chatId}));
        });

    });
```
