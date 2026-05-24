# Architecture

This document is the engineering reference for the bot. For the runbook see [OPERATIONS.md](OPERATIONS.md); for env vars see [CONFIGURATION.md](CONFIGURATION.md).

---

## 1. System overview

The bot is a single Python process running an `APScheduler.BlockingScheduler` loop. ~30 jobs (each one a "bot") fire on independent intervals and serialize browser access via a single `_safari_lock` mutex inside `twitter_client.py`. The process never makes Twitter/X API calls; all interactions go through Safari + AppleScript JS-injection.

### Process model

```
main.py
   │
   ├── argparse → flags (--post-only, --reply-only, --dry-run)
   ├── signal handlers → SIGTERM/SIGINT → graceful scheduler.shutdown()
   ├── BlockingScheduler
   │     ├── 30+ IntervalTrigger jobs, each wrapped in safe_run_*
   │     └── Each safe_run_* calls health.record_success/failure
   │
   └── twitter_client._safari_lock (threading.RLock)
            └── serialises all Safari activations
```

### Data flow

```
                     ┌─────────────────────────┐
                     │   external_signal.json  │
        RSS  ─────┐  │  (RSS + HN + Reddit +   │
        HN   ─────┼──▶  X /home, top 30)       │
        Reddit ───┘  └────────────┬────────────┘
        X /home  ────────────────┘
                                  ▼
        ┌─── prompt assembly (agent.py / hotake_agent.py / etc.) ───┐
        │                                                           │
        │   1. lang_directive (en|fr) ── from lang_mode.py           │
        │   2. core_identity ── from core_identity.md                │
        │   3. bot_self ── from self_evolution_agent.json            │
        │   4. global_mood ── from personality.json                  │
        │   5. external_signal ── HN/RSS/Reddit/Home pulse           │
        │   6. follower_growth ── from follower_history.json         │
        │   7. pattern_stats ── from engagement_log + performance    │
        │   8. live_strategy ── from meta_strategy_agent (caps)      │
        │   9. directives.md ── from evolution_agent (style rules)   │
        │  10. hard_rules + respect_list (always last)               │
        │                                                           │
        └────────────┬──────────────────────────────────────────────┘
                     ▼
              run_llm() → configured CLI provider
                     ▼
              humanizer + strip_agent_preamble + scrub_metadata_leaks
                     ▼
              twitter_client.post_tweet
                     ▼
              engagement_log.csv (with pattern attribution)
                     ▼
        performance.evaluate_and_learn (every 2h)
                     ▼
        evolution_agent / reflection_agent / meta_strategy_agent
                     ▼
        rewrite directives + dossiers + caps
                     ▼
        git_ops.auto_push (per agent)
```

---

## 2. Module catalog

63 modules. Grouped by responsibility.

### Content generation

| Module | Cadence | Output |
|---|---|---|
| `agent.py` | tied to scheduler `post_interval` | News post (≤280 chars + URL) |
| `hotake_agent.py` | 25-30% of post cycles | Hot take + URL |
| `breakout_bot.py` | every 5 min | Fast-trend reaction post |
| `spicy_bot.py` | every ~80 min | Polarising take or question |
| `thread_bot.py` | every 4h (idempotent daily) | 4-tweet single-story thread |
| `digest_thread_bot.py` | every 4h (idempotent daily) | 6-tweet "top 5 stories" recap |
| `agent.py` monthly mode | 1st of month + manual `--monthly-recap-now` | 3 Monthly Décode Top 10 posts: IA, Crypto, Investissement |

### Reshare

| Module | Cadence | Behavior |
|---|---|---|
| `retweet_bot.py` | every 3 min | Feed/search/trusted-handle/big-post scrape → niche+age filter → deterministic score → retweet up to `RETWEETS_PER_CYCLE` |
| `quote_tweet_bot.py` | every 8 min | Legacy repost-pool scrape → FR/EN filter → plain repost |
| `notify_bot.run_boost_cycle` | every 60 min | Self-RT freshest own post (algo-window timing) |

### Reply paths

