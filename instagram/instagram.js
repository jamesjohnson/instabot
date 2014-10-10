var posts = []
var picture = "";

function getPosts() {
    var posts = document.querySelectorAll('div.timelineCenter');
    return Array.prototype.map.call(links, function(e) {
        return e
    });
}

var casper = require('casper').create({
        verbose: true,
        logLevel: 'debug'
});

function fillForm() {
    var form = $("iframe.hiFrame")[0].contentWindow.$("form")
    return form
}

casper.start('https://instagram.com/accounts/login/', function() {
    this.wait(5000, function() {
        this.page.switchToChildFrame(0);
        this.echo("called")
        this.evaluate(function(username, password) {
            document.querySelector("input[name='username']").value = username;
            document.querySelector("input[name='password']").value = password;
            document.querySelector("input[type='submit']").click();
        }, 'jamesjohnsona', 'homie4king');
    });
});



casper.run();
