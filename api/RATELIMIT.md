# Handling Rate Limits

The Metron API enforces two independent rate limits on every authenticated request: a short **burst** limit and a longer **sustained** limit. This guide explains the response headers the API sends back, how to interpret them, and how to build a well-behaved client that backs off automatically instead of hammering the API with retries.

## Table of Contents

- [How the limits work](#how-the-limits-work)
- [Response headers](#response-headers)
- [The 429 response](#the-429-response)
- [Recommended client strategy](#recommended-client-strategy)
- [Examples](#examples)
    - [Python](#python)
    - [Go](#go)
    - [C#](#c)
    - [JavaScript](#javascript)
- [Common mistakes](#common-mistakes)

## How the limits work

Every request against `/api/` counts against two counters at once:

| Scope       | Default limit | Window   |
| ----------- | -------------- | -------- |
| Burst       | 20 requests    | 1 minute |
| Sustained   | 5,000 requests | 1 day    |

Both are enforced per authenticated user. Whichever limit you hit first returns a `429 Too Many Requests` response — a request can be rejected by the burst limit even if you're nowhere near your daily sustained limit, and vice versa.

Supporters (OpenCollective donors) get an elevated **sustained** limit based on their tier; the burst limit is the same for everyone. Don't hardcode the numbers in the table above — always read the limit from the response headers, since it can vary per account and may change over time.

## Response headers

Every successful response includes six headers describing both counters:

```
X-RateLimit-Burst-Limit: 20
X-RateLimit-Burst-Remaining: 17
X-RateLimit-Burst-Reset: 1700000060
X-RateLimit-Sustained-Limit: 5000
X-RateLimit-Sustained-Remaining: 4982
X-RateLimit-Sustained-Reset: 1700003600
```

- **`-Limit`** — the total number of requests allowed in the current window.
- **`-Remaining`** — how many requests you have left in the current window. When this hits `0`, your *next* request in that window will be throttled.
- **`-Reset`** — a Unix timestamp (seconds since epoch) for when the window's counter resets.

A well-behaved client should read `X-RateLimit-Burst-Remaining` and `X-RateLimit-Sustained-Remaining` after every response, and slow down proactively — for example, pausing until the reset time once remaining count drops to a small number — rather than waiting to be throttled.

## The 429 response

When either limit is exceeded, the API returns:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 42
Content-Type: application/json

{"detail": "Request was throttled. Expected available in 42 seconds."}
```

- **`Retry-After`** is the number of seconds to wait before retrying. Always prefer this header over parsing the `detail` message — the header is a stable contract, the message text is not.
- The rate limit headers (`X-RateLimit-*`) are still present on 429 responses, so you can tell which of the two limits (burst or sustained) was the one that tripped.

## Recommended client strategy

1. **Track remaining counts locally.** Cache the `X-RateLimit-*-Remaining` and `X-RateLimit-*-Reset` values from each response so you know how much headroom you have before making the next call.
2. **Throttle proactively.** If `Burst-Remaining` reaches `0`, sleep until `Burst-Reset` before your next request instead of firing and hoping.
3. **On a 429, always honor `Retry-After`.** Sleep for exactly that many seconds, then retry. Don't use a fixed retry delay.
4. **Use exponential backoff as a fallback** for network errors or unexpected 5xx responses, but not for 429s — `Retry-After` already tells you the correct wait time.
5. **Reduce how often you need to ask.** Use [filtering](README.md#filtering) and `modified_gt` so a single request returns only the data you actually need — fewer results per query means fewer pages, and fewer pages means fewer requests against your limit. Note that [conditional requests](README.md#conditional-requests) (`If-Modified-Since`) still count as a request each time (a `304` still consumes a slot on both counters) — they save you bandwidth and parsing on unchanged resources, not requests, so they don't help you stay under the rate limit by themselves.

## Examples

Each example makes a request, checks **both** the burst and sustained counters (a client that only watches burst will still get blindsided by the daily sustained limit), and — if throttled — waits for `Retry-After` seconds before retrying once.

**Note:** These are rough sketches of the *logic* needed to handle rate limits correctly, not production-ready libraries. They omit things a real client would want, such as a retry cap, jitter, logging/observability hooks, and thread- or task-safety if you're issuing concurrent requests. Adapt them to your application's HTTP client and error-handling conventions.

### Python

```python
import time
import requests

session = requests.Session()
session.headers["Authorization"] = "Bearer <your-token>"


def get_with_rate_limit(url, **kwargs):
    while True:
        resp = session.get(url, **kwargs)

        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 1))
            print(f"Rate limited, waiting {wait}s")
            time.sleep(wait)
            continue

        # Check sustained before burst -- running out of the daily sustained
        # limit costs far more wait time than running out of burst, so treat
        # it as the higher-priority check even though either can throttle you.
        wait = 0
        for scope in ("Sustained", "Burst"):
            remaining = int(resp.headers.get(f"X-RateLimit-{scope}-Remaining", 1))
            reset = int(resp.headers.get(f"X-RateLimit-{scope}-Reset", 0))
            if remaining == 0:
                wait = max(wait, reset - int(time.time()))

        if wait > 0:
            print(f"Rate limit exhausted, pausing {wait}s before next call")
            time.sleep(wait)

        return resp


resp = get_with_rate_limit("https://metron.cloud/api/issue/12345/")
resp.raise_for_status()
data = resp.json()
```

### Go

```go
package main

import (
	"fmt"
	"net/http"
	"strconv"
	"time"
)

func getWithRateLimit(client *http.Client, url, token string) (*http.Response, error) {
	for {
		req, err := http.NewRequest(http.MethodGet, url, nil)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+token)

		resp, err := client.Do(req)
		if err != nil {
			return nil, err
		}

		if resp.StatusCode == http.StatusTooManyRequests {
			wait := 1
			if v := resp.Header.Get("Retry-After"); v != "" {
				if parsed, err := strconv.Atoi(v); err == nil {
					wait = parsed
				}
			}
			resp.Body.Close()
			fmt.Printf("Rate limited, waiting %ds\n", wait)
			time.Sleep(time.Duration(wait) * time.Second)
			continue
		}

		// Check sustained before burst -- running out of the daily sustained
		// limit costs far more wait time than running out of burst, so treat
		// it as the higher-priority check even though either can throttle you.
		var wait int64
		for _, scope := range []string{"Sustained", "Burst"} {
			remaining, err := strconv.Atoi(resp.Header.Get("X-RateLimit-" + scope + "-Remaining"))
			if err != nil || remaining != 0 {
				continue
			}
			reset, _ := strconv.ParseInt(resp.Header.Get("X-RateLimit-"+scope+"-Reset"), 10, 64)
			if w := reset - time.Now().Unix(); w > wait {
				wait = w
			}
		}
		if wait > 0 {
			fmt.Printf("Rate limit exhausted, pausing %ds before next call\n", wait)
			time.Sleep(time.Duration(wait) * time.Second)
		}

		return resp, nil
	}
}

func main() {
	client := &http.Client{}
	resp, err := getWithRateLimit(client, "https://metron.cloud/api/issue/12345/", "<your-token>")
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()
	fmt.Println("status:", resp.StatusCode)
}
```

### C#

```csharp
using System;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;

public class MetronClient
{
    private readonly HttpClient _client;

    public MetronClient(string token)
    {
        _client = new HttpClient { BaseAddress = new Uri("https://metron.cloud/") };
        _client.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", token);
    }

    public async Task<HttpResponseMessage> GetWithRateLimitAsync(string requestUri)
    {
        while (true)
        {
            var response = await _client.GetAsync(requestUri);

            if (response.StatusCode == System.Net.HttpStatusCode.TooManyRequests)
            {
                var wait = response.Headers.RetryAfter?.Delta?.TotalSeconds ?? 1;
                Console.WriteLine($"Rate limited, waiting {wait}s");
                await Task.Delay(TimeSpan.FromSeconds(wait));
                continue;
            }

            // Check sustained before burst -- running out of the daily sustained
            // limit costs far more wait time than running out of burst, so treat
            // it as the higher-priority check even though either can throttle you.
            var wait = TimeSpan.Zero;
            foreach (var scope in new[] { "Sustained", "Burst" })
            {
                if (response.Headers.TryGetValues($"X-RateLimit-{scope}-Remaining", out var remainingValues)
                    && int.TryParse(remainingValues.First(), out var remaining)
                    && remaining == 0
                    && response.Headers.TryGetValues($"X-RateLimit-{scope}-Reset", out var resetValues))
                {
                    var resetEpoch = long.Parse(resetValues.First());
                    var resetTime = DateTimeOffset.FromUnixTimeSeconds(resetEpoch);
                    var scopeWait = resetTime - DateTimeOffset.UtcNow;
                    if (scopeWait > wait)
                    {
                        wait = scopeWait;
                    }
                }
            }

            if (wait > TimeSpan.Zero)
            {
                Console.WriteLine($"Rate limit exhausted, pausing {wait.TotalSeconds}s before next call");
                await Task.Delay(wait);
            }

            return response;
        }
    }
}
```

### JavaScript

Works in Node.js (18+) and modern browsers using the built-in `fetch` API.

```javascript
const BASE_URL = "https://metron.cloud/api/";
const TOKEN = "<your-token>";

async function getWithRateLimit(path) {
  while (true) {
    const resp = await fetch(BASE_URL + path, {
      headers: { Authorization: `Bearer ${TOKEN}` },
    });

    if (resp.status === 429) {
      const wait = Number(resp.headers.get("Retry-After") ?? 1);
      console.log(`Rate limited, waiting ${wait}s`);
      await new Promise((r) => setTimeout(r, wait * 1000));
      continue;
    }

    // Check sustained before burst -- running out of the daily sustained
    // limit costs far more wait time than running out of burst, so treat
    // it as the higher-priority check even though either can throttle you.
    let wait = 0;
    for (const scope of ["Sustained", "Burst"]) {
      const remaining = Number(resp.headers.get(`X-RateLimit-${scope}-Remaining`) ?? 1);
      if (remaining === 0) {
        const reset = Number(resp.headers.get(`X-RateLimit-${scope}-Reset`) ?? 0);
        wait = Math.max(wait, reset - Math.floor(Date.now() / 1000));
      }
    }
    if (wait > 0) {
      console.log(`Rate limit exhausted, pausing ${wait}s before next call`);
      await new Promise((r) => setTimeout(r, wait * 1000));
    }

    return resp;
  }
}

const resp = await getWithRateLimit("issue/12345/");
const data = await resp.json();
```

## Common mistakes

- **Hardcoding the limit values.** Supporter tiers get a higher sustained limit, and defaults may change — always read `X-RateLimit-*-Limit` from the response instead of assuming `20`/`5000`.
- **Retrying immediately on a 429 without waiting.** This just extends your own backoff window and wastes requests that will be throttled again.
- **Ignoring the sustained limit.** An application that paces itself under the burst limit (20/minute) can still blow through 5,000 requests/day well before the day is over if it runs unattended — track both counters, not just burst.
- **Polling instead of syncing.** Repeatedly re-fetching an entire collection burns through your sustained limit fast. Use `modified_gt` so each poll returns only what changed — that's what actually reduces request count. Conditional requests are still worth using on detail endpoints to save bandwidth, but don't count on them to keep you under the limit, since each one still consumes a request.