| Module | Cadence | Source |
|---|---|---|
| `direct_reply.py` | dynamic | `ALWAYS_PROFILES` + `PROFILE-FR` + FOLLOWING + FEED + SEARCH |
| `reply_bot.py` | dynamic | Search-driven random discovery (loose floor) |
| `early_bird_bot.py` | every 4-12 min | 125-account roster, 12-min freshness window |
| `mega_watch_bot.py` | every 90s | Top-10 mega accounts, top-5-reply window |
| `replyback_agent.py` (in `notify_bot`) | every 20 min | Reply-back to people who reply to OUR tweets |
| `viral_followup_bot.py` | every 30 min | When own post hits ≥8 likes, post follow-up |
| `spike_bot.py` | every 8 min | When own post hits ≥25 likes, orchestrate amplification |
| `roast_pgm_bot.py` | every 12-17 min | Dedicated 1-roast-per-tweet path |

### Follow / network

| Module | Cadence | Behavior |
|---|---|---|
| `engage_bot.py` | dynamic | Curated-list follow + like (10-15/cycle) |
| `discover_bot.py` | every 2h | Search X for new niche handles + auto-follow approved |
| `scout_agent.py` | every 4h | Open-web search (WebSearch+WebFetch) for FR/EN voices |
| `follow_blast_bot.py` | every 30 min | JS-bulk-follow on `/search?f=people` (~30/cycle) |
| `followback_bot.py` | every 2h | Scrape /followers, follow back fresh ones |
| `smart_unfollow_bot.py` | every 4h | Diff /following vs /followers, unfollow non-reciprocal (cap 15) |

### Like / promote

| Module | Cadence | Behavior |
|---|---|---|
| `like_bot.py` | every 15 min | JS-click ~18 likes on niche search results |
| `pin_bot.py` | every 6h (idempotent daily) | Auto-pin highest-likes own post via JS menu |
| `promote_bot.py` | every 3h | Plain-repost top recent reply onto profile |

### Real-time signal

| Module | Cadence | Source |
|---|---|---|
| `rss_signal_bot.py` | every 5 min | 20 trusted RSS feeds, parallel fetch |
| `hn_signal_bot.py` | every 20 min | HN front page + Reddit hot |
| `x_home_scout_bot.py` | every 7 min | /home niche-filter |
| `auto_tune_bot.py` | every 30 min | Per-source velocity gauge |
| `mega_watch_bot.py` (signal side) | every 90s | Top-10 mega-account fresh tweets |

### Autonomous self-modification

| Agent | Cadence | Output | Auto-push |
|---|---|---|---|
| `meta_strategy_agent.py` | 4h | `live_strategy.json` (caps, cadence, topic focus) | ✓ |
| `strategy_agent.py` | 3h | `dynamic_queries.json` + `dynamic_accounts.json` | ✓ |
| `evolution_agent.py` | 3h | `directives.md` + `pruned_accounts.json` + `reinforced_accounts.json` | ✓ |
| `reflection_agent.py` | 6h | `personality.json` (per-account dossiers + topic positions) | ✓ |
| `self_evolution_agent.py` | 4h | `bot_self.json` (mood, obsession, drift, self_narrative) | ✓ |
| `scout_agent.py` | 4h | `dynamic_accounts.json` + auto-follows | ✓ |

### Performance + telemetry

| Module | Cadence | Behavior |
|---|---|---|
| `performance.py` | every 2h | Scrape own profile metrics, write `performance_log.json` + `learnings.json`, compute pattern bandit |
| `daily_digest.py` | hourly (idempotent) | Append yesterday's rollup to `daily_digest.md` |
| `follower_tracker_bot.py` | every 30 min | Scrape /gpumaxxing header, log `follower_history.json` |
| `cleanup_bot.py` | hourly (idempotent) | Daily state hygiene — log rotation + JSON caps |
| `heartbeat_bot.py` | every 60s | Alive-tick log line |

Current impact bias: active prompts and repost scoring favor concrete,
numeric, named-actor updates over abstract one-liners. The data-backed pattern
is actor + exact number + consequence, e.g. BTC buys, funding, valuations,
capex, regulation, datacenter energy, and clear winners/losers.

### Safety + infrastructure

