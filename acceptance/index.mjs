import fs from "fs";

import Go from './wasm_exec_node.js'

const go = new Go();
const buf = fs.readFileSync(`/home/runner/work/_actions/databrickslabs/sandbox/go/wasm/acceptance/acceptance.wasm`);
// const buf = fs.readFileSync(`${__dirname}/acceptance.wasm`);
const wasm = await WebAssembly.instantiate(new Uint8Array(buf), go.importObject);
go.run(wasm.instance)
