// function chooseBinary() {
//     // ...
//     if (platform === 'linux' && arch === 'x64') {
//         return `main-linux-amd64-${VERSION}`
//     }
//     // ...
// }

// const binary = chooseBinary()
// const mainScript = `${__dirname}/${binary}`

const { spawnSync } = require('child_process');

spawnSync('go', ['main.go'], { stdio: 'inherit' });
