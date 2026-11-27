/**
 * @replay8004/client: ask the replay8004 validator to re-check an agent's claim on Celo, and read
 * the answer. The job bytes and requestHash match the Python validator byte for byte
 * (see tests/vectors/client.json in the repo, checked by both test suites).
 */
import {
  encodeFunctionData, keccak256, parseAbi, toBytes, type Address, type Hex, type PublicClient, type WalletClient,
} from "viem";

export const SCHEMA = "replay8004/job@1";

export const NETWORKS = {
  "celo-sepolia": { chainId: 11142220, validation: "0x8004Cb1BF31DAf7788923b405b754f57acEB4272" as Address,
                    identity: "0x8004A818BFB912233c491871b3d84c89A494BD9e" as Address },
  "celo-mainnet": { chainId: 42220, validation: "0x8004Cc8439f36fd5F9F049D9fF86523Df6dAAB58" as Address,
                    identity: "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432" as Address },
} as const;
export type NetworkName = keyof typeof NETWORKS;

export const KINDS = ["erc20_transfer", "erc20_balance", "contract_read", "x402_settlement"] as const;
export type Kind = (typeof KINDS)[number];
export const tagFor = (k: Kind) => `replay:${k}`;

export const VALIDATION_ABI = parseAbi([
  "function validationRequest(address validatorAddress, uint256 agentId, string requestURI, bytes32 requestHash)",
  "function getSummary(uint256 agentId, address[] validatorAddresses, string tag) view returns (uint64 count, uint8 avgResponse)",
  "function getValidationStatus(bytes32 requestHash) view returns (address validatorAddress, uint256 agentId, uint8 response, bytes32 responseHash, string tag, uint256 lastUpdate)",
]);

type Json = null | boolean | number | string | Json[] | { [k: string]: Json };

/** Same bytes as Python json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False). */
export function canonical(v: Json): string {
  if (v === null || typeof v !== "object") {
    if (typeof v === "number" && !Number.isSafeInteger(v)) throw new Error("use strings for non-integer or big numbers");
    return JSON.stringify(v);
  }
  if (Array.isArray(v)) return "[" + v.map(canonical).join(",") + "]";
  const keys = Object.keys(v).filter((k) => v[k] !== undefined).sort(byCodePoint);
  return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonical(v[k] as Json)).join(",") + "}";
}

function byCodePoint(a: string, b: string): number {
  const x = Array.from(a), y = Array.from(b);
  for (let i = 0; i < Math.min(x.length, y.length); i++) {
    const d = x[i].codePointAt(0)! - y[i].codePointAt(0)!;
    if (d) return d;
  }
  return x.length - y.length;
}

export interface Job { bytes: Uint8Array; text: string; requestHash: Hex; dataUri: string }

export function makeJob(agentId: number | bigint, chainId: number, kind: Kind, claim: { [k: string]: Json },
                        note = ""): Job {
  if (!KINDS.includes(kind)) throw new Error(`unknown kind ${kind}`);
  const text = canonical({ schema: SCHEMA, agentId: Number(agentId), chainId, kind, claim,
                           note: Array.from(note).slice(0, 500).join("") });
  const bytes = new TextEncoder().encode(text);
  if (bytes.length > 64 * 1024) throw new Error("job larger than 64 KB");
  return { bytes, text, requestHash: keccak256(bytes), dataUri: "data:application/json;base64," + Buffer.from(bytes).toString("base64") };
}

/** Claim for kind "x402_settlement": the PaymentRequirements you accepted + the server's settlement response. */
export function x402Claim(requirements: { [k: string]: Json }, settlement: { [k: string]: Json } | string,
                          opts: { minConfirmations?: number; authorizationNonce?: Hex; facilitator?: Address } = {}) {
  const st = typeof settlement === "string"
    ? JSON.parse(settlement.trim().startsWith("{") ? settlement : Buffer.from(settlement, "base64").toString("utf8"))
    : settlement;
  const c: { [k: string]: Json } = { requirements, settlement: st, minConfirmations: opts.minConfirmations ?? 2 };
  if (opts.authorizationNonce) c.authorizationNonce = opts.authorizationNonce;
  if (opts.facilitator) c.facilitator = opts.facilitator;
  return c;
}

export function requestCalldata(validator: Address, agentId: number | bigint, requestURI: string, requestHash: Hex): Hex {
  return encodeFunctionData({ abi: VALIDATION_ABI, functionName: "validationRequest",
                              args: [validator, BigInt(agentId), requestURI, requestHash] });
}

export function summaryCalldata(agentId: number | bigint, validators: Address[], tag: string): Hex {
  return encodeFunctionData({ abi: VALIDATION_ABI, functionName: "getSummary", args: [BigInt(agentId), validators, tag] });
}

