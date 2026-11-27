// Compiles the canonical ERC-8004 registries (vendored in ./src from erc-8004/erc-8004-contracts
// commit b9e466c250744a7e06b13dff9d3c2844ed64f825, SPDX MIT) with the settings that repo uses
// (solc 0.8.24, viaIR, optimizer 200, shanghai), so tests run against the real code, not a mock.
// setup: cd contracts/canonical && npm i --no-save solc@0.8.24 @openzeppelin/contracts@5.4.0 @openzeppelin/contracts-upgradeable@5.4.0
// usage: node contracts/canonical/build.js
const fs = require("fs"), path = require("path");
const dir = __dirname, nm = path.join(dir, "node_modules");
const solc = require(path.join(nm, "solc"));
const files = ["IdentityRegistryUpgradeable.sol", "ValidationRegistryUpgradeable.sol", "HardhatMinimalUUPS.sol", "ERC1967Proxy.sol"];
const sources = Object.fromEntries(files.map(f => [f, { content: fs.readFileSync(path.join(dir, "src", f), "utf8") }]));
const input = { language: "Solidity", sources, settings: { viaIR: true, optimizer: { enabled: true, runs: 200 },
  evmVersion: "shanghai", outputSelection: { "*": { "*": ["abi", "evm.bytecode.object"] } } } };
const findImports = p => {
  for (const base of [nm, path.join(dir, "src")]) {
    const f = path.join(base, p);
    if (fs.existsSync(f)) return { contents: fs.readFileSync(f, "utf8") };
  }
  return { error: "not found: " + p };
};
const out = JSON.parse(solc.compile(JSON.stringify(input), { import: findImports }));
const errs = (out.errors || []).filter(e => e.severity === "error");
for (const e of errs) console.error(e.formattedMessage);
if (errs.length) process.exit(1);
const want = new Set(["IdentityRegistryUpgradeable", "ValidationRegistryUpgradeable", "HardhatMinimalUUPS", "ERC1967Proxy"]);
const outDir = path.join(dir, "..", "out", "canonical");
fs.mkdirSync(outDir, { recursive: true });
for (const [file, cs] of Object.entries(out.contracts))
  for (const [name, c] of Object.entries(cs))
    if (want.has(name) && files.includes(file))
      fs.writeFileSync(path.join(outDir, name + ".json"), JSON.stringify({ abi: c.abi, bytecode: "0x" + c.evm.bytecode.object, source: file }));
console.log("compiled canonical", solc.version(), [...want].join(", "));
