import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export interface PiRuntimeManifest {
  readonly runtime_version: string;
  readonly protocol_version: "1";
  readonly contract_digest: string;
  readonly capability_digest: string;
  readonly prompt_digest: string;
  readonly skill_digest: string;
}

let cached: PiRuntimeManifest | undefined;

export function loadRuntimeManifest(): PiRuntimeManifest {
  if (cached) return cached;
  const path = resolve(
    dirname(fileURLToPath(import.meta.url)),
    "generated/runtime-manifest.json",
  );
  const value: unknown = JSON.parse(readFileSync(path, "utf8"));
  if (!validManifest(value)) throw new Error("agent_runtime_manifest_invalid");
  cached = Object.freeze(value);
  return cached;
}

function validManifest(value: unknown): value is PiRuntimeManifest {
  if (!value || typeof value !== "object") return false;
  const manifest = value as Partial<PiRuntimeManifest>;
  return (
    manifest.protocol_version === "1" &&
    typeof manifest.runtime_version === "string" &&
    validDigest(manifest.contract_digest) &&
    validDigest(manifest.capability_digest) &&
    validDigest(manifest.prompt_digest) &&
    validDigest(manifest.skill_digest)
  );
}

function validDigest(value: unknown): value is string {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}
