#!/usr/bin/env node

import http from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { extname, resolve } from "node:path";

const DEFAULT_PORT = 8787;
const BOARD_INDEX = "https://www.ptt.cc/bbs/Stock/index.html";
const TWSE_ALL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL";
const TWSE_VALUATION = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL";
const TPEX_ALL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes";
const TPEX_VALUATION = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis";
const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36";

const POSITIVE_WORDS = [
  "低估",
  "便宜",
  "超跌",
  "打底",
  "轉強",
  "轉機",
  "突破",
  "成長",
  "利多",
  "買",
  "加碼",
  "看好",
  "殖利率",
  "配息",
  "EPS",
  "eps",
  "營收",
  "獲利",
  "毛利",
  "訂單",
  "法說",
  "回升",
  "落後補漲",
];

const NEGATIVE_WORDS = [
  "高估",
  "太貴",
  "套",
  "爛",
  "跌",
  "崩",
  "利空",
  "賣",
  "空",
  "減碼",
  "看壞",
  "虧",
  "衰退",
  "下修",
  "泡沫",
  "出貨",
  "破底",
];

const UNDERVALUED_WORDS = [
  "低估",
  "便宜",
  "本益比低",
  "淨值比低",
  "股淨比低",
  "殖利率",
  "配息",
  "超跌",
  "落後補漲",
  "價值",
  "轉機",
  "被錯殺",
  "低基期",
];

const HYPE_WORDS = [
  "噴",
  "飆",
  "妖",
  "歐印",
  "all in",
  "ALL IN",
  "無腦",
  "上車",
  "嘎",
  "火箭",
  "目標價",
];

const STOP_CODES = new Set(["2023", "2024", "2025", "2026", "2027", "2028"]);
let stockUniverseCache = null;
let valuationCache = null;

function usage() {
  console.log(`
PTT Stock Radar

Commands:
  node ptt-stock-radar.mjs serve [--port 8787]
  node ptt-stock-radar.mjs analyze <ptt-article-url> [-o report.html]
  node ptt-stock-radar.mjs latest [keyword]

Examples:
  node ptt-stock-radar.mjs serve
  node ptt-stock-radar.mjs analyze https://www.ptt.cc/bbs/Stock/M.1234567890.A.html -o report.html
  node ptt-stock-radar.mjs latest 盤後閒聊
`);
}

