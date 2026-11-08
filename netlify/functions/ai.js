// Помічник новин Полтави: отримує питання і список новин, відповідає через Groq.
// Ключ GROQ_API_KEY зберігається у змінних середовища Netlify, а не в коді.

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

const SYSTEM_PROMPT =
  "Ти помічник з новин Полтави. Відповідай українською мовою, коротко і по суті. " +
  "Відповідай лише на основі наданого списку новин. Для кожної новини, яку згадуєш, " +
  "вказуй час, місце, що сталося і посилання. Якщо потрібної інформації в списку немає, так і скажи. " +
  "Ніколи не вигадуй новин.";

exports.handler = async (event) => {
  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers: CORS, body: "" };
  }
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, headers: CORS, body: "Method not allowed" };
  }

  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    return json(500, { answer: "Помічник ще не налаштований: немає ключа доступу." });
  }

  let question = "";
  let news = [];
  try {
    const body = JSON.parse(event.body || "{}");
    question = String(body.question || "").slice(0, 300).trim();
    news = Array.isArray(body.news) ? body.news.slice(0, 40) : [];
  } catch {
    return json(400, { answer: "Некоректний запит." });
  }

  if (!question) {
    return json(400, { answer: "Напиши запит." });
  }

  const context = news
    .map((n) => `${n.published} | ${n.source} | ${n.title} | ${n.summary} | ${n.url}`)
    .join("\n");

  try {
    const res = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        temperature: 0.2,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: `Новини:\n${context || "список порожній"}\n\nПитання: ${question}` },
        ],
      }),
    });

    if (!res.ok) {
      return json(502, { answer: "Помічник тимчасово недоступний. Спробуй пізніше." });
    }

    const data = await res.json();
    const answer = data.choices?.[0]?.message?.content?.trim();
    return json(200, { answer: answer || "Не вдалося отримати відповідь." });
  } catch {
    return json(502, { answer: "Помічник тимчасово недоступний. Спробуй пізніше." });
  }
};

function json(status, payload) {
  return {
    statusCode: status,
    headers: { ...CORS, "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify(payload),
  };
  }
