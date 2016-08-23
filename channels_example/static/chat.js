$.fn.serializeObject = function() {
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name]) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};


$(function () {
    var i;
    var Socket = {
        ws: null,

        init: function () {
            var self = this;
            this.ws = new WebSocket(window.url);
            //this.ws = new SockJS("//localhost:8080/websocket");

            this.ws.onopen = function () {
                console.log('Socket opened');

                //self.ws.send(JSON.stringify({type: 'subscribe', user: window.user}));
            };

            this.ws.onclose = function () {
                console.log('Socket close');
                setTimeout(function(){
                    Socket.init();
                    socket = Socket.ws;
                    console.log('Reconnect...');
                }, 5000);
            };

            this.ws.onmessage = function (e) {
                var msg = JSON.parse(e.data);
                console.log(msg);
                if (msg.type == 'message') {
                    self.openForm(msg);
                    $('#' + msg.room).parent().find('.messages').prepend('<li>' + msg.message +'</li>');
                } else if (msg.type == 'active') {
                    for(i=0;i<msg.users.length; i+=1){
                        $('.users').find('li[data-pk="' + msg.users[i] + '"]').addClass('active');
                    }
                } else if (msg.type == 'inactive') {
                    for(i=0;i<msg.users.length; i+=1){
                        $('.users').find('li[data-pk="' + msg.users[i] + '"]').removeClass('active');
                    }
                } else if (msg.type == 'invite') {
                    self.openForm(msg);
                } else if (msg.type == 'unsubscribe') {
                    var users = '';
                    for(i=0;i<msg.users.length; i+=1) {
                        users += $('.users').find('li[data-pk="' + msg.users[i] + '"] a').text() + ', ';
                    }
                    $('#' + msg.room).parent().find('.messages').prepend('<li>Users ' + users + ' has been unsubscribe.</li>');
                    if (msg.users.indexOf(window.user) != -1) {
                        $('#' + msg.room).remove();
                    }
                }
            };

            this.openForm = function(msg){
                var $form = $('form#' + msg.room),
                    users = [];
                if(!$form.length) {
                    $form = $('.chat[hidden="hidden"]').clone().removeAttr('hidden');
                    $('.chats').append($form);
                    $form.find('form').attr('id', msg.room);
                    for(i=0;i<msg.users.length; i+=1) {
                        users.push($('.users').find('li[data-pk="' + msg.users[i] + '"] a').text());
                        $form.find('input[name="friends"][value="' + msg.users[i] + '"]').prop('checked', 'checked');
                    }
                    $form.find('span').text(users.join(', '));
                }
            }
        }
    };

    Socket.init();
    var socket = Socket.ws,
        data;


    $('body').on('submit', 'form', function(){
        data = $(this).serializeObject();
        data['type'] = 'message';
        data['room'] = $(this).attr('id');
        socket.send(JSON.stringify(data));
        $(this).find('[name="message"]').val('');
        return false;
    }).on('click', '.add-friends', function(){
        var users = $(this).parent().find('input[name="friends"]:checked').map(function(index, domElement) {
            return $(domElement).val();
        }).get();
        console.log(users);
        socket.send(JSON.stringify({type: 'invite', users: users,
            'room': $(this).parents('.chat').find('form').attr('id')}));
        return false;
    });

    $('.users').on('click', 'a', function(){
        socket.send(JSON.stringify({type: 'invite', users: [$(this).parent().attr('data-pk')]}));
        return false;
    });


});