function decodeHtml(input) {
  return String(input || "")
    .replace(/&nbsp;/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x27;/g, "'")
    .replace(/&#x2F;/g, "/");
}

function stripTags(input) {
  return decodeHtml(String(input || "").replace(/<[^>]+>/g, ""));
}

function normalizeUrl(rawUrl) {
  if (!rawUrl || rawUrl === "term" || rawUrl.includes("term.ptt.cc")) {
    return BOARD_INDEX;
  }
  if (rawUrl.startsWith("/bbs/")) {
    return `https://www.ptt.cc${rawUrl}`;
  }
  if (rawUrl.startsWith("http://")) {
    return rawUrl.replace("http://", "https://");
  }
  return rawUrl;
}

async function fetchText(url) {
  const response = await fetch(url, {
    headers: {
      "user-agent": USER_AGENT,
      cookie: "over18=1",
    },
  });
  if (!response.ok) {
    throw new Error(`抓取失敗：HTTP ${response.status} ${response.statusText}`);
  }
  return await response.text();
}

async function fetchJson(url) {
  const response = await fetch(url, {
    headers: {
      "user-agent": USER_AGENT,
      accept: "application/json",
    },
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.json();
}

async function loadTaiwanStockUniverse() {
  if (stockUniverseCache) return stockUniverseCache;
  const universe = new Map();
  const add = (code, name, market, price = "") => {
    const normalized = String(code || "").trim();
    if (!/^[1-9]\d{3}$/.test(normalized)) return;
    universe.set(normalized, { code: normalized, name: String(name || "").trim(), market, price: parseNumber(price) });
  };

  try {
    const [twse, tpex] = await Promise.allSettled([fetchJson(TWSE_ALL), fetchJson(TPEX_ALL)]);
    if (twse.status === "fulfilled") {
      for (const item of twse.value) add(item.Code, item.Name, "上市", item.ClosingPrice);
    }
    if (tpex.status === "fulfilled") {
      for (const item of tpex.value) add(item.SecuritiesCompanyCode, item.CompanyName, "上櫃", item.Close);
    }
  } catch {
    // Network enrichment is optional; text analysis can still run without the market universe.
  }

  stockUniverseCache = universe;
  return universe;
}

function parseNumber(value) {
  const text = String(value ?? "").replace(/,/g, "").trim();
  if (!text || text === "--" || text === "-") return null;
  const number = Number(text);
  return Number.isFinite(number) ? number : null;
}

async function loadValuationData() {
  if (valuationCache) return valuationCache;
  const valuations = new Map();
  const add = (code, fields) => {
    const normalized = String(code || "").trim();
    if (!/^[1-9]\d{3}$/.test(normalized)) return;
    valuations.set(normalized, fields);
  };

  try {
    const [twse, tpex] = await Promise.allSettled([fetchJson(TWSE_VALUATION), fetchJson(TPEX_VALUATION)]);
    if (twse.status === "fulfilled") {
      for (const item of twse.value) {
        add(item.Code, {
          valuationDate: item.Date || "",
          pe: parseNumber(item.PEratio),
          dividendYield: parseNumber(item.DividendYield),
          pb: parseNumber(item.PBratio),
          dividendPerShare: null,
          valuationSource: "TWSE",
        });
      }
    }
    if (tpex.status === "fulfilled") {
      for (const item of tpex.value) {
        add(item.SecuritiesCompanyCode, {
          valuationDate: item.Date || "",
          pe: parseNumber(item.PriceEarningRatio),
          dividendYield: parseNumber(item.YieldRatio),
          pb: parseNumber(item.PriceBookRatio),
          dividendPerShare: parseNumber(item.DividendPerShare),
          valuationSource: "TPEx",
        });
      }
    }
  } catch {
    // Valuation enrichment is optional; discussion analysis still works without it.
  }

  valuationCache = valuations;
  return valuations;
}

function parseListPage(html, baseUrl) {
  const rows = [...html.matchAll(/<div class="r-ent">([\s\S]*?)<\/div>\s*<\/div>/g)];
  return rows
    .map((row) => {
      const block = row[1];
      const linkMatch = block.match(/<div class="title">\s*(?:<a href="([^"]+)">([\s\S]*?)<\/a>|([\s\S]*?))\s*<\/div>/);
      const authorMatch = block.match(/<div class="author">([\s\S]*?)<\/div>/);
      const dateMatch = block.match(/<div class="date">([\s\S]*?)<\/div>/);
      const pushMatch = block.match(/<div class="nrec">([\s\S]*?)<\/div>/);
      if (!linkMatch) return null;
      const href = linkMatch[1] ? new URL(linkMatch[1], baseUrl).toString() : null;
      const title = stripTags(linkMatch[2] || linkMatch[3] || "").trim();
      if (!href || !title) return null;
      return {
        title,
        href,
        author: stripTags(authorMatch?.[1] || "").trim(),
        date: stripTags(dateMatch?.[1] || "").trim(),
        push: stripTags(pushMatch?.[1] || "").trim(),
      };
    })
    .filter(Boolean);
}

function getPreviousPageUrl(html, currentUrl) {
  const match = html.match(/<a class="btn wide" href="([^"]+)">‹ 上頁<\/a>/);
  return match ? new URL(match[1], currentUrl).toString() : null;
}

async function findLatestArticle(keyword = "盤後閒聊", maxPages = 8) {
  let url = BOARD_INDEX;
  const visited = [];
  for (let page = 0; page < maxPages && url; page += 1) {
    const html = await fetchText(url);
    visited.push(url);
    const articles = parseListPage(html, url);
    const match = articles.find((article) => article.title.includes(keyword));
    if (match) return { ...match, searchedPages: visited };
    url = getPreviousPageUrl(html, url);
  }
  throw new Error(`找不到標題含「${keyword}」的文章，已搜尋 ${visited.length} 頁。`);
}

function parseArticle(html, url) {
  const title = stripTags(html.match(/<span class="article-meta-tag">標題<\/span>\s*<span class="article-meta-value">([\s\S]*?)<\/span>/)?.[1] || "");
  const author = stripTags(html.match(/<span class="article-meta-tag">作者<\/span>\s*<span class="article-meta-value">([\s\S]*?)<\/span>/)?.[1] || "");
  const date = stripTags(html.match(/<span class="article-meta-tag">時間<\/span>\s*<span class="article-meta-value">([\s\S]*?)<\/span>/)?.[1] || "");
  const contentMatch = html.match(/<div id="main-content"[^>]*>([\s\S]*?)<\/div>\s*<div id="article-polling"/);
  const mainHtml = contentMatch?.[1] || "";

  const pushRegex = /<div class="push">([\s\S]*?)<\/div>/g;
  const comments = [...mainHtml.matchAll(pushRegex)].map((match) => {
    const block = match[1];
    const tag = stripTags(block.match(/<span class="[^"]*\bpush-tag\b[^"]*">([\s\S]*?)<\/span>/)?.[1] || "").trim();
    const user = stripTags(block.match(/<span class="[^"]*\bpush-userid\b[^"]*">([\s\S]*?)<\/span>/)?.[1] || "").trim();
    const content = stripTags(block.match(/<span class="[^"]*\bpush-content\b[^"]*">([\s\S]*?)<\/span>/)?.[1] || "")
      .replace(/^:\s*/, "")
      .trim();
    const time = stripTags(block.match(/<span class="push-ipdatetime">([\s\S]*?)<\/span>/)?.[1] || "").trim();
    return { tag, user, content, time };
  });

  const bodyHtml = mainHtml
    .replace(/<div class="article-metaline[\s\S]*?<\/div>/g, "")
    .replace(/<div class="article-metaline-right[\s\S]*?<\/div>/g, "")
    .replace(pushRegex, "")
    .replace(/<span class="f2">※ 發信站:[\s\S]*$/g, "");

  const body = stripTags(bodyHtml)
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n")
    .trim();

  return { url, title, author, date, body, comments };
}

function countMatches(text, words) {
  return words.reduce((sum, word) => sum + (String(text).includes(word) ? 1 : 0), 0);
}

function extractStockCodes(text, universe = null) {
  const candidates = [...String(text).matchAll(/(?<!\d)([1-9]\d{3})(?!\d)/g)].map((match) => match[1]);
  return [...new Set(candidates)].filter((code) => {
    if (STOP_CODES.has(code)) return false;
    if (/20\d{2}/.test(code)) return false;
    if (universe?.size && !universe.has(code)) return false;
    return true;
  });
}

function scoreComment(comment) {
  const text = comment.content;
  return {
    positive: countMatches(text, POSITIVE_WORDS),
    negative: countMatches(text, NEGATIVE_WORDS),
    undervalued: countMatches(text, UNDERVALUED_WORDS),
    hype: countMatches(text, HYPE_WORDS),
  };
}

function buildNextChecks(item) {
  const checks = ["確認近 3 個月營收年增率", "查本益比/股價淨值比是否低於同業", "看近日法人買賣超與成交量是否異常"];
  if (item.undervalued > 0) checks.unshift("驗證低估理由是否有財報或估值支撐");
  if (item.positive > item.negative) checks.push("比對利多是否已反映在股價漲幅");
  if (item.hype >= 2) checks.push("檢查是否只是短線追價或情緒題材");
  if (item.mentions <= 1) checks.push("樣本數偏少，至少再觀察 2-3 篇相關討論");
  return [...new Set(checks)].slice(0, 5);
}

function evaluateValuation(valuation) {
  const flags = [];
  const warnings = [];
  if (!valuation) {
    return {
      pe: null,
      pb: null,
      dividendYield: null,
      dividendPerShare: null,
      valuationDate: "",
      valuationSource: "",
      cheapFlags: [],
      valuationWarnings: ["缺估值資料"],
      valuationScore: 0,
    };
  }

  if (valuation.pe !== null && valuation.pe > 0 && valuation.pe <= 12) flags.push("本益比偏低");
  if (valuation.pb !== null && valuation.pb > 0 && valuation.pb <= 1) flags.push("股價淨值比低於 1");
  if (valuation.dividendYield !== null && valuation.dividendYield >= 5) flags.push("殖利率 >= 5%");
  if (valuation.pe !== null && valuation.pe >= 30) warnings.push("本益比偏高");
  if (valuation.pb !== null && valuation.pb >= 4) warnings.push("股價淨值比偏高");
  if (valuation.pe === null) warnings.push("缺本益比");
  if (valuation.pb === null) warnings.push("缺股價淨值比");

  return {
    ...valuation,
    cheapFlags: flags,
    valuationWarnings: warnings,
    valuationScore: flags.length * 12 - warnings.filter((warning) => warning.includes("偏高")).length * 8,
  };
}

function classifyResearch(stock) {
  const hasDiscussion = stock.referenceScore >= 40;
  const hasValuation = stock.cheapFlags.length > 0;
  const thin = stock.uniqueUsers <= 1 || stock.mentions <= 1;
  if (hasDiscussion && hasValuation) return "討論熱且估值有支撐";
  if (hasDiscussion && !hasValuation) return "討論熱，估值待確認";
  if (!hasDiscussion && hasValuation) return thin ? "估值便宜但樣本少" : "估值便宜，討論未熱";
  return thin ? "樣本少，先觀察" : "一般觀察";
}

function analyzeArticle(article, universe = null, valuations = null) {
  const stockMap = new Map();
  const allText = [article.title, article.body, ...article.comments.map((c) => c.content)].join("\n");
  const articleCodes = extractStockCodes(allText, universe);

  for (const code of articleCodes) {
    const meta = universe?.get(code);
    stockMap.set(code, {
      code,
      name: meta?.name || "",
      market: meta?.market || "",
      price: meta?.price ?? null,
      mentions: 0,
      push: 0,
      boo: 0,
      neutral: 0,
      uniqueUsers: new Set(),
      userMentions: new Map(),
      positive: 0,
      negative: 0,
      undervalued: 0,
      hype: 0,
      evidence: [],
    });
  }

  for (const comment of article.comments) {
    const codes = extractStockCodes(comment.content, universe);
    if (!codes.length) continue;
    const commentScore = scoreComment(comment);
    for (const code of codes) {
      if (!stockMap.has(code)) {
        const meta = universe?.get(code);
        stockMap.set(code, {
          code,
          name: meta?.name || "",
          market: meta?.market || "",
          price: meta?.price ?? null,
          mentions: 0,
          push: 0,
          boo: 0,
          neutral: 0,
          uniqueUsers: new Set(),
          userMentions: new Map(),
          positive: 0,
          negative: 0,
          undervalued: 0,
          hype: 0,
          evidence: [],
        });
      }
      const item = stockMap.get(code);
      item.mentions += 1;
      if (comment.tag.includes("推")) item.push += 1;
      else if (comment.tag.includes("噓")) item.boo += 1;
      else item.neutral += 1;
      if (comment.user) {
        item.uniqueUsers.add(comment.user);
        item.userMentions.set(comment.user, (item.userMentions.get(comment.user) || 0) + 1);
      }
      item.positive += commentScore.positive;
      item.negative += commentScore.negative;
      item.undervalued += commentScore.undervalued;
      item.hype += commentScore.hype;
      if (item.evidence.length < 6) {
        item.evidence.push({
          tag: comment.tag,
          user: comment.user,
          time: comment.time,
          text: comment.content.slice(0, 140),
        });
      }
    }
  }

  const stocks = [...stockMap.values()]
    .map((item) => {
      const uniqueUsers = item.uniqueUsers.size;
      const sentiment = item.positive - item.negative;
      const undervaluedScore =
        item.mentions * 2 +
        uniqueUsers * 3 +
        item.positive * 2 +
        item.undervalued * 5 -
        item.negative * 1.5 -
        item.hype * 2;
      const riskFlags = [];
      const userBreakdown = [...item.userMentions.entries()]
        .map(([user, mentions]) => ({ user, mentions }))
        .sort((a, b) => b.mentions - a.mentions || a.user.localeCompare(b.user))
        .slice(0, 20);
      const topUserMentions = userBreakdown[0]?.mentions || 0;
      const concentrationRatio = item.mentions ? topUserMentions / item.mentions : 0;
      const evidenceScore =
        uniqueUsers * 4 +
        item.mentions * 1.5 +
        item.undervalued * 5 +
        Math.max(0, sentiment) * 1.5 -
        item.hype * 2 -
        (concentrationRatio >= 0.6 && item.mentions >= 3 ? 8 : 0);
      const referenceScore = Math.max(0, Math.min(100, Math.round(evidenceScore * 4)));
      const referenceLevel =
        referenceScore >= 70 ? "高" : referenceScore >= 40 ? "中" : referenceScore >= 20 ? "低" : "觀察";
      if (item.hype >= 2) riskFlags.push("炒作詞偏多");
      if (item.mentions >= 5 && uniqueUsers <= 2) riskFlags.push("少數帳號集中提及");
      if (userBreakdown[0]?.mentions >= 3) riskFlags.push("單一帳號多次提及");
      if (concentrationRatio >= 0.6 && item.mentions >= 3) riskFlags.push("ID 集中度偏高");
      if (item.negative > item.positive + item.undervalued) riskFlags.push("負面詞較多");
      const valuation = evaluateValuation(valuations?.get(item.code));
      const adjustedReferenceScore = Math.max(0, Math.min(100, referenceScore + valuation.valuationScore));
      const stock = {
        code: item.code,
        name: item.name,
        market: item.market,
        price: item.price,
        mentions: item.mentions,
        uniqueUsers,
        push: item.push,
        boo: item.boo,
        neutral: item.neutral,
        positive: item.positive,
        negative: item.negative,
        undervaluedSignals: item.undervalued,
        hypeSignals: item.hype,
        sentiment,
        undervaluedScore: Number(undervaluedScore.toFixed(1)),
        referenceScore: adjustedReferenceScore,
        referenceLevel:
          adjustedReferenceScore >= 70 ? "高" : adjustedReferenceScore >= 40 ? "中" : adjustedReferenceScore >= 20 ? "低" : "觀察",
        concentrationRatio: Number(concentrationRatio.toFixed(2)),
        riskFlags,
        userBreakdown,
        nextChecks: buildNextChecks(item),
        evidence: item.evidence,
        ...valuation,
      };
      stock.researchBucket = classifyResearch(stock);
      return stock;
    })
    .filter((item) => item.mentions > 0)
    .sort((a, b) => b.undervaluedScore - a.undervaluedScore || b.mentions - a.mentions);

  const pushCount = article.comments.filter((c) => c.tag.includes("推")).length;
  const booCount = article.comments.filter((c) => c.tag.includes("噓")).length;
  const neutralCount = article.comments.length - pushCount - booCount;

  return {
    generatedAt: new Date().toISOString(),
    source: {
      url: article.url,
      title: article.title,
      author: article.author,
      date: article.date,
    },
    totals: {
      comments: article.comments.length,
      push: pushCount,
      boo: booCount,
      neutral: neutralCount,
      stockCount: stocks.length,
    },
    definitions: {
      undervaluedScore:
        "mentions*2 + uniqueUsers*3 + positiveWords*2 + undervaluedWords*5 - negativeWords*1.5 - hypeWords*2",
      universe:
        universe?.size
          ? "使用 TWSE/STOCK_DAY_ALL 與 TPEx/tpex_mainboard_daily_close_quotes 公開清單過濾有效台股代號。"
          : "無法取得交易所/櫃買清單時，退回四碼代號文字辨識。",
      referenceScore:
        "綜合不同 ID 數、提及數、低估線索、正負情緒、炒作詞與 ID 集中度，估算此 PTT 訊號的參考性。",
      caveat:
        "此分數只代表討論雷達，不是投資建議；真正低估仍需接基本面與估值資料驗證。",
    },
    stocks,
  };
}

async function analyzeUrl(rawUrl) {
  const normalizedUrl = normalizeUrl(rawUrl);
  if (normalizedUrl.endsWith("/bbs/Stock/index.html") || normalizedUrl.includes("/bbs/Stock/index")) {
    const latest = await findLatestArticle("盤後閒聊");
    return analyzeUrl(latest.href);
  }
  const html = await fetchText(normalizedUrl);
  const article = parseArticle(html, normalizedUrl);
  if (!article.title && !article.comments.length) {
    throw new Error("這看起來不像 PTT Web 版文章頁，請貼 https://www.ptt.cc/bbs/Stock/...html。");
  }
  const [universe, valuations] = await Promise.all([loadTaiwanStockUniverse(), loadValuationData()]);
  return analyzeArticle(article, universe, valuations);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatMetric(value, digits = 2) {
  return value === null || value === undefined ? "-" : Number(value).toFixed(digits).replace(/\.00$/, "");
}

function renderStaticReport(data) {
  const rows = data.stocks
    .map(
      (stock) => `
        <tr>
          <td><strong>${escapeHtml(stock.code)}</strong></td>
          <td>${escapeHtml(stock.name || "")}</td>
          <td>${escapeHtml(stock.researchBucket || "")}</td>
          <td>${formatMetric(stock.price)}</td>
          <td>${formatMetric(stock.pe)}</td>
          <td>${formatMetric(stock.pb)}</td>
          <td>${formatMetric(stock.dividendYield)}%</td>
          <td>${stock.cheapFlags.map((flag) => escapeHtml(flag)).join("<br>") || "-"}</td>
          <td>${stock.undervaluedScore}</td>
          <td>${stock.referenceLevel} (${stock.referenceScore})</td>
          <td>${Math.round(stock.concentrationRatio * 100)}%</td>
          <td>${stock.mentions}</td>
          <td>${stock.uniqueUsers}</td>
          <td>${stock.userBreakdown.map((u) => `${escapeHtml(u.user)} (${u.mentions})`).join("<br>")}</td>
          <td>${stock.sentiment}</td>
          <td>${stock.undervaluedSignals}</td>
          <td>${escapeHtml([...stock.riskFlags, ...stock.valuationWarnings].join("、") || "無")}</td>
          <td>${stock.nextChecks.map((check) => escapeHtml(check)).join("<br>")}</td>
          <td>${stock.evidence.map((e) => escapeHtml(e.text)).join("<br>")}</td>
        </tr>`
    )
    .join("");

  return `<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PTT Stock Radar Report</title>
  <style>
    body { margin: 0; font-family: Arial, "Microsoft JhengHei", sans-serif; background: #f6f7f9; color: #1f2933; }
    header { background: #102a43; color: white; padding: 28px 32px; }
    main { max-width: 1180px; margin: 0 auto; padding: 24px; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .card { background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 16px; }
    .metric { font-size: 28px; font-weight: 700; margin-top: 6px; }
    table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #d9e2ec; }
    th, td { padding: 10px; border-bottom: 1px solid #e4e7eb; vertical-align: top; text-align: left; }
    th { background: #eef2f7; }
    a { color: #0b65c2; }
    @media (max-width: 800px) { .grid { grid-template-columns: 1fr 1fr; } main { padding: 16px; } table { font-size: 13px; } }
  </style>
</head>
<body>
  <header>
    <h1>PTT Stock Radar</h1>
    <div>${escapeHtml(data.source.title)} · <a href="${escapeHtml(data.source.url)}">${escapeHtml(data.source.url)}</a></div>
  </header>
  <main>
    <section class="grid">
      <div class="card">留言數<div class="metric">${data.totals.comments}</div></div>
      <div class="card">股票數<div class="metric">${data.totals.stockCount}</div></div>
      <div class="card">推 / 噓<div class="metric">${data.totals.push} / ${data.totals.boo}</div></div>
      <div class="card">產生時間<div class="metric" style="font-size:16px">${escapeHtml(data.generatedAt)}</div></div>
    </section>
    <h2>低估候選排行</h2>
    <table>
      <thead><tr><th>代號</th><th>名稱</th><th>研究分類</th><th>收盤價</th><th>本益比</th><th>股淨比</th><th>殖利率</th><th>估值線索</th><th>低估分數</th><th>參考等級</th><th>ID 集中度</th><th>提及</th><th>帳號數</th><th>提及 ID</th><th>情緒</th><th>低估線索</th><th>風險</th><th>下一步查核</th><th>留言摘錄</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="19">沒有找到股票代號。</td></tr>`}</tbody>
    </table>
    <p>${escapeHtml(data.definitions.caveat)}</p>
    <p>${escapeHtml(data.definitions.universe)}</p>
    <p>參考等級：${escapeHtml(data.definitions.referenceScore)}</p>
    <p>估值來源：上市使用 TWSE BWIBBU_ALL，上市收盤價使用 TWSE STOCK_DAY_ALL；上櫃使用 TPEx 本益比分析與日收盤行情。</p>
    <p>分數定義：${escapeHtml(data.definitions.undervaluedScore)}</p>
  </main>
</body>
</html>`;
}

async function serve(port = DEFAULT_PORT) {
  const server = http.createServer(async (req, res) => {
    try {
      const requestUrl = new URL(req.url || "/", `http://localhost:${port}`);
      if (requestUrl.pathname === "/api/analyze") {
        const url = requestUrl.searchParams.get("url");
        const data = await analyzeUrl(url);
        res.writeHead(200, { "content-type": "application/json; charset=utf-8" });
        res.end(JSON.stringify(data));
        return;
      }
      if (requestUrl.pathname === "/api/latest") {
        const keyword = requestUrl.searchParams.get("keyword") || "盤後閒聊";
        const article = await findLatestArticle(keyword);
        res.writeHead(200, { "content-type": "application/json; charset=utf-8" });
        res.end(JSON.stringify(article));
        return;
      }
      const file = requestUrl.pathname === "/" ? "dashboard.html" : requestUrl.pathname.slice(1);
      const path = resolve(file);
      if (!existsSync(path) || !path.startsWith(process.cwd())) {
        res.writeHead(404);
        res.end("Not found");
        return;
      }
      const contentType = extname(path) === ".html" ? "text/html; charset=utf-8" : "text/plain; charset=utf-8";
      res.writeHead(200, { "content-type": contentType });
      res.end(await readFile(path));
    } catch (error) {
      res.writeHead(500, { "content-type": "application/json; charset=utf-8" });
      res.end(JSON.stringify({ error: error.message || String(error) }));
    }
  });
  server.listen(port, () => {
    console.log(`PTT Stock Radar running at http://localhost:${port}`);
  });
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  if (!command || command === "--help" || command === "-h") {
    usage();
    return;
  }
  if (command === "serve") {
    const portIndex = args.indexOf("--port");
    const port = portIndex >= 0 ? Number(args[portIndex + 1]) : DEFAULT_PORT;
    await serve(port);
    return;
  }
  if (command === "latest") {
    const keyword = args[0] || "盤後閒聊";
    console.log(JSON.stringify(await findLatestArticle(keyword), null, 2));
    return;
  }
  if (command === "analyze") {
    const url = args[0];
    if (!url) throw new Error("請提供 PTT 文章網址。");
    const outputIndex = args.indexOf("-o");
    const data = await analyzeUrl(url);
    if (outputIndex >= 0) {
      const output = args[outputIndex + 1] || "ptt-stock-report.html";
      await writeFile(output, renderStaticReport(data), "utf8");
      console.log(`已輸出：${output}`);
    } else {
      console.log(JSON.stringify(data, null, 2));
    }
    return;
  }
  usage();
}

main().catch((error) => {
  console.error(error.message || error);
  process.exitCode = 1;
});
