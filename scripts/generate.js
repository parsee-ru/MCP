#!/usr/bin/env node
"use strict";
/*
 * generate.js — пересобирает tools.json и llms.txt из живого кода приложения.
 *
 * Списки инструментов и инструкция должны совпадать с тем, что реально отдаёт сервер.
 * Переписывать их руками — верный способ разойтись: в приложении инструмент появился,
 * а в репозитории его нет, и ассистент про него не знает.
 *
 * Запуск из корня репозитория ПАРСИ:  node parsee-mcp/scripts/generate.js
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "parsee-desktop", "src", "main");

const { TOOLS, PORT } = require(path.join(SRC, "mcp-server.js"));
const { INSTRUCTIONS } = require(path.join(SRC, "mcp-instructions.js"));
const pkg = require(path.join(ROOT, "parsee-desktop", "package.json"));

const catalogue = {
  name: "ru.parsee/parsee",
  appVersion: pkg.version,
  port: PORT,
  toolCount: TOOLS.length,
  tools: TOOLS.map((t) => ({
    name: t.name,
    title: t.title || "",
    description: t.description || "",
    input: Object.keys((t.inputSchema && t.inputSchema.properties) || {}),
    readOnly: !!(t.annotations && t.annotations.readOnlyHint),
    destructive: !!(t.annotations && t.annotations.destructiveHint),
  })),
};
fs.writeFileSync(path.join(OUT, "tools.json"), JSON.stringify(catalogue, null, 2) + "\n");

const head = "# ПАРСИ · MCP\n\n" +
  "> Инструкция для ИИ-ассистентов. Тот же текст сервер отдаёт при подключении и инструментом parsee_help.\n" +
  "> Работает только вместе с приложением ПАРСИ (https://parsee.ru): сервер входит в его состав и слушает 127.0.0.1.\n\n";
fs.writeFileSync(path.join(OUT, "llms.txt"), head + INSTRUCTIONS + "\n");

// В манифесте реестра держим актуальную версию и число инструментов.
const manifestPath = path.join(OUT, "server.json");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
manifest.version = String(pkg.version).replace(/-.*$/, "");
manifest._meta.capabilities.tools = TOOLS.length;
manifest._meta.capabilities.readOnlyTools = TOOLS.filter((t) => t.annotations && t.annotations.readOnlyHint).length;
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n");

console.log("обновлено: инструментов " + TOOLS.length + ", инструкция " + INSTRUCTIONS.length + " символов");
