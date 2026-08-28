#!/usr/bin/env node
"use strict";

/*
 * Static OpenAPI generator for this repository.
 *
 * Usage:
 *   node app/scripts/openapi.js > openapi.json
 *   node app/scripts/openapi.js --summary
 *   node app/scripts/openapi.js --routes
 *
 * The chatbot service is Flask, so it does not expose /openapi.json by itself.
 * This file scans the backend route source files and relevant markdown docs,
 * then builds an OpenAPI 3.1 document with source references for inspection.
 */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");

const SERVER_BY_SERVICE = {
  chatbot: {
    url: "http://127.0.0.1:5000",
    description: "Chatbot Flask service",
  },
  rag: {
    url: "http://127.0.0.1:8000",
    description: "RAG FastAPI service",
  },
  clip: {
    url: "http://127.0.0.1:8200",
    description: "CLIP embedding FastAPI sidecar",
  },
};

const BODY_METHODS = new Set(["post", "put", "patch", "delete"]);
const ROUTER_METHODS = new Set([
  "get",
  "post",
  "put",
  "delete",
  "patch",
  "head",
  "options",
]);

function exists(filePath) {
  try {
    return fs.existsSync(filePath);
  } catch {
    return false;
  }
}

function readText(filePath) {
  return fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, "");
}

function toPosix(filePath) {
  return filePath.replace(/\\/g, "/");
}

function rel(filePath) {
  return toPosix(path.relative(ROOT, filePath));
}

function walkFiles(dir, predicate) {
  if (!exists(dir)) return [];
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (
        entry.name === "__pycache__" ||
        entry.name === ".git" ||
        entry.name === "node_modules" ||
        entry.name === ".venv" ||
        entry.name === "venv" ||
        entry.name === "venv-core" ||
        entry.name === "venv-image"
      ) {
        continue;
      }
      out.push(...walkFiles(full, predicate));
    } else if (!predicate || predicate(full)) {
      out.push(full);
    }
  }
  return out;
}

function backendFiles() {
  const files = [
    path.join(ROOT, "services/chatbot/chatbot_main.py"),
    path.join(ROOT, "services/clip-embed/server.py"),
  ];

  files.push(
    ...walkFiles(path.join(ROOT, "services/chatbot/routes"), (file) =>
      file.endsWith(".py") && !file.endsWith("__init__.py")
    )
  );

  return [...new Set(files.filter(exists))].sort();
}

function docFiles() {
  const roots = [
    path.join(ROOT, "README.md"),
    path.join(ROOT, "app/docs"),
    path.join(ROOT, "services/chatbot/docs"),
    path.join(ROOT, "services/mcp-server/docs"),
    path.join(ROOT, ".claude/skills"),
  ];

  const files = [];
  for (const root of roots) {
    if (!exists(root)) continue;
    const stat = fs.statSync(root);
    if (stat.isFile() && root.toLowerCase().endsWith(".md")) {
      files.push(root);
    } else if (stat.isDirectory()) {
      files.push(
        ...walkFiles(root, (file) => file.toLowerCase().endsWith(".md"))
      );
    }
  }
  return [...new Set(files)].sort();
}

function countChar(text, char) {
  let count = 0;
  for (const ch of text) {
    if (ch === char) count += 1;
  }
  return count;
}

