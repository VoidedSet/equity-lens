import crypto from "crypto";

export interface S3PresignOptions {
  bucket?: string;
  region?: string;
  accessKeyId?: string;
  secretAccessKey?: string;
  sessionToken?: string;
  expiresIn?: number;
}

function hmacSha256(key: string | Buffer, data: string): Buffer {
  return crypto.createHmac("sha256", key).update(data, "utf8").digest();
}

function sha256Hex(data: string): string {
  return crypto.createHash("sha256").update(data, "utf8").digest("hex");
}

function encodeRfc3986(value: string): string {
  return encodeURIComponent(value).replace(/[!'()*]/g, (c) =>
    `%${c.charCodeAt(0).toString(16).toUpperCase()}`
  );
}

function encodeS3Key(key: string): string {
  return key
    .replace(/^\/+/, "")
    .split("/")
    .map((segment) => encodeRfc3986(segment))
    .join("/");
}

export function isS3Configured(): boolean {
  return Boolean(
    process.env.S3_BUCKET &&
      process.env.AWS_ACCESS_KEY_ID &&
      process.env.AWS_SECRET_ACCESS_KEY
  );
}

export function presignS3GetUrl(key: string, opts: S3PresignOptions = {}): string {
  const bucket = opts.bucket ?? process.env.S3_BUCKET;
  const region = opts.region ?? process.env.AWS_REGION ?? "ap-south-1";
  const accessKeyId = opts.accessKeyId ?? process.env.AWS_ACCESS_KEY_ID;
  const secretAccessKey = opts.secretAccessKey ?? process.env.AWS_SECRET_ACCESS_KEY;
  const sessionToken = opts.sessionToken ?? process.env.AWS_SESSION_TOKEN;
  const expiresIn = Math.max(1, Math.min(604800, opts.expiresIn ?? 900));

  if (!bucket || !accessKeyId || !secretAccessKey) {
    throw new Error("S3_BUCKET, AWS_ACCESS_KEY_ID, and AWS_SECRET_ACCESS_KEY are required for S3 presigning");
  }

  const now = new Date();
  const iso = now.toISOString().replace(/[:-]|\.\d{3}/g, "");
  const amzDate = iso;
  const dateStamp = iso.slice(0, 8);
  const credentialScope = `${dateStamp}/${region}/s3/aws4_request`;
  const host = `${bucket}.s3.${region}.amazonaws.com`;
  const canonicalUri = `/${encodeS3Key(key)}`;

  const queryParams: Array<[string, string]> = [
    ["X-Amz-Algorithm", "AWS4-HMAC-SHA256"],
    ["X-Amz-Credential", `${accessKeyId}/${credentialScope}`],
    ["X-Amz-Date", amzDate],
    ["X-Amz-Expires", String(expiresIn)],
    ["X-Amz-SignedHeaders", "host"],
  ];
  if (sessionToken) {
    queryParams.push(["X-Amz-Security-Token", sessionToken]);
  }
  queryParams.sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));

  const canonicalQuery = queryParams
    .map(([k, v]) => `${encodeRfc3986(k)}=${encodeRfc3986(v)}`)
    .join("&");

  const canonicalRequest = [
    "GET",
    canonicalUri,
    canonicalQuery,
    `host:${host}\n`,
    "host",
    "UNSIGNED-PAYLOAD",
  ].join("\n");

  const stringToSign = [
    "AWS4-HMAC-SHA256",
    amzDate,
    credentialScope,
    sha256Hex(canonicalRequest),
  ].join("\n");

  const kDate = hmacSha256(`AWS4${secretAccessKey}`, dateStamp);
  const kRegion = hmacSha256(kDate, region);
  const kService = hmacSha256(kRegion, "s3");
  const kSigning = hmacSha256(kService, "aws4_request");
  const signature = hmacSha256(kSigning, stringToSign).toString("hex");

  return `https://${host}${canonicalUri}?${canonicalQuery}&X-Amz-Signature=${signature}`;
}
