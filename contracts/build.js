// Compiles contracts with solc-js (npm "solc" 0.8.28) into contracts/out/*.json (abi + bytecode).
// usage: node contracts/build.js [path/to/node_modules/solc]
const fs = require("fs"), path = require("path");
const solc = require(process.argv[2] || "solc");
const dir = __dirname, files = ["ReplayGate.sol", "test/MockValidationRegistry.sol", "test/EscrowExample.sol"];
const sources = Object.fromEntries(files.map(f => [f, { content: fs.readFileSync(path.join(dir, f), "utf8") }]));
const input = { language: "Solidity", sources, settings: { optimizer: { enabled: true, runs: 200 }, evmVersion: "paris",
  outputSelection: { "*": { "*": ["abi", "evm.bytecode.object"] } } } };
const out = JSON.parse(solc.compile(JSON.stringify(input), { import: p => ({ contents: fs.readFileSync(path.join(dir, p), "utf8") }) }));
const errs = (out.errors || []).filter(e => e.severity === "error");
for (const e of out.errors || []) console.error(e.formattedMessage);
if (errs.length) process.exit(1);
fs.mkdirSync(path.join(dir, "out"), { recursive: true });
for (const [file, cs] of Object.entries(out.contracts))
  for (const [name, c] of Object.entries(cs))
    fs.writeFileSync(path.join(dir, "out", name + ".json"), JSON.stringify({ abi: c.abi, bytecode: "0x" + c.evm.bytecode.object, source: file }, null, 1));
console.log("compiled", solc.version(), Object.values(out.contracts).flatMap(Object.keys).join(", "));
