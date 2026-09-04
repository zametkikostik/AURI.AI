import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 5,
  duration: "30s",
  thresholds: {
    http_req_duration: ["p(95)<800"],
    http_req_failed: ["rate<0.05"],
  },
};

const BASE = __ENV.BASE_URL || "http://localhost:8000";
const EMAIL = __ENV.EMAIL || "";
const PASSWORD = __ENV.PASSWORD || "";

export default function () {
  const health = http.get(`${BASE}/health`);
  check(health, { "health 200": (r) => r.status === 200 });

  if (EMAIL && PASSWORD) {
    const login = http.post(
      `${BASE}/api/v1/auth/login`,
      JSON.stringify({ email: EMAIL, password: PASSWORD }),
      { headers: { "Content-Type": "application/json" } }
    );
    check(login, { "login 200": (r) => r.status === 200 });
    const token = login.json("access_token");
    if (token) {
      const meetings = http.get(`${BASE}/api/v1/meetings`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      check(meetings, { "meetings 200": (r) => r.status === 200 });
    }
  }
  sleep(1);
}
