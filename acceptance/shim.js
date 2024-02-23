const version = 'v0.1.1';

const { createWriteStream, chmodSync } = require('fs');
const { createGunzip } = require('zlib');
const { basename } = require('path');
const { spawnSync } = require('child_process');
const { pipeline } = require('stream');
const { exit } = require('node:process');
const { promisify } = require('util');
const pipelineAsync = promisify(pipeline);

(async () => {
    const platform = process.platform == 'win32' ? 'windows' : process.platform;
    const arch = process.arch == 'x64' ? 'amd64' : process.arch;
    const artifact = `acceptance_${platform}_${arch}.gz`;
    const downloadUrl = `https://github.com/databrickslabs/sandbox/releases/download/acceptance/${version}/${artifact}`;
    const filename = basename(downloadUrl).split('.')[0];
    const dest = createWriteStream(filename);
    const response = await fetch(downloadUrl);
    if (!response.ok) {
        throw new Error(`Failed to download file (status ${response.status}): ${response.statusText}`);
    }   
    await pipelineAsync(response.body, createGunzip(), dest)
    chmodSync(filename, '755')
    const { status } = spawnSync(`${process.cwd()}/${filename}`, [], { stdio: 'inherit' });
    exit(status);
})();