function parseStringLiteral(text) {
  const match = text.match(/(["'])(.*?)\1/s);
  return match ? match[2] : "";
}

function parseStringList(text) {
  const out = [];
  const re = /(["'])(.*?)\1/g;
  let match;
  while ((match = re.exec(text))) out.push(match[2]);
  return out;
}

function parseLocalRouters(text, sourceFile) {
  const routers = {};
  const patterns = [
    {
      kind: "flask-blueprint",
      re: /([A-Za-z_]\w*)\s*=\s*Blueprint\s*\(([\s\S]*?)\)/g,
    },
    {
      kind: "fastapi-router",
      re: /([A-Za-z_]\w*)\s*=\s*APIRouter\s*\(([\s\S]*?)\)/g,
    },
  ];

  for (const pattern of patterns) {
    let match;
    while ((match = pattern.re.exec(text))) {
      const variable = match[1];
      const args = match[2];
      const prefixMatch = args.match(/(?:url_prefix|prefix)\s*=\s*(["'])(.*?)\1/s);
      const tagsMatch = args.match(/tags\s*=\s*\[([\s\S]*?)\]/s);
      routers[variable] = {
        variable,
        kind: pattern.kind,
        file: sourceFile,
        name: parseStringLiteral(args) || variable,
        prefix: prefixMatch ? prefixMatch[2] : "",
        tags: tagsMatch ? parseStringList(tagsMatch[1]) : [],
      };
    }
  }
  return routers;
}

function parseRegistrationPrefixes() {
  const mainFile = path.join(ROOT, "services/chatbot/chatbot_main.py");
  if (!exists(mainFile)) return {};
  const text = readText(mainFile);
  const prefixes = {};
  const re = /register_blueprint\s*\(\s*([A-Za-z_]\w*)([\s\S]*?)\)/g;
  let match;
  while ((match = re.exec(text))) {
    const variable = match[1];
    const args = match[2];
    const prefixMatch = args.match(/url_prefix\s*=\s*(["'])(.*?)\1/s);
    prefixes[variable] = prefixMatch ? prefixMatch[2] : "";
  }
  return prefixes;
}

function collectDecorator(lines, startIndex) {
  const collected = [];
  let balance = 0;
  let index = startIndex;

  while (index < lines.length) {
    const line = lines[index];
    collected.push(line);
    balance += countChar(line, "(") - countChar(line, ")");
    index += 1;
    if (balance <= 0) break;
  }

  return {
    text: collected.join("\n"),
    nextIndex: index,
  };
}

function collectFunctionSource(lines, startIndex) {
  let end = startIndex + 1;
  while (end < lines.length) {
    const line = lines[end];
    if (/^(def|async\s+def)\s+[A-Za-z_]\w*\s*\(/.test(line)) break;
    if (/^@[A-Za-z_]\w*\./.test(line)) break;
    end += 1;
  }
  return lines.slice(startIndex, end).join("\n");
}

function parseDecoratorRoute(decoratorText) {
  const header = decoratorText.trimStart();
  const match = header.match(
    /^@([A-Za-z_]\w*)\.(route|get|post|put|delete|patch|head|options)\s*\(/s
  );
  if (!match) return null;

  const owner = match[1];
  const decoratorMethod = match[2].toLowerCase();
  const pathPart = decoratorText.slice(decoratorText.indexOf("(") + 1);
  const rawPath = parseStringLiteral(pathPart);
  if (rawPath === "" && !/["']{2}/.test(pathPart)) return null;

  let methods;
  if (decoratorMethod === "route") {
    const methodMatch = decoratorText.match(/methods\s*=\s*\[([\s\S]*?)\]/s);
    methods = methodMatch ? parseStringList(methodMatch[1]) : ["GET"];
  } else {
    methods = [decoratorMethod.toUpperCase()];
  }

  const statusMatch = decoratorText.match(/status_code\s*=\s*(\d+)/);

  return {
    owner,
    decoratorMethod,
    rawPath,
    methods: methods.map((method) => method.toUpperCase()),
    statusCode: statusMatch ? Number(statusMatch[1]) : undefined,
    decorator: decoratorText,
  };
}

function extractRoutesFromFile(filePath, localRouters) {
  const text = readText(filePath);
  const lines = text.split(/\r?\n/);
  const sourceFile = rel(filePath);
  const routes = [];
  const pendingDecorators = [];

  for (let i = 0; i < lines.length; ) {
    const trimmed = lines[i].trimStart();

    if (trimmed.startsWith("@")) {
      const collected = collectDecorator(lines, i);
      pendingDecorators.push({ text: collected.text, line: i + 1 });
      i = collected.nextIndex;
      continue;
    }

    const defMatch = trimmed.match(/^(?:async\s+def|def)\s+([A-Za-z_]\w*)\s*\(/);
    if (defMatch && pendingDecorators.length) {
      const handler = defMatch[1];
      const functionSource = collectFunctionSource(
        lines,
        Math.max(0, pendingDecorators[0].line - 1)
      );

      for (const pending of pendingDecorators) {
        const parsed = parseDecoratorRoute(pending.text);
        if (!parsed) continue;
        const router = localRouters[parsed.owner] || {};
        const kind =
          router.kind === "fastapi-router" || parsed.decoratorMethod !== "route"
            ? "fastapi"
            : "flask";

        routes.push({
          kind,
          owner: parsed.owner,
          rawPath: parsed.rawPath,
          methods: parsed.methods,
          statusCode: parsed.statusCode,
          handler,
          file: sourceFile,
          line: i + 1,
          decoratorLine: pending.line,
          router,
          functionSource,
        });
      }
      pendingDecorators.length = 0;
    } else if (trimmed && !trimmed.startsWith("#")) {
      pendingDecorators.length = 0;
    }

    i += 1;
  }

  return routes;
}

function joinPaths(prefix, routePath) {
  const left = prefix || "";
  const right = routePath || "";
  if (!left) return right || "/";
  if (!right) return left || "/";
  if (right === "/") return left.endsWith("/") ? left : `${left}/`;
  return `${left.replace(/\/+$/, "")}/${right.replace(/^\/+/, "")}`.replace(
    /\/+/g,
    "/"
  );
}

function toOpenApiPath(routePath) {
  return routePath.replace(/<(?:(?:[^:<>]+):)?([^<>]+)>/g, "{$1}");
}

function includePrefixFor(file) {
  return "";
}

function serviceFor(file) {
  if (file.startsWith("services/clip-embed/")) return "clip";
  return "chatbot";
}

function finalizeRoute(route, registrationPrefixes) {
  let prefix = route.router && route.router.prefix ? route.router.prefix : "";
  if (route.kind === "flask") {
    const registered = registrationPrefixes[route.owner];
    if (registered) prefix = joinPaths(registered, prefix);
  } else if (route.kind === "fastapi") {
    prefix = joinPaths(includePrefixFor(route.file), prefix);
  }

  const fullPath = joinPaths(prefix, route.rawPath);
  return {
    ...route,
    service: serviceFor(route.file),
    fullPath,
    openapiPath: toOpenApiPath(fullPath),
  };
}

function titleCase(text) {
  return text
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function inferTag(route) {
  const p = route.openapiPath;
  if (route.service === "rag") return p.includes("/documents") ? "RAG Documents" : p.includes("/query") ? "RAG Query" : "RAG Health";
  if (route.service === "clip") return p.startsWith("/embed") ? "CLIP Embeddings" : "CLIP Health";
  if (p.startsWith("/chat/stream")) return "Chat Streaming";
  if (p.startsWith("/chat/async")) return "Async Chat";
  if (p.startsWith("/api/image-gen")) return "Image Generation";
  if (p.startsWith("/api/video")) return "Video";
  if (p.startsWith("/api/anime-pipeline")) return "Anime Pipeline";
  if (p.startsWith("/api/reasoning-image-gen")) return "Reasoning Image Gen";
  if (p.startsWith("/api/sd") || p.startsWith("/sd-api") || p.includes("img2img") || p.includes("generate-image")) return "Stable Diffusion";
  if (p.startsWith("/api/mcp")) return "MCP";
  if (p.startsWith("/memory") || p.startsWith("/api/memory")) return "Memory";
  if (p.includes("conversation")) return "Conversations";
  if (p.startsWith("/api/models")) return "Models";
  if (p.startsWith("/api/skills")) return "Skills";
  if (p.startsWith("/api/characters") || p.startsWith("/api/character-select") || p.startsWith("/api/local-image-gen")) return "Characters";
  if (p.startsWith("/api/jobs")) return "Jobs";
  if (p.startsWith("/api/gallery") || p.startsWith("/storage/images") || p.startsWith("/api/list-images") || p.startsWith("/api/save-image")) return "Images";
  if (p.startsWith("/api/auth") || p === "/login") return "Auth";
  if (p.startsWith("/api/v1")) return "External API";
  if (p.includes("health")) return "Health";
  return "Chatbot";
}

function operationIdFor(method, route) {
  const id = `${route.service}_${method}_${route.openapiPath}_${route.handler}`
    .replace(/[{}]/g, "")
    .replace(/[^A-Za-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
  return id || `${route.service}_${method}_${route.handler}`;
}

function extractDocstring(functionSource) {
  const match = functionSource.match(
    /(?:async\s+def|def)\s+[A-Za-z_]\w*\s*\([\s\S]*?\):\s*(?:\r?\n)\s*(["']{3})([\s\S]*?)\1/
  );
  return match ? match[2].trim().replace(/\s+/g, " ") : "";
}

function extractRouteDocsFromMarkdown(files) {
  const summaries = new Map();
  const rowRe = /^\|\s*`?([A-Z, /]+)`?\s*\|\s*`?([^`|]+)`?\s*\|\s*([^|]+?)\s*\|/;

  for (const file of files) {
    let text;
    try {
      text = readText(file);
    } catch {
      continue;
    }

    for (const line of text.split(/\r?\n/)) {
      const match = line.match(rowRe);
      if (!match) continue;
      const methods = match[1]
        .split(/[,\s/]+/)
        .map((item) => item.trim().toUpperCase())
        .filter((item) => /^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$/.test(item));
      if (!methods.length) continue;

      const routePath = toOpenApiPath(match[2].trim());
      const summary = match[3].replace(/`/g, "").trim();
      if (!routePath.startsWith("/")) continue;

      for (const method of methods) {
        const key = `${method.toLowerCase()} ${routePath}`;
        if (!summaries.has(key)) {
          summaries.set(key, {
            summary,
            file: rel(file),
          });
        }
      }
    }
  }

  return summaries;
}

function extractPathParameters(openapiPath) {
  const params = [];
  const seen = new Set();
  const re = /{([^}]+)}/g;
  let match;
  while ((match = re.exec(openapiPath))) {
    const name = match[1];
    if (seen.has(name)) continue;
    seen.add(name);
    params.push({
      name,
      in: "path",
      required: true,
      schema: { type: "string" },
    });
  }
  return params;
}

function addUniqueParam(params, param) {
  if (!param.name) return;
  const key = `${param.in}:${param.name}`;
  if (params.some((item) => `${item.in}:${item.name}` === key)) return;
  params.push(param);
}

function extractRequestDetails(route) {
  const src = route.functionSource || "";
  const params = extractPathParameters(route.openapiPath);
  const jsonFields = new Set();
  const formFields = new Set();
  const fileFields = new Set();

  const queryPatterns = [
    /request\.args\.get(?:list)?\(\s*(["'])(.*?)\1/g,
    /request\.values\.get(?:list)?\(\s*(["'])(.*?)\1/g,
  ];
  for (const pattern of queryPatterns) {
    let match;
    while ((match = pattern.exec(src))) {
      addUniqueParam(params, {
        name: match[2],
        in: "query",
        required: false,
        schema: { type: "string" },
      });
    }
  }

  const headerRe = /([A-Za-z_]\w*)\s*:\s*[^=,\n]+=\s*Header\s*\(/g;
  let headerMatch;
  while ((headerMatch = headerRe.exec(src))) {
    addUniqueParam(params, {
      name: headerMatch[1].replace(/_/g, "-"),
      in: "header",
      required: true,
      schema: { type: "string" },
    });
  }

  const jsonPatterns = [
    /(?:data|payload|body|request_json)\.get\(\s*(["'])(.*?)\1/g,
    /request\.json\[['"]([^'"]+)['"]\]/g,
  ];
  for (const pattern of jsonPatterns) {
    let match;
    while ((match = pattern.exec(src))) jsonFields.add(match[2] || match[1]);
  }

  const formRe = /request\.form\.get\(\s*(["'])(.*?)\1/g;
  let formMatch;
  while ((formMatch = formRe.exec(src))) formFields.add(formMatch[2]);

  const filesRe = /request\.files(?:\.get)?\(\s*(["'])(.*?)\1|request\.files\[['"]([^'"]+)['"]\]/g;
  let filesMatch;
  while ((filesMatch = filesRe.exec(src))) fileFields.add(filesMatch[2] || filesMatch[3]);

  const fastApiFormRe = /([A-Za-z_]\w*)\s*:\s*[^=,\n]+=\s*Form\s*\(/g;
  while ((formMatch = fastApiFormRe.exec(src))) formFields.add(formMatch[1]);

  const fastApiFileRe = /([A-Za-z_]\w*)\s*:\s*(?:UploadFile|[^=,\n]*UploadFile)/g;
  let fileMatch;
  while ((fileMatch = fastApiFileRe.exec(src))) fileFields.add(fileMatch[1]);

  const bodyModelMatch = src.match(/\n\s*(body|req|request_body)\s*:\s*([A-Za-z_]\w*)/);

  return {
    parameters: params,
    jsonFields: [...jsonFields].sort(),
    formFields: [...formFields].sort(),
    fileFields: [...fileFields].sort(),
    bodyModel: bodyModelMatch ? bodyModelMatch[2] : undefined,
  };
}

function schemaForFields(fields, fileFields) {
  const properties = {};
  const required = [];

  for (const name of fields) {
    properties[name] = { type: "string" };
  }
  for (const name of fileFields) {
    properties[name] = { type: "string", format: "binary" };
    required.push(name);
  }

  return {
    type: "object",
    additionalProperties: true,
    properties,
    ...(required.length ? { required } : {}),
  };
}

function responseContentFor(route) {
  const p = route.openapiPath;
  if (p.includes("/stream")) {
    return {
      "text/event-stream": {
        schema: { type: "string", description: "Server-Sent Events stream" },
      },
    };
  }
  if (
    p.includes("/download/") ||
    p.includes("/file/") ||
    p.includes("/thumbnail") ||
    p.includes("/images/{") ||
    p.startsWith("/storage/images/") ||
    p.startsWith("/static/")
  ) {
    return {
      "application/octet-stream": {
        schema: { type: "string", format: "binary" },
      },
    };
  }
  return {
    "application/json": {
      schema: { $ref: "#/components/schemas/AnyJson" },
    },
  };
}

function requestBodyFor(method, route, details) {
  const lower = method.toLowerCase();
  if (!BODY_METHODS.has(lower)) return undefined;

  if (details.fileFields.length || details.formFields.length) {
    return {
      required: details.fileFields.length > 0,
      content: {
        "multipart/form-data": {
          schema: schemaForFields(details.formFields, details.fileFields),
        },
      },
    };
  }

  if (details.bodyModel) {
    return {
      required: true,
      content: {
        "application/json": {
          schema: {
            allOf: [{ $ref: "#/components/schemas/AnyJson" }],
            description: `Body model in source: ${details.bodyModel}`,
          },
        },
      },
    };
  }

  return {
    required: false,
    content: {
      "application/json": {
        schema: schemaForFields(details.jsonFields, []),
      },
    },
  };
}

function makeOperation(method, route, docSummaries) {
  const key = `${method.toLowerCase()} ${route.openapiPath}`;
  const docs = docSummaries.get(key);
  const details = extractRequestDetails(route);
  const docstring = extractDocstring(route.functionSource);
  const summary = docs ? docs.summary : titleCase(route.handler);
  const status = String(route.statusCode || (method === "DELETE" ? 200 : 200));
  const requestBody = requestBodyFor(method, route, details);

  return {
    tags: [inferTag(route)],
    summary,
    description:
      docstring ||
      `Generated by static scan from ${route.file}:${route.line}. Check x-source for the exact handler.`,
    operationId: operationIdFor(method, route),
    servers: [SERVER_BY_SERVICE[route.service]],
    parameters: details.parameters,
    ...(requestBody ? { requestBody } : {}),
    responses: {
      [status]: {
        description: status === "202" ? "Accepted" : "Successful response",
        content: responseContentFor(route),
      },
      default: {
        description: "Error response",
        content: {
          "application/json": {
            schema: { $ref: "#/components/schemas/ErrorResponse" },
          },
        },
      },
    },
    "x-source": {
      service: route.service,
      file: route.file,
      line: route.line,
      handler: route.handler,
      owner: route.owner,
      rawPath: route.rawPath,
      kind: route.kind,
    },
    ...(docs ? { "x-source-doc": docs.file } : {}),
  };
}

function mergeOperation(existing, incoming) {
  const sources = existing["x-sources"] || [existing["x-source"]];
  sources.push(incoming["x-source"]);
  existing["x-sources"] = sources;
  existing["x-duplicate-count"] = sources.length;

  for (const tag of incoming.tags || []) {
    if (!existing.tags.includes(tag)) existing.tags.push(tag);
  }
  return existing;
}

function scanProject() {
  const registrationPrefixes = parseRegistrationPrefixes();
  const routes = [];

  for (const file of backendFiles()) {
    const sourceFile = rel(file);
    const text = readText(file);
    const localRouters = parseLocalRouters(text, sourceFile);
    const fileRoutes = extractRoutesFromFile(file, localRouters).map((route) =>
      finalizeRoute(route, registrationPrefixes)
    );
    routes.push(...fileRoutes);
  }

  const docs = docFiles();
  return {
    routes: routes.sort((a, b) =>
      `${a.service} ${a.openapiPath} ${a.line}`.localeCompare(
        `${b.service} ${b.openapiPath} ${b.line}`
      )
    ),
    docs,
    docSummaries: extractRouteDocsFromMarkdown(docs),
    registrationPrefixes,
  };
}

function buildOpenApi() {
  const scan = scanProject();
  const paths = {};

  for (const route of scan.routes) {
    if (!paths[route.openapiPath]) paths[route.openapiPath] = {};
    for (const method of route.methods) {
      const lower = method.toLowerCase();
      const operation = makeOperation(method, route, scan.docSummaries);
      if (paths[route.openapiPath][lower]) {
        paths[route.openapiPath][lower] = mergeOperation(
          paths[route.openapiPath][lower],
          operation
        );
      } else {
        paths[route.openapiPath][lower] = operation;
      }
    }
  }

  const operationCount = Object.values(paths).reduce(
    (total, item) => total + Object.keys(item).length,
    0
  );
  const duplicateCount = Object.values(paths).reduce(
    (total, item) =>
      total +
      Object.values(item).filter((operation) => operation["x-duplicate-count"])
        .length,
    0
  );

  return {
    openapi: "3.1.0",
    info: {
      title: "AI-Assistant Backend API",
      version: "0.1.0",
      description:
        "Static OpenAPI document generated from Flask/FastAPI route source files and markdown docs. Flask schemas are best-effort and include x-source metadata for deep backend inspection.",
    },
    servers: Object.values(SERVER_BY_SERVICE),
    externalDocs: {
      description: "Repository API reference",
      url: "./app/docs/API_REFERENCE.md",
    },
    tags: [
      "Chatbot",
      "Chat Streaming",
      "Async Chat",
      "Conversations",
      "Memory",
      "MCP",
      "Images",
      "Image Generation",
      "Stable Diffusion",
      "Anime Pipeline",
      "Reasoning Image Gen",
      "Video",
      "Models",
      "Skills",
      "Characters",
      "Jobs",
      "Auth",
      "External API",
      "Health",
      "RAG Documents",
      "RAG Query",
      "RAG Health",
      "CLIP Embeddings",
      "CLIP Health",
    ].map((name) => ({ name })),
    paths,
    components: {
      securitySchemes: {
        BearerAuth: {
          type: "http",
          scheme: "bearer",
          bearerFormat: "JWT",
          description:
            "Optional Authorization header for endpoints that require a bearer token.",
        },
      },
      schemas: {
        AnyJson: {
          description: "Generic JSON payload. Inspect x-source for exact handler logic.",
        },
        ErrorResponse: {
          type: "object",
          additionalProperties: true,
          properties: {
            error: { type: "string" },
            message: { type: "string" },
            detail: {},
          },
        },
      },
    },
    "x-generated-by": "openapi.js static scanner",
    "x-scan": {
      backendFiles: backendFiles().map(rel),
      markdownFilesScanned: scan.docs.map(rel),
      rawRouteDecorators: scan.routes.length,
      uniqueOperations: operationCount,
      duplicateOperations: duplicateCount,
      notes: [
        "chatbot_main.py is the live Flask monolith entrypoint.",
        "services/chatbot/routes/__init__.py is intentionally not treated as the live registration source.",
        "reasoning image routes are conditional in the runtime app but included here for inspection.",
        "Flask request/response schemas are inferred from static source patterns and may be incomplete.",
      ],
    },
  };
}

function printSummary() {
  const spec = buildOpenApi();
  const services = {};
  for (const pathItem of Object.values(spec.paths)) {
    for (const operation of Object.values(pathItem)) {
      const source = operation["x-source"];
      services[source.service] = (services[source.service] || 0) + 1;
    }
  }

  console.log("AI-Assistant OpenAPI scan");
  console.log(`Raw route decorators: ${spec["x-scan"].rawRouteDecorators}`);
  console.log(`Unique operations: ${spec["x-scan"].uniqueOperations}`);
  console.log(`Duplicate operations: ${spec["x-scan"].duplicateOperations}`);
  console.log(`Backend files scanned: ${spec["x-scan"].backendFiles.length}`);
  console.log(`Markdown files scanned: ${spec["x-scan"].markdownFilesScanned.length}`);
  console.log("Operations by service:");
  for (const [service, count] of Object.entries(services).sort()) {
    console.log(`  ${service}: ${count}`);
  }
  console.log("");
  console.log("Write JSON with: node app/scripts/openapi.js > openapi.json");
}

function printRoutes() {
  const scan = scanProject();
  for (const route of scan.routes) {
    console.log(
      `${route.methods.join(",").padEnd(8)} ${route.openapiPath.padEnd(60)} ${route.file}:${route.line} ${route.handler}`
    );
  }
}

if (require.main === module) {
  const arg = process.argv[2];
  if (arg === "--summary") {
    printSummary();
  } else if (arg === "--routes") {
    printRoutes();
  } else {
    process.stdout.write(`${JSON.stringify(buildOpenApi(), null, 2)}\n`);
  }
}

module.exports = {
  buildOpenApi,
  scanProject,
};
