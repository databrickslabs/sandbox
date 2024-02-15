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
const { exec } = require('child_process');
const { createGunzip } = require('zlib');
const { pipeline } = require('stream');

const downloadUrl = 'https://github.com/databrickslabs/sandbox/releases/download/acceptance/v0.0.1/acceptance_linux_amd64.zip';
const zipFilePath = './acceptance_linux_amd64.zip';
const unzipDir = './unzipped';

// Function to download file
function downloadFile(url, dest) {
    const file = fs.createWriteStream(dest);
    const request = (url, resolve, reject) => {
        https.get(url, (response) => {
            if (response.statusCode >= 200 && response.statusCode < 300) {
                pipeline(response, file, (err) => {
                    if (err) {
                        reject(err);
                        return;
                    }
                    resolve();
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

function unzipFile(zipFilePath, targetDir) {
    return new Promise((resolve, reject) => {
        const fileStream = fs.createReadStream(zipFilePath);
        const targetStream = fs.createWriteStream(targetDir);
        fileStream.pipe(createGunzip()).pipe(targetStream)
    });
}

// Function to execute subprocess
function executeSubprocess(command) {
    return new Promise((resolve, reject) => {
        exec(command, (error, stdout, stderr) => {
            if (error) {
                reject(error);
                return;
            }
            console.log(stdout);
            console.error(stderr);
            resolve();
        });
    });
}

// Main function
async function main() {
    try {
        // Download the zip file
        await downloadFile(downloadUrl, zipFilePath);
        console.log('Zip file downloaded successfully.');

        // Unzip the file
        await unzipFile(zipFilePath, unzipDir);
        console.log('Zip file extracted successfully.');

        // Execute the extracted file as a subprocess
        const executablePath = `${unzipDir}/your_executable_file`; // Adjust this path accordingly
        await executeSubprocess(executablePath);
    } catch (error) {
        console.error('Error:', error);
    }
}

// Run the main function
main();


// const { spawnSync } = require('child_process');
// const { exit } = require('node:process');
// const { status } = spawnSync('go', ['run', `${__dirname}/main.go`], { stdio: 'inherit' });
// exit(status);
