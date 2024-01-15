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
const { spawnSync } = require('child_process');
const { exit } = require('node:process');
const { status } = spawnSync('go', ['run', `${__dirname}/main.go`], { stdio: 'inherit' });
exit(status);