| Module | Purpose |
|---|---|
| `health.py` | Per-bot success/failure tracking; 3-fail Safari restart |
| `suppression_watch_bot.py` | Hourly engagement health check; pauses aggressive bots if avg likes drop |
| `respect_list.py` | Soft list of protected handles; output scrub before post |
| `personality_store.py` | Hard rules + per-account dossiers + bot self loader |
| `humanizer.py` | Strip AI artifacts (em dashes, robotic openers, agent preamble) |
| `pattern_tags.py` | Comedy-pattern enum + extract/scrub helpers |
| `lang_mode.py` | Bilingual content language picker |
| `git_ops.py` | Best-effort autonomous git push helper |
| `engagement_log.py` | CSV append-only log: ts, type, text, target_url, source, pattern |

---

## 3. Key invariants

These properties hold at every point in the bot's life cycle:

1. **No cycle ever crashes the scheduler.** Every `safe_run_*` wraps the body in try/except and reports to `health`.
2. **No state file is corrupted by partial write.** Every persistent file uses `json.dump` to a fully-formed dict; counter increments load-modify-save.
3. **No tweet is double-posted.** Every reply/post path has lock-URL-before-publish dedup against a persistent set.
4. **No protected handle is named in critical content.** The `respect_list.scrub_text_or_skip()` final-line defense rejects output containing `@<protected>` or bare-token + derisive marker.
5. **No pattern/source/image metadata leaks into a posted tweet.** `pattern_tags.extract_pattern` + `humanizer.strip_agent_preamble` + `twitter_client._scrub_metadata_leaks` form a 3-layer guard.
6. **No autonomous agent can move caps outside hard ranges.** `meta_strategy_agent._BOUNDS` clamps every output.
7. **No git commit is created on a failed cycle.** `auto_push` is called only after `health.record_success`.

---

## 4. Hard rules (immutable)

Two rules are stamped into every generation prompt via `personality_store.HARD_RULES_BLOCK`. They cannot be auto-rewritten by any agent:

1. **No illegal content** in any form.
2. **No trolling of US government / federal agencies** (Fed, SEC, IRS, FBI, DOJ, etc.). Commenting on the *facts* of their decisions is fine; mocking is not.

A third dynamic rule is added at runtime from `respect_list.json`: never criticize protected handles by name.

---

## 5. Self-modification boundary

What an agent CAN modify autonomously:

- `dynamic_queries.json` / `dynamic_accounts.json` (additions only)
- `directives.md` (overwritten each cycle)
- `pruned_accounts.json` (max 3 prunes/cycle, TTL 30d)
- `reinforced_accounts.json` (max 5/cycle, no TTL)
- `personality.json` (max 30 account updates / 10 topic updates per cycle)
- `bot_self.json` (max 5 voice_tweaks, 5 drift entries)
- `live_strategy.json` (caps clamped to bounds)

What it CANNOT touch:

- `core_identity.md` (the ideological spine)
- `BLOCKLIST` in `config.py`
- `respect_list.py` defaults (operator-managed)
- `personality_store.HARD_RULES_BLOCK`
- Quiet-hour boundaries
- Any source code (only state files)

---

## 6. Adding a new bot

1. Write `src/<your_bot>.py` exposing `safe_run_<your_bot>_cycle()`.
2. Inside `safe_run_*`, wrap the cycle body in try/except. Call `health.record_success/failure` at the end.
3. If the bot writes state files that should be visible in git, call `git_ops.auto_push([...], "message")` after success.
4. If the bot interacts with X via Safari, take `_safari_lock` before opening any URL and `close_front_tab` at the end.
5. Register in `main.py`:
   ```python
   from src.your_bot import safe_run_your_bot_cycle
   ...
   scheduler.add_job(
       safe_run_your_bot_cycle,
       trigger=IntervalTrigger(minutes=N),
       id="your_bot_job",
   )
   ```
6. If your bot has a daily cap, key it by `date.today().isoformat()` in a state file and short-circuit when reached.

---

## 7. Testing strategy

Modules are stateless or store JSON; the bot is exercised by running it. There are no traditional unit tests. The contract is:

- `python3 -c "import main"` must succeed (CI smoke test).
- `python3 -c "import src.<module>"` must succeed for every module.
- `./bin/run.sh` must boot through the AUTONOMY AUDIT block without exception within 10 seconds.

Any new bot must satisfy the same contract.
