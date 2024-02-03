import fs from "fs";

import Go from './wasm_exec_node.js'

const go = new Go();
const buf = fs.readFileSync('./acceptance.wasm');
const wasm = await WebAssembly.instantiate(new Uint8Array(buf), go.importObject);
go.run(wasm.instance)
