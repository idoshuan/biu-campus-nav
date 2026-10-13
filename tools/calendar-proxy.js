// Cloudflare Worker that lets the page read a calendar feed (.ics).
// Calendar services such as Google don't allow other web pages to read their feeds directly,
// so the page asks this worker instead: GET https://<worker>/?url=<calendar link>
// Only known calendar hosts are forwarded, so it can't be used as an open proxy. Nothing is stored or logged.
//
// Deploy: npx wrangler deploy tools/calendar-proxy.js --name biu-calendar-proxy --compatibility-date 2024-09-01
// Then put the worker URL in CAL_PROXY in src/app.html and run `python3 tools/assemble.py`.

const ALLOWED_HOSTS = [
  /^calendar\.google\.com$/,
  /^outlook\.(office365|office|live)\.com$/,
  /^p\d+-caldav\.icloud\.com$/,
  /^calendar\.yahoo\.com$/,
];
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS" };

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (request.method !== "GET") return new Response("Method not allowed", { status: 405, headers: CORS });

    let target;
    try {
      target = new URL(new URL(request.url).searchParams.get("url").replace(/^webcal:\/\//i, "https://"));
    } catch {
      return new Response("Missing or invalid ?url=", { status: 400, headers: CORS });
    }
    if (target.protocol !== "https:" || !ALLOWED_HOSTS.some((re) => re.test(target.hostname))) {
      return new Response("This calendar host is not allowed", { status: 403, headers: CORS });
    }

    const upstream = await fetch(target.toString(), { headers: { Accept: "text/calendar" }, redirect: "follow" });
    const body = await upstream.text();
    if (!upstream.ok || !/BEGIN:VCALENDAR/i.test(body)) {
      return new Response("The link did not return a calendar", { status: 502, headers: CORS });
    }
    return new Response(body, {
      headers: { ...CORS, "Content-Type": "text/calendar; charset=utf-8", "Cache-Control": "private, max-age=300" },
    });
  },
};
