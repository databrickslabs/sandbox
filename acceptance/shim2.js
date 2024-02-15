url = 'https://github.com/databrickslabs/sandbox/releases/download/acceptance/v0.0.1/acceptance_linux_amd64.zip'

var zlib = require('zlib');
var https = require('https');
var fs = require('fs');
var request = https.get({
  followRedirect: true,
    host: 'github.com',
    path: '/databrickslabs/sandbox/releases/download/acceptance/v0.0.1/acceptance_linux_amd64.zip',
    port: 443,
    headers: {
        'accept-encoding': 'gzip,deflate'
    }
});
request.on('response', function(response) {
  console.log('xx', response.headers)
    switch (response.headers['content-encoding']) {
        // or, just use zlib.createUnzip() to handle both cases
        case 'gzip':

            console.log("gzip");
            response.pipe(zlib.createGunzip()).pipe(res);
            break;
        case 'deflate':
            response.pipe(zlib.createInflate()).pipe(res);
            break;
        default:
            response.pipe(res);
            break;
    }
});