/** Send validationRequest from the agent owner's (or operator's) wallet. Returns the tx hash. */
export async function requestValidation(wallet: WalletClient, p: {
  network: NetworkName; validator: Address; agentId: number | bigint; kind: Kind; claim: { [k: string]: Json };
  requestURI?: string; note?: string;
}): Promise<{ hash: Hex; requestHash: Hex; requestURI: string }> {
  const net = NETWORKS[p.network];
  const job = makeJob(p.agentId, net.chainId, p.kind, p.claim, p.note);
  const requestURI = p.requestURI ?? job.dataUri;
  if (!wallet.account) throw new Error("wallet client needs an account");
  if (wallet.chain && wallet.chain.id !== net.chainId) throw new Error(`wallet is on chain ${wallet.chain.id}, not ${net.chainId}`);
  const hash = await wallet.writeContract({ address: net.validation, abi: VALIDATION_ABI, functionName: "validationRequest",
    args: [p.validator, BigInt(p.agentId), requestURI, job.requestHash], account: wallet.account, chain: wallet.chain ?? null });
  return { hash, requestHash: job.requestHash, requestURI };
}

/** Read the on-chain result: how many answers this validator gave the agent for a tag, and their average score. */
export async function getSummary(client: PublicClient, network: NetworkName, agentId: number | bigint,
                                 validators: Address[], tag = ""): Promise<{ count: bigint; avgResponse: number }> {
  const [count, avgResponse] = await client.readContract({ address: NETWORKS[network].validation, abi: VALIDATION_ABI,
    functionName: "getSummary", args: [BigInt(agentId), validators, tag] });
  return { count, avgResponse };
}

/** Gate helper: true when the agent has at least `minCount` answers averaging >= `minScore`. */
export async function passes(client: PublicClient, network: NetworkName, agentId: number | bigint, validator: Address,
                             kind: Kind, minScore = 90, minCount = 1n): Promise<boolean> {
  const s = await getSummary(client, network, agentId, [validator], tagFor(kind));
  return s.count > 0n && s.count >= minCount && s.avgResponse >= minScore;  // no history never passes
}

/** Reason codes shared with contracts/ReplayGate.sol and replay8004/gate.py. */
export const REASON = { OK: 0, WRONG_VALIDATOR: 1, WRONG_AGENT: 2, NO_RESPONSE: 3, LOW_SCORE: 4, STALE: 5, WRONG_TAG: 6 } as const;

export interface ValidationStatus { validatorAddress: Address; agentId: bigint; response: number; responseHash: Hex; tag: string; lastUpdate: bigint }

/** Pure decision for one request, identical to ReplayGate.claimStatus. maxAge 0n = no limit; tag "" = any. */
export function decideClaim(s: ValidationStatus, p: { validator: Address; agentId: bigint; tag?: string; minScore?: number;
                            maxAge?: bigint; now: bigint }): { ok: boolean; reason: number } {
  const r = (reason: number) => ({ ok: reason === 0, reason });
  if (s.validatorAddress.toLowerCase() !== p.validator.toLowerCase()) return r(REASON.WRONG_VALIDATOR);
  if (s.agentId !== p.agentId) return r(REASON.WRONG_AGENT);
  if (BigInt(s.responseHash) === 0n) return r(REASON.NO_RESPONSE);
  if (p.tag && s.tag !== p.tag) return r(REASON.WRONG_TAG);
  if (s.response < (p.minScore ?? 100)) return r(REASON.LOW_SCORE);
  if ((p.maxAge ?? 0n) !== 0n && p.now > s.lastUpdate + (p.maxAge ?? 0n)) return r(REASON.STALE);
  return r(REASON.OK);
}

/** "Was this exact claim (e.g. an x402 payment) verified, recently, with a full score?" */
export async function claimStatus(client: PublicClient, network: NetworkName, requestHash: Hex, p: {
  validator: Address; agentId: bigint; tag?: string; minScore?: number; maxAge?: bigint; now?: bigint;
}) {
  const [validatorAddress, agentId, response, responseHash, tag, lastUpdate] = await client.readContract({
    address: NETWORKS[network].validation, abi: VALIDATION_ABI, functionName: "getValidationStatus", args: [requestHash] });
  const s: ValidationStatus = { validatorAddress, agentId, response, responseHash, tag, lastUpdate };
  return { ...decideClaim(s, { ...p, now: p.now ?? BigInt(Math.floor(Date.now() / 1000)) }), status: s };
}

export const _hashText = (t: string) => keccak256(toBytes(t));
