"use strict";

globalThis.require = require;
globalThis.fs = require("fs");
globalThis.TextEncoder = require("util").TextEncoder;
globalThis.TextDecoder = require("util").TextDecoder;
globalThis.performance ??= require("performance");
globalThis.crypto ??= require("crypto");

const { Go } = require("./wasm_exec");

const go = new Go();
go.env = process.env;
go.exit = process.exit;
WebAssembly.instantiate(fs.readFileSync(`${__dirname}/acceptance.wasm`), go.importObject).then((result) => {
	process.on("exit", (code) => { // Node.js exits if no event handler is pending
		if (code === 0 && !go.exited) {
			// deadlock, make Go print error and stack traces
			go._pendingEvent = { id: 0 };
			go._resume();
		}
	});
	return go.run(result.instance);
}).catch((err) => {
	console.error(err);
	process.exit(1);
});
