// function chooseBinary() {
//     // ...
//     if (platform === 'linux' && arch === 'x64') {
//         return `main-linux-amd64-${VERSION}`
//     }
//     // ...
// }
// const binary = chooseBinary()
// const mainScript = `${__dirname}/${binary}`
// TODO: try calling the result of GOOS=js GOARCH=wasm go build -o acceptance.wasm
console.log('env', process.env)

const https = require('https');
const fs = require('fs');
const { createGunzip } = require('zlib');
const { basename } = require('path');
const { spawnSync } = require('child_process');
const { pipeline } = require('stream');
const { exit } = require('node:process');


// Function to download file
function downloadFile(url) {
    const filename = basename(url).split('.')[0]
    const dest = fs.createWriteStream(filename);
    const request = (url, resolve, reject) => {
        https.get(url, (response) => {
            if (response.statusCode >= 200 && response.statusCode < 300) {
                pipeline(response, createGunzip(), dest, (err) => {
                    if (err) {
                        reject(err);
                        return;
                    }
                    resolve(filename);
                });
            } else if (response.headers.location) {
                request(response.headers.location, resolve, reject);
            } else {
                reject(new Error(`Failed to get '${url}' (${response.statusCode})`));
            }
        }).on('error', (err) => {
            reject(err);
        });
    }
    return new Promise((resolve, reject) => {
        request(url, resolve, reject);
    });
}

async function main() {
    const version = 'v0.0.1'
    const platform = process.platform == 'win32' ? 'windows' : process.platform;
    const arch = process.arch == 'x64' ? 'amd64' : process.arch;
    const artifact = `acceptance_${platform}_${arch}.gz`;
    const downloadUrl = `https://github.com/databrickslabs/sandbox/releases/download/acceptance/${version}/${artifact}`;
    const binary = await downloadFile(downloadUrl);
    fs.chmodSync(binary, '755')
    const { status } = spawnSync(binary, [], { stdio: 'inherit' });
    exit(status);
}

main();


// const { spawnSync } = require('child_process');
// const { exit } = require('node:process');
// const { status } = spawnSync('go', ['run', `${__dirname}/main.go`], { stdio: 'inherit' });
// exit(status